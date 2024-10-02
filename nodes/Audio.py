
import os
import folder_paths
import torchaudio

class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")


def analyze_audio_data(audio_data):
    total_duration = 0
    total_gap_duration = 0
    emotion_counts = {}
    audio_types = set()
    languages = set()

    for i, entry in enumerate(audio_data):
        # Calculate the duration of each audio segment
        start_time = entry['start_time']
        end_time = entry['end_time']
        duration = end_time - start_time
        total_duration += duration

        # Count the emotions
        if "emotion" in entry:
            emotion = entry['emotion']
            if emotion in emotion_counts:
                emotion_counts[emotion] += 1
            else:
                emotion_counts[emotion] = 1

        # Collect the audio types
        if "audio_type" in entry:
            audio_types.add(entry['audio_type'])

        if "language" in entry:
            languages.add(entry['language'])

        # Calculate gap duration if not the last entry
        if i < len(audio_data) - 1:
            next_start_time = audio_data[i + 1]['start_time']
            gap_duration = next_start_time - end_time
            if gap_duration > 0:
                total_gap_duration += gap_duration

    # Get the most frequent emotion
    if len(emotion_counts.keys())>0:
        most_frequent_emotion = max(emotion_counts, key=emotion_counts.get)
    else:
        most_frequent_emotion=None

    # Convert audio_types set to list for better readability
    audio_types = list(audio_types)

    languages=list(languages)

    # Print the results
    print(f"Total Effective Duration: {total_duration:.2f} seconds")
    print(f"Total Gap Duration: {total_gap_duration:.2f} seconds")
    print(f"Emotion Changes: {emotion_counts}")
    print(f"Most Frequent Emotion: {most_frequent_emotion}")
    print(f"Audio Types: {audio_types}")


    return {
        "total_duration": total_duration,
        "total_gap_duration": total_gap_duration,
        "emotion_changes": emotion_counts,
        "most_frequent_emotion": most_frequent_emotion,
        "audio_types": audio_types,
        "languages":languages
    }


# 分析音频数据
class AnalyzeAudioNone:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "json":(any_type,),}, 
                }
    
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("result",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Audio"

    def run(self,json):
        result=analyze_audio_data(json)
        return (result,)



class SpeechRecognition:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "upload":("AUDIOINPUTMIX",),   },
                "optional":{
                    "start_by":("INT", {
                        "default": 0, 
                        "min": 0, #Minimum value
                        "max": 2048, #Maximum value
                        "step": 1, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    }),
                   
                }
                }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Audio"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,upload,start_by):
        return {"ui": {"start_by": [start_by]}, "result": (upload,)}


class SpeechSynthesis:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "♾️Mixlab/Audio"

    def run(self, text):
        # print(session_history)
        return {"ui": {"text": text}, "result": (text,)}
    


class AudioPlayNode:
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = ""
        self.compress_level = 4
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "audio": ("AUDIO",),
              }, 
                }
    
    RETURN_TYPES = ()
  
    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Audio"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = ()

    OUTPUT_NODE = True
  
    def run(self,audio):

        # 判断是否是 Tensor 类型
        is_tensor = not isinstance(audio, dict)
        # print('#判断是否是 Tensor 类型',is_tensor,audio)
        if not is_tensor and 'waveform' in audio and 'sample_rate' in audio:
            # {'waveform': tensor([], size=(1, 1, 0)), 'sample_rate': 44100}
            is_tensor=True

        if is_tensor and (not 'audio_path' in audio):
            filename_prefix=""
            # 保存
            filename_prefix += self.prefix_append
            full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir)
            results = list()
            
            filename_with_batch_num = filename.replace("%batch_num%", str(1))
            file = f"{filename_with_batch_num}_{counter:05}_.wav"
            
            torchaudio.save(os.path.join(full_output_folder, file), audio['waveform'].squeeze(0), audio["sample_rate"])
            results.append({
                    "filename": file,
                    "subfolder": subfolder,
                    "type": self.type
                })
            
        else:
            results=[{
                    "filename": audio['filename'],
                    "subfolder":audio['subfolder'],
                    "type": audio['type'],
                    "audio_path":audio['audio_path']
                }]
                

        # print(audio)
        return {"ui": {"audio":results}}