import websockets
import uuid
import json
import asyncio
import ssl

from VoiceStreamAI.audio_utils import save_audio_to_file
from VoiceStreamAI.client import Client

class Server:
    """
    Represents the WebSocket server for handling real-time audio transcription.

    This class manages WebSocket connections, processes incoming audio data,
    and interacts with VAD and ASR pipelines for voice activity detection and
    speech recognition.

    Attributes:
        vad_pipeline: An instance of a voice activity detection pipeline.
        asr_pipeline: An instance of an automatic speech recognition pipeline.
        host (str): Host address of the server.
        port (int): Port on which the server listens.
        sampling_rate (int): The sampling rate of audio data in Hz.
        samples_width (int): The width of each audio sample in bits.
        connected_clients (dict): A dictionary mapping client IDs to Client objects.
    """
    def __init__(self, vad_pipeline, asr_pipeline, host='localhost', port=8765, sampling_rate=16000, samples_width=2, certfile = None, keyfile = None,llm_port=9000):
        self.vad_pipeline = vad_pipeline
        self.asr_pipeline = asr_pipeline
        self.host = host
        self.port = port
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.certfile = certfile
        self.keyfile = keyfile
        self.connected_clients = {}

        self.llm_port=llm_port

    async def handle_audio(self, client, websocket):
        while True:
            message = await websocket.recv()

            if isinstance(message, bytes):
                client.append_audio_data(message)
            elif isinstance(message, str):
                config = json.loads(message)
                if config.get('type') == 'config':
                    client.update_config(config['data'])
                    continue
            else:
                print(f"Unexpected message type from {client.client_id}")

            # this is synchronous, any async operation is in BufferingStrategy
            client.process_audio(websocket, self.vad_pipeline, self.asr_pipeline,self.llm_port)


    async def handle_websocket(self, websocket, path):
        client_id = str(uuid.uuid4())
        client = Client(client_id, self.sampling_rate, self.samples_width)
        self.connected_clients[client_id] = client

        print(f"Client {client_id} connected")

        try:
            await self.handle_audio(client, websocket)
        except websockets.ConnectionClosed as e:
            print(f"Connection with {client_id} closed: {e}")
        finally:
            del self.connected_clients[client_id]

    def start(self):
        if self.certfile:
            # Create an SSL context to enforce encrypted connections
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            
            # Load your server's certificate and private key
            # Replace 'your_cert_path.pem' and 'your_key_path.pem' with the actual paths to your files
            ssl_context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)

            print(f"WebSocket server ready to accept secure connections on {self.host}:{self.port}")
            
            # Pass the SSL context to the serve function along with the host and port
            # Ensure the secure flag is set to True if using a secure WebSocket protocol (wss://)
            return websockets.serve(self.handle_websocket, self.host, self.port, ssl=ssl_context)
        else:
            print(f"WebSocket server ready to accept secure connections on {self.host}:{self.port}")
            return websockets.serve(self.handle_websocket, self.host, self.port)
