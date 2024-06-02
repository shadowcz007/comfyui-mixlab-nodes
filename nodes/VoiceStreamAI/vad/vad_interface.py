class VADInterface:
    """
    Interface for voice activity detection (VAD) systems.
    """

    async def detect_activity(self, client):
        """
        Detects voice activity in the given audio data.

        Args:
            client (src.Client): The client to detect on

        Returns:
            List: VAD result, a list of objects containing "start", "end", "confidence"
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
