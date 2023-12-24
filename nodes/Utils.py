import os
import re,random
# FONT_PATH= os.path.abspath(os.path.join(os.path.dirname(__file__),'../assets/王汉宗颜楷体繁.ttf'))

import matplotlib.font_manager as fm

def get_font_files(directory):
    font_files = {}

    # 从指定目录加载字体
    for file in os.listdir(directory):
        if file.endswith('.ttf') or file.endswith('.otf'):
            font_name = os.path.splitext(file)[0]
            font_path = os.path.join(directory, file)
            font_files[font_name] = os.path.abspath(font_path)

    # 尝试获取系统字体
    try:
        font_paths = fm.findSystemFonts()
        for path in font_paths:
            try:
                font_prop = fm.FontProperties(fname=path)
                font_name = font_prop.get_name()
                font_files[font_name] = path
            except Exception as e:
                print(f"Error processing font {path}: {e}")
    except Exception as e:
        print(f"Error finding system fonts: {e}")

    return font_files

r_directory = os.path.join(os.path.dirname(__file__), '../assets/')

font_files = get_font_files(r_directory)
# print(font_files)


class ColorInput:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
             
                    "color":("TCOLOR",), 
                             },
                }
    
    RETURN_TYPES = ("STRING",)
    # RETURN_NAMES = ("WIDTH","HEIGHT","X","Y",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,)

    def run(self,color):
        return (color,)



class FontInput:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
             
                    "font": (list(font_files.keys()),),
                             },
                }
    
    RETURN_TYPES = ("STRING",)
    # RETURN_NAMES = ("WIDTH","HEIGHT","X","Y",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,)

    def run(self,font):

        return (font_files[font],)
    
class TextToNumber:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "text": ("STRING",{"multiline": False,"default": "1"}),
                    "random_number": (["enable", "disable"],),
                    "number":("INT", {
                        "default": 0, 
                        "min": 0, #Minimum value
                        "max": 10000000000, #Maximum value
                        "step": 1, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    }),
                             },
                }
    
    RETURN_TYPES = ("INT",)
    # RETURN_NAMES = ("WIDTH","HEIGHT","X","Y",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,text,random_number,number):
        
        numbers = re.findall(r'\d+', text)
        result=0
        for n in numbers:
            result = int(n)
            print(result)
        
        if random_number=='enable' and result>0:
            result= random.randint(1, 10000000000)
        return {"ui": {"text": [text],"num":[result]}, "result": (result,)}
    
# 接收一个值，然后根据字符串或数值长度计算延迟时间，用户可以自定义延迟"字/s"，延迟之后将转化

import comfy.samplers
import folder_paths
 
# import time


class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")
import time

class DynamicDelayProcessor:

    @classmethod
    def INPUT_TYPES(cls):
        print("print INPUT_TYPES",cls)
        return {
            "required":{
                    "delay_seconds":("INT",{
                    "default":1,
                    "min": 0,
                    "max": 1000000,
                    }),
            },
            "optional":{
                "any_input":(any_type,),
                "delay_by_text":("STRING",{"multiline":True,}),
                "words_per_seconds":("FLOAT",{ "default":1.50,"min": 0.0,"max": 1000.00,"display":"Chars per second?"}),
                "replace_output": (["disable","enable"],),
                "replace_value":("INT",{ "default":-1,"min": 0,"max": 1000000,"display":"Replacement value"})
                }
            }
  
    @classmethod
    def calculate_words_length(cls,text):
        chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]')
        english_word_pattern = re.compile(r'\b[a-zA-Z]+\b')
        number_pattern = re.compile(r'\b[0-9]+\b')

        words_length = 0
        for segment in text.split():
            if chinese_char_pattern.search(segment):
                # 中文字符，每个字符计为 1
                words_length += len(segment)
            elif number_pattern.match(segment):
                # 数字，每个字符计为 1
                words_length += len(segment)
            elif english_word_pattern.match(segment):
                # 英文单词，整个单词计为 1
                words_length += 1

        return words_length



    FUNCTION = "run"
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ('output',)

    CATEGORY = "♾️Mixlab/utils"
    def run(self,any_input,delay_seconds,delay_by_text,words_per_seconds,replace_output,replace_value):
        # print(f"Delay text:",delay_by_text )
        # 获取开始时间戳
        start_time = time.time()

        # 计算延迟时间
        delay_time = delay_seconds
        if delay_by_text and isinstance(delay_by_text, str) and words_per_seconds > 0:
            words_length = self.calculate_words_length(delay_by_text)
            print(f"Delay text: {delay_by_text}, Length: {words_length}")
            delay_time += words_length / words_per_seconds
            
        # 延迟执行
        time.sleep(delay_time)

        # 获取结束时间戳并计算间隔
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"实际延迟时间: {elapsed_time} 秒")        

        # 根据 replace_output 决定输出值
        return (max(0, replace_value),) if replace_output == "enable" else (any_input,)
        
