import asyncio
import websockets
import webrtcvad
import sys
from faster_whisper import WhisperModel
import numpy as np
import io

# pip install webrtcvad-wheels
# pip install websockets
# pip install faster-whisper

vad = webrtcvad.Vad(3)

class AudioStream:
    def __init__(self) -> None:
        self.sample_rate = 16000
        self.frame_size = 320
        self.bytes_per_sample = 2
        self.idle_cut = (self.sample_rate/2)/self.frame_size # chunk audio if no voice for 0.5 seconds
        self.last_voice_activity = {}
        self.audio_buffers = {}

    def convert_buffer_size(self, audio_frame):
        while len(audio_frame) < (self.frame_size * self.bytes_per_sample):
            audio_frame = audio_frame + b'\x00'
        return audio_frame
    
    def manage_client_idle(self, client_id):
        if client_id not in self.last_voice_activity:
            self.last_voice_activity[client_id] = 0
        return self.last_voice_activity[client_id]
    
    def voice_activity_detection(self, audio_frame, client_id):
        idle_time = self.manage_client_idle(client_id)
        converted_frame = self.convert_buffer_size(audio_frame)
        is_speech = vad.is_speech(converted_frame, sample_rate=self.sample_rate)
        if is_speech:
            self.last_voice_activity[client_id] = 0
            if client_id not in self.audio_buffers:
                self.audio_buffers[client_id] = []
            self.audio_buffers[client_id].append(converted_frame)
            return "1"
        else:
            if idle_time == self.idle_cut:
                self.last_voice_activity[client_id] = 0
                return "X"
            else:
                self.last_voice_activity[client_id] += 1
                return "_"

audiostream = AudioStream()
model_size = "faster-distil-medium.en"
whisper_model = WhisperModel(model_size, device="cuda", compute_type="float16")

async def handler(websocket, path):
    client_id = id(websocket)
    print(f"WebSocket connection established for client {client_id} from {path}")
    try:
        async for message in websocket:
            is_active = audiostream.voice_activity_detection(message, client_id)
            
            if is_active == "X":  # Voice activity stopped
                audio_buffer = audiostream.audio_buffers.pop(client_id, None)
                if audio_buffer:
                    audio_data = b''.join(audio_buffer)
                    audio_data = np.frombuffer(audio_data, dtype=np.int16)
                    with io.BytesIO() as wav_buffer:
                        wav_buffer.write(audio_data.tobytes())
                        wav_buffer.seek(0)
                        segments, info = whisper_model.transcribe(wav_buffer, beam_size=5, language="en", condition_on_previous_text=False)
                        transcript = " ".join(segment.text for segment in segments)
                        await websocket.send(transcript)
            else:
                await websocket.send(is_active)

    except websockets.exceptions.ConnectionClosed:
        print(f"WebSocket connection closed for client {client_id}")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        await websocket.close()

async def main():
    PORT = 5000
    async with websockets.serve(handler, 'localhost', PORT):
        print(f"WebSocket server started at ws://localhost:{PORT}")
        await asyncio.Future()

asyncio.run(main())

