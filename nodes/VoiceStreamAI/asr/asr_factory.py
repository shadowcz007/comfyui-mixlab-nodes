from VoiceStreamAI.asr.whisper_asr import WhisperASR
from VoiceStreamAI.asr.faster_whisper_asr import FasterWhisperASR

class ASRFactory:
    @staticmethod
    def create_asr_pipeline(type, **kwargs):
        if type == "whisper":
            return WhisperASR(**kwargs)
        if type == "faster_whisper":
            return FasterWhisperASR(**kwargs)
        else:
            raise ValueError(f"Unknown ASR pipeline type: {type}")
