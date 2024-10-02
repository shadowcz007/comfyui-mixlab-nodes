import os,re
import sys,time
from pathlib import Path
import torchaudio
import hashlib
import torch
import folder_paths
import comfy.utils

from faster_whisper import WhisperModel

class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")

def get_model_dir(m):
    try:
        return folder_paths.get_folder_paths(m)[0]
    except:
        return os.path.join(folder_paths.models_dir, m)



whisper_model_path=get_model_dir('whisper')

model_sizes=[
                d for d in os.listdir(whisper_model_path) if os.path.isdir(
                    os.path.join(whisper_model_path, d)
                    ) and os.path.isfile(os.path.join(os.path.join(whisper_model_path, d), "config.json"))
                    ]


class LoadWhisperModel:
    def __init__(self):
        self.model = None
        self.device="cuda" if torch.cuda.is_available() else "cpu"
        self.model_size=model_sizes[0]
        self.compute_type='float16'

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "model_size": (model_sizes,),
            "device": (["auto","cpu"],),
            "compute_type": (["float16","int8_float16","int8"],),
                             },
                }
    
    RETURN_TYPES = ("WHISPER",)
    RETURN_NAMES = ("whisper_model",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Audio/Whisper"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,model_size,device,compute_type):

        if device=="auto" and self.device!='cuda':
            self.device="cuda" if torch.cuda.is_available() else "cpu"
            self.model=None

        if device=='cpu' and self.device!='cpu':
            self.device="cpu"
            self.model=None
        
        if model_size!= self.model_size:
            self.model_size=model_size
            self.model=None

        if compute_type!=self.compute_type:
            self.compute_type=compute_type
            self.model=None

        if self.model==None:
            self.model = WhisperModel(
                os.path.join(whisper_model_path, self.model_size), 
                device=self.device,
                compute_type=self.compute_type
                )

        return (self.model,)
    

class WhisperTranscribe:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                                "whisper_model": ("WHISPER",),
                                "audio": ("AUDIO",),
                             },
                }
    
    RETURN_TYPES = (any_type,"STRING","STRING","FLOAT",)
    RETURN_NAMES = ("result","srt","text","total_seconds",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Audio/Whisper"

    INPUT_IS_LIST = False
    # OUTPUT_IS_LIST = (False,False,False,)
    
    def run(self,whisper_model,audio):

        if 'audio_path' in audio and (not 'waveform' in audio):
            waveform, sample_rate = torchaudio.load(audio['audio_path'])
            waveform=waveform.mean(0)
            total_length_seconds = waveform.shape[0] / sample_rate
            waveform=waveform.numpy()
            
        elif 'waveform' in audio and 'sample_rate' in audio:
            print("Original shape:", audio["waveform"].shape, isinstance(audio["waveform"], torch.Tensor))  # 打印原始形状
            waveform = audio["waveform"].squeeze(0)  # Remove the added batch dimension
            sample_rate = audio["sample_rate"]

            # if audio_sf != sampling_rate:
            #     waveform = torchaudio.functional.resample(
            #         waveform, orig_freq=audio_sf, new_freq=sampling_rate
            #     )
            
            waveform=waveform.mean(0)

            total_length_seconds = waveform.shape[0] / sample_rate

            waveform=waveform.numpy() #whisper_model.transcribe 旧版不支持直接传tensor，先用numpy
        
        segments, info = whisper_model.transcribe(waveform, beam_size=5)

        print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

        # Function to format time for SRT
        def format_time(seconds):
            millis = int((seconds - int(seconds)) * 1000)
            hours, remainder = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

        # Prepare SRT content as a string
        results = []
        for i, segment in enumerate(segments):
            start_time = format_time(segment.start)
            end_time = format_time(segment.end)
            srt_content = f"{i + 1}\n"
            srt_content += f"{start_time} --> {end_time}\n"

            text=segment.text.strip()

            srt_content += f"{text}\n\n"

            start_time=segment.start
            end_time=segment.end
            

            results.append({ 
                    "srt_content":srt_content,
                    "start_time":start_time,
                    "end_time":end_time,
                    "text":text,
                    "language":[info.language]
            })
        
        srt_content="\n".join([s['srt_content'] for s in results])
        text="\n".join([s['text'] for s in results])

        return (results,srt_content,text,total_length_seconds,)

