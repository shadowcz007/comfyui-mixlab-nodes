import wave
import os

async def save_audio_to_file(audio_data, file_name, audio_dir="audio_files", audio_format="wav"):
    """
    Saves the audio data to a file.

    :param client_id: Unique identifier for the client.
    :param audio_data: The audio data to save.
    :param file_counters: Dictionary to keep track of file counts for each client.
    :param audio_dir: Directory where audio files will be saved.
    :param audio_format: Format of the audio file.
    :return: Path to the saved audio file.
    """

    os.makedirs(audio_dir, exist_ok=True)
    
    file_path = os.path.join(audio_dir, file_name)

    with wave.open(file_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Assuming mono audio
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(audio_data)

    return file_path
