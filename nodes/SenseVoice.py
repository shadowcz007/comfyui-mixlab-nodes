# -*- coding:utf-8 -*-
import logging
import os
import time

from huggingface_hub import snapshot_download
import torch,re
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

# 字幕
def format_to_srt(channel_id, start_time_ms, end_time_ms, asr_result):
    start_time = start_time_ms / 1000
    end_time = end_time_ms / 1000
    
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"
    
    start_time_str = format_time(start_time)
    end_time_str = format_time(end_time)

    pattern = r"<\|(.+?)\|><\|(.+?)\|><\|(.+?)\|><\|(.+?)\|>(.+)"
    match = re.match(pattern,asr_result)
    print('#format_to_srt',match,asr_result)
    if match==None:
        return None, None, None, None,None,start_time,end_time,None
    lang, emotion, audio_type, itn, text = match.groups()
     # 😊 表示高兴，😡 表示愤怒，😔 表示悲伤。对于音频事件，🎼 表示音乐，😀 表示笑声，👏 表示掌声
    
    srt_content = f"1\n{start_time_str} --> {end_time_str}\n{text}\n"
    
    logging.info(f"[Channel {channel_id}] [{start_time}s - {end_time}s] [{lang}] [{emotion}] [{audio_type}] [{itn}] {text}")

    return lang, emotion, audio_type, itn,srt_content,start_time,end_time,text


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

                lang, emotion, audio_type, itn,srt_content,start_time,end_time,text=format_to_srt(
                    channel_id, 
                    part[0] , 
                    part[1], 
                    asr_result)

                if lang!=None:
                    results.append({
                        "language":lang, 
                        "emotion":emotion,
                        "audio_type":audio_type, 
                        "itn":itn,
                        "srt_content":srt_content,
                        "start_time":start_time,
                        "end_time":end_time,
                        "text":text
                    })

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
    
    RETURN_TYPES = (any_type,"STRING","STRING","FLOAT",)
    RETURN_NAMES = ("result","srt","text","total_seconds",)

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
            sample_rate = audio['sample_rate']
            # print("Original shape:", waveform.shape)  # 打印原始形状
            if waveform.ndim == 3 and waveform.shape[0] == 1:  # 检查是否为三维且 batch_size 为 1
                waveform = waveform.squeeze(0)  # 移除 batch_size 维度
            else:
                raise ValueError("Unexpected waveform dimensions")

            print("waveform.shape:", waveform.shape) 
            total_length_seconds = waveform.shape[1] / sample_rate

            waveform_numpy = waveform.numpy().transpose(1, 0)  # 转换为 (num_samples, num_channels)

        results=self.processor.process_audio(waveform_numpy, sample_rate, language, use_itn)

        srt_content="\n".join([s['srt_content'] for s in results])
        text="\n".join([s['text'] for s in results])

        return (results,srt_content,text,total_length_seconds,)
 