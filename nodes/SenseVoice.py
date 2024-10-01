# -*- coding:utf-8 -*-
import logging
import os
import time

from huggingface_hub import snapshot_download
import torch
from sensevoice.onnx.sense_voice_ort_session import SenseVoiceInferenceSession
from sensevoice.utils.frontend import WavFrontend
from sensevoice.utils.fsmn_vad import FSMNVad
import comfy.utils
import folder_paths

languages = {"auto": 0, "zh": 3, "en": 4, "yue": 7, "ja": 11, "ko": 12, "nospeech": 13}

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 
def get_model_path():
    try:
        return folder_paths.get_folder_paths('sense_voice')[0]
    except:
        return os.path.join(folder_paths.models_dir, "sense_voice")

class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")    

class SenseVoiceProcessor:
    def __init__(self, download_model_path, device, num_threads, use_int8):

        if not os.path.exists(download_model_path):
            logging.info(
                "Downloading model from huggingface hub from https://huggingface.co/lovemefan/SenseVoice-onnx"
            )
            logging.info(
                "You can speed up with  `export HF_ENDPOINT=https://hf-mirror.com`"
            )
            snapshot_download(
                repo_id="lovemefan/SenseVoice-onnx", local_dir=download_model_path
            )

        self.download_model_path = download_model_path
        self.device = device
        self.num_threads = num_threads
        self.use_int8 = use_int8
        self.front = WavFrontend(os.path.join(download_model_path, "am.mvn"))
        self.model = SenseVoiceInferenceSession(
            os.path.join(download_model_path, "embedding.npy"),
            os.path.join(
                download_model_path,
                "sense-voice-encoder-int8.onnx"
                if use_int8
                else "sense-voice-encoder.onnx",
            ),
            os.path.join(download_model_path, "chn_jpn_yue_eng_ko_spectok.bpe.model"),
            device,
            num_threads,
        )
        self.vad = FSMNVad(download_model_path)

    def process_audio(self, waveform, _sample_rate, language, use_itn):
    
        start = time.time()
        pbar = comfy.utils.ProgressBar(waveform.shape[1])  # 进度条

        results = []

        for channel_id, channel_data in enumerate(waveform.T):
            segments = self.vad.segments_offline(channel_data)
            
            for part in segments:
                audio_feats = self.front.get_features(channel_data[part[0] * 16 : part[1] * 16])
                asr_result = self.model(
                    audio_feats[None, ...],
                    language=languages[language],
                    use_itn=use_itn,
                )
                logging.info(f"[Channel {channel_id}] [{part[0] / 1000}s - {part[1] / 1000}s] {asr_result}")
                
                results.append(asr_result)

            self.vad.vad.all_reset_detection()
            pbar.update(1)  # 更新进度条

        decoding_time = time.time() - start
        logging.info(f"Decoder audio takes {decoding_time} seconds")
        logging.info(f"The RTF is {decoding_time/(waveform.shape[1] * len(waveform) / _sample_rate)}.")
        return results


class SenseVoiceNode:

    def __init__(self):
        self.processor = None
        self.download_model_path=get_model_path()
        self.device="cpu"
        self.num_threads = 4
        self.use_int8 = True
        self.language='auto'

    @classmethod
    def INPUT_TYPES(s):
       
        return {"required": {
                    "audio": ("AUDIO", ), 
                    "device": ( ['auto','cpu'], {"default": 'auto'}),
                     "language": (list(languages.keys()), {"default": 'auto'}),# 不能直接写 languages.keys(),json.dumps会报错
                     "num_threads":("INT",{
                                "default":4, 
                                "min": 1, #Minimum value
                                "max": 32, #Maximum value
                                "step": 1, #Slider's step
                                "display": "number" # Cosmetic only: display as "number" or "slider"
                                },),
                     "use_int8":("BOOLEAN", {"default": True},),
                     "use_itn":("BOOLEAN", {"default": True},),
                     },
                }

    CATEGORY = "♾️Mixlab/Audio"

    OUTPUT_NODE = True
    FUNCTION = "run" 
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("result",)

    def run(self,audio,device,language,num_threads,use_int8,use_itn ):
 
        if device!=self.device:
            self.device=device
            self.processor=None
        if language!=self.language:
            self.language=language
            self.processor=None
        if num_threads!=self.num_threads:
            self.num_threads=num_threads
            self.processor=None
        if use_int8!=self.use_int8:
            self.use_int8=use_int8
            self.processor=None
        
        if device=='auto' and torch.cuda.is_available():
            self.device='cuda'

        # num_threads=4
        # use_int8=True

        if self.processor==None:
            self.processor = SenseVoiceProcessor(self.download_model_path, 
                                                 self.device, 
                                                 self.num_threads, 
                                                 self.use_int8)

        if 'waveform' in audio and 'sample_rate' in audio:
            waveform = audio['waveform']
            # print("Original shape:", waveform.shape)  # 打印原始形状
            if waveform.ndim == 3 and waveform.shape[0] == 1:  # 检查是否为三维且 batch_size 为 1
                waveform = waveform.squeeze(0)  # 移除 batch_size 维度
                waveform_numpy = waveform.numpy().transpose(1, 0)  # 转换为 (num_samples, num_channels)
            else:
                raise ValueError("Unexpected waveform dimensions")

            _sample_rate = audio['sample_rate']

        results=self.processor.process_audio(waveform_numpy, _sample_rate, language, use_itn)


        return (results,)
