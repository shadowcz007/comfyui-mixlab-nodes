from VoiceStreamAI.buffering_strategy.buffering_strategies import SilenceAtEndOfChunk

class BufferingStrategyFactory:
    """
    A factory class for creating instances of different buffering strategies.

    This factory provides a centralized way to instantiate various buffering strategies
    based on the type specified. It abstracts the creation logic, making it easier to
    manage and extend with new buffering strategy types.

    Methods:
        create_buffering_strategy: Creates and returns an instance of a specified buffering strategy.
    """

    @staticmethod
    def create_buffering_strategy(type, client, **kwargs):
        """
        Creates an instance of a buffering strategy based on the specified type.

        This method acts as a factory for creating buffering strategy objects. It returns
        an instance of the strategy corresponding to the given type. If the type is not
        recognized, it raises a ValueError.

        Args:
            type (str): The type of buffering strategy to create. Currently supports 'silence_at_end_of_chunk'.
            client (Client): The client instance to be associated with the buffering strategy.
            **kwargs: Additional keyword arguments specific to the buffering strategy being created.

        Returns:
            An instance of the specified buffering strategy.

        Raises:
            ValueError: If the specified type is not recognized or supported.

        Example:
            strategy = BufferingStrategyFactory.create_buffering_strategy("silence_at_end_of_chunk", client)
        """
        if type == "silence_at_end_of_chunk":
            return SilenceAtEndOfChunk(client, **kwargs)
        else:
            raise ValueError(f"Unknown buffering strategy type: {type}")
