from os import remove
import os

from pyannote.core import Segment
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection

from VoiceStreamAI.vad.vad_interface import VADInterface
from VoiceStreamAI.audio_utils import save_audio_to_file


class PyannoteVAD(VADInterface):
    """
    Pyannote-based implementation of the VADInterface.
    """

    def __init__(self, **kwargs):
        """
        Initializes Pyannote's VAD pipeline.

        Args:
            model_name (str): The model name for Pyannote.
            auth_token (str, optional): Authentication token for Hugging Face.
        """
        
        model_name = kwargs.get('model_name', "pyannote/segmentation")

        auth_token = os.environ.get('PYANNOTE_AUTH_TOKEN')
        if not auth_token:
            auth_token = kwargs.get('auth_token')
        
        if auth_token is None:
            raise ValueError("Missing required env var in PYANNOTE_AUTH_TOKEN or argument in --vad-args: 'auth_token'")
        
        pyannote_args = kwargs.get('pyannote_args', {"onset": 0.5, "offset": 0.5, "min_duration_on": 0.3, "min_duration_off": 0.3})
        self.model = Model.from_pretrained(model_name, use_auth_token=auth_token)
        self.vad_pipeline = VoiceActivityDetection(segmentation=self.model)
        self.vad_pipeline.instantiate(pyannote_args)

    async def detect_activity(self, client):
        audio_file_path = await save_audio_to_file(client.scratch_buffer, client.get_file_name())
        vad_results = self.vad_pipeline(audio_file_path)
        remove(audio_file_path)
        vad_segments = []
        if len(vad_results) > 0:
            vad_segments = [
                {"start": segment.start, "end": segment.end, "confidence": 1.0}
                for segment in vad_results.itersegments()
            ]
        return vad_segments
