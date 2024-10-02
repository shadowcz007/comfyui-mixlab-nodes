
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
        "audio_types": audio_types
    }

# Example usage
audio_data = [{'language': 'zh', 'emotion': 'SAD', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:00:00,540 --> 00:00:10,550\n嘿，欢迎来到梦幻纷飞探索心灵迷雾的奇境之旅。在这里，你将踏上一段超现实的。\n', 'start_time': 0.54, 'end_time': 10.55, 'text': '嘿，欢迎来到梦幻纷飞探索心灵迷雾的奇境之旅。在这里，你将踏上一段超现实的。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:00:10,550 --> 00:00:20,559\n有奇幻之旅，想象一下啊，这个悬浮的棋盘和巨大的漂浮眼睛。哇这。\n', 'start_time': 10.55, 'end_time': 20.56, 'text': '有奇幻之旅，想象一下啊，这个悬浮的棋盘和巨大的漂浮眼睛。哇这。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:00:20,559 --> 00:00:25,960\n意象就会让你对其他世界为独，充满好奇。\n', 'start_time': 20.56, 'end_time': 25.96, 'text': '意象就会让你对其他世界为独，充满好奇。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:00:26,239 --> 00:00:36,250\n我们的艺术家梦颖就以其独特的杏人型眼睛和飘逸的黑发，穿着流动的礼服，完美。\n', 'start_time': 26.24, 'end_time': 36.25, 'text': '我们的艺术家梦颖就以其独特的杏人型眼睛和飘逸的黑发，穿着流动的礼服，完美。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:00:36,250 --> 00:00:41,820\n融入这个暗淡的背景啊，形成一个神秘的身影。\n', 'start_time': 36.25, 'end_time': 41.82, 'text': '融入这个暗淡的背景啊，形成一个神秘的身影。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:00:43,170 --> 00:00:53,179\n在这次展览中，我们将一起揭示人类心灵的秘密与欲望。那个梦影的作品通过细腻的绘画。\n', 'start_time': 43.17, 'end_time': 53.18, 'text': '在这次展览中，我们将一起揭示人类心灵的秘密与欲望。那个梦影的作品通过细腻的绘画。'}, {'language': 'zh', 'emotion': 'SAD', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:00:53,179 --> 00:01:03,189\n技巧和超越常规的图像构思，带你探索内心深处的情感和欲望。这种感觉真的就是。\n', 'start_time': 53.18, 'end_time': 63.19, 'text': '技巧和超越常规的图像构思，带你探索内心深处的情感和欲望。这种感觉真的就是。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:01:03,189 --> 00:01:09,019\n是准备好被激发想象力和困惑了吗？哇哦。\n', 'start_time': 63.19, 'end_time': 69.02, 'text': '是准备好被激发想象力和困惑了吗？哇哦。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:01:09,299 --> 00:01:19,310\n通过与艺术家的互动，你将进入一个超越现实的境界，挑战你对现实和逻辑的理解。\n', 'start_time': 69.3, 'end_time': 79.31, 'text': '通过与艺术家的互动，你将进入一个超越现实的境界，挑战你对现实和逻辑的理解。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:01:20,939 --> 00:01:30,950\n所以快来吧，然后让我们一起投身这场奇境之旅吧，挖掘人类的秘密与欲望。\n', 'start_time': 80.94, 'end_time': 90.95, 'text': '所以快来吧，然后让我们一起投身这场奇境之旅吧，挖掘人类的秘密与欲望。'}, {'language': 'zh', 'emotion': 'SAD', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:01:31,189 --> 00:01:41,200\n激发你的想象力与困惑，希望这段旅程能让你在艺术与灵魂的碰撞中找到珍贵的。\n', 'start_time': 91.19, 'end_time': 101.2, 'text': '激发你的想象力与困惑，希望这段旅程能让你在艺术与灵魂的碰撞中找到珍贵的。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:01:41,200 --> 00:01:47,170\n回忆并引发内心的转变与行动。那就是。\n', 'start_time': 101.2, 'end_time': 107.17, 'text': '回忆并引发内心的转变与行动。那就是。'}, {'language': 'zh', 'emotion': 'NEUTRAL', 'audio_type': 'Speech', 'itn': 'withitn', 'srt_content': '1\n00:01:48,760 --> 00:01:51,790\n嗯，准备好了吗？走吧。\n', 'start_time': 108.76, 'end_time': 111.79, 'text': '嗯，准备好了吗？走吧。'}]

print(analyze_audio_data(audio_data))

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