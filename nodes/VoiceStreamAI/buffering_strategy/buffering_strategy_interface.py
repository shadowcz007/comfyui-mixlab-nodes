class BufferingStrategyInterface:
    """
    An interface class for buffering strategies in audio processing systems.

    This class defines the structure for buffering strategies used in handling
    and processing audio data. It serves as a template for creating custom buffering
    strategies that fit specific requirements of an audio processing pipeline.

    Subclasses should implement the methods defined in this interface to ensure
    consistency and compatibility with the system's audio processing framework.

    Methods:
        process_audio: Process audio data. This method should be implemented by subclasses.
    """

    def process_audio(self, websocket, vad_pipeline, asr_pipeline):
        """
        Process audio data using the given WebSocket connection, VAD pipeline, and ASR pipeline.

        This method is intended to be overridden in subclasses to provide specific logic
        for handling and processing audio data in different buffering strategies.

        Args:
            websocket (Websocket): The WebSocket connection for communication with clients.
            vad_pipeline: The Voice Activity Detection (VAD) pipeline used for detecting speech in the audio.
            asr_pipeline: The Automatic Speech Recognition (ASR) pipeline used for transcribing speech in the audio.

        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
