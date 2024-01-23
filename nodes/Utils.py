import os,platform
import re,random,json
from PIL import Image
import numpy as np
# FONT_PATH= os.path.abspath(os.path.join(os.path.dirname(__file__),'../assets/王汉宗颜楷体繁.ttf'))
import folder_paths
import matplotlib.font_manager as fm
import torch



def recursive_search(directory, excluded_dir_names=None):
    if not os.path.isdir(directory):
        return [], {}

    if excluded_dir_names is None:
        excluded_dir_names = []

    result = []
    dirs = {directory: os.path.getmtime(directory)}
    for dirpath, subdirs, filenames in os.walk(directory, followlinks=True, topdown=True):
        subdirs[:] = [d for d in subdirs if d not in excluded_dir_names]
        for file_name in filenames:
            relative_path = os.path.relpath(os.path.join(dirpath, file_name), directory)
            result.append(relative_path)
        for d in subdirs:
            path = os.path.join(dirpath, d)
            dirs[path] = os.path.getmtime(path)
    return result, dirs

def filter_files_extensions(files, extensions):
    return sorted(list(filter(lambda a: os.path.splitext(a)[-1].lower() in extensions or len(extensions) == 0, files)))


def get_system_font_path():
    ps=[]
    system = platform.system()
    if system == "Windows":
        ps.append(os.path.join(os.environ["WINDIR"], "Fonts"))
    elif system == "Darwin":
        ps.append(os.path.join("/Library", "Fonts"))
    elif system == "Linux":
        ps.append(os.path.join("/usr", "share", "fonts"))
        ps.append(os.path.join("/usr", "local", "share", "fonts"))
    ps=[p for p in ps if os.path.exists(p)]
    file_paths=[]
    for f in ps:
        result, dirs=recursive_search(f)
        for r in result:
            file_paths.append(r)
    file_paths=filter_files_extensions(file_paths,[".otf", ".ttf"])

    return file_paths



# import json
# import hashlib


# def get_json_hash(json_content):
#     json_string = json.dumps(json_content, sort_keys=True)
#     hash_object = hashlib.sha256(json_string.encode())
#     hash_value = hash_object.hexdigest()
#     return hash_value
    


def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


def create_temp_file(image):
    output_dir = folder_paths.get_temp_directory()

    (
            full_output_folder,
            filename,
            counter,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path('tmp', output_dir)

    
    im=tensor2pil(image)
 
    image_file = f"{filename}_{counter:05}.png"
     
    image_path=os.path.join(full_output_folder, image_file)

    im.save(image_path,compress_level=4)

    return [{
                "filename": image_file,
                "subfolder": subfolder,
                "type": "temp"
                }]

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
        font_paths = get_system_font_path()
        for file in font_paths:
            try:
                font_name = os.path.splitext(file)[0]
                font_path = file
                font_files[font_name] = os.path.abspath(font_path)
            except Exception as e:
                print(f"Error processing font {file}: {e}")
    except Exception as e:
        print(f"Error finding system fonts: {e}")

    return font_files

r_directory = os.path.join(os.path.dirname(__file__), '../assets/')

font_files = get_font_files(r_directory)
# print(font_files)


def flatten_list(nested_list):
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))
        else:
            if torch.is_tensor(item):
                print('item.shape',item.shape)
                for i in range(item.shape[0]):
                    flat_list.append(item[i:i + 1, ...])
            else:
                flat_list.append(item)
    return flat_list


class ColorInput:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
             
                    "color":("TCOLOR",), 
                             },
                }
    
    RETURN_TYPES = ("STRING","INT","INT","INT","FLOAT",)
    RETURN_NAMES = ("hex","r","g","b","a",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,False,False,False,)

    def run(self,color):
        h=color['hex']
        r=color['r']
        g=color['g']
        b=color['b']
        a=color['a']
        return (h,r,g,b,a,)



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

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

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

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,text,random_number,number):
        
        numbers = re.findall(r'\d+', text)
        result=0
        for n in numbers:
            result = int(n)
            # print(result)
        
        if random_number=='enable' and result>0:
            result= random.randint(1, 10000000000)
        return {"ui": {"text": [text],"num":[result]}, "result": (result,)}
    

   
class FloatSlider:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "number":("FLOAT", {
                        "default": 0, 
                        "min": 0, #Minimum value
                        "max": 0xffffffffffffffff, #Maximum value
                        "step": 0.001, #Slider's step
                        "display": "slider" # Cosmetic only: display as "number" or "slider"
                    }),
                    "min_value":("FLOAT", {
                        "default": 0, 
                        "min": -0xffffffffffffffff, 
                        "max": 0xffffffffffffffff,
                        "step": 0.001, 
                        "display": "number"  
                    }),
                    "max_value":("FLOAT", {
                            "default": 1, 
                            "min": -0xffffffffffffffff,
                            "max": 0xffffffffffffffff,
                            "step": 0.001, 
                            "display": "number"  
                        }),
                    "step":("FLOAT", {
                            "default": 0.001, 
                            "min": -0xffffffffffffffff,
                            "max": 0xffffffffffffffff,
                            "step": 0.001, 
                            "display": "number"  
                        }),
                             },
                }
    
    RETURN_TYPES = ("FLOAT",) 

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self, number, min_value, max_value, step):
        if number < min_value:
            number = min_value
        elif number > max_value:
            number = max_value
        scaled_number = (number - min_value) / (max_value - min_value)
        return (scaled_number,)
    
  
class IntNumber:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "number":("INT", {
                        "default": 0, 
                        "min": -1, #Minimum value
                        "max": 0xffffffffffffffff,
                        "step": 1, 
                        "display": "number"
                    }),
                    "min_value":("INT", {
                        "default": 0, 
                        "min": -0xffffffffffffffff, 
                        "max": 0xffffffffffffffff,
                        "step": 1, 
                        "display": "number"  
                    }),
                    "max_value":("INT", {
                            "default": 1, 
                            "min": -0xffffffffffffffff,
                            "max": 0xffffffffffffffff,
                            "step": 1, 
                            "display": "number"  
                        }),
                    "step":("INT", {
                            "default": 1, 
                            "min": -0xffffffffffffffff,
                            "max": 0xffffffffffffffff,
                            "step":1,
                            "display": "number"  
                        }),
                             },
                }
    
    RETURN_TYPES = ("INT",) 

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,number,min_value,max_value,step):
        if number < min_value:
            number= min_value
        elif number > max_value:
            number= max_value
        return (number,)

class MultiplicationNode:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "numberA":(any_type,),
                    "multiply_by":("FLOAT", {
                        "default": 0, 
                        "min": -2, #Minimum value
                        "max": 0xffffffffffffffff,
                        "step": 0.01, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    }),
                     "add_by":("FLOAT", {
                        "default": 0, 
                        "min": -2000, #Minimum value
                        "max": 0xffffffffffffffff,
                        "step": 0.01, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    })
                             },
                }
    
    RETURN_TYPES = ("FLOAT","INT",) 

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,)

    def run(self,numberA,multiply_by,add_by):
        b=int(numberA*multiply_by+add_by)
        a=float(numberA*multiply_by+add_by)
        return (a,b,) 

class TextInput:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "text": ("STRING",{"multiline": True,"default": ""}),
                             },
                }
    
    RETURN_TYPES = ("STRING",) 

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,text):
       
        return (text,)
    
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
        # print("print INPUT_TYPES",cls)
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
                "delay_by_text":("STRING",{"multiline":True,"dynamicPrompts": False,}),
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

    CATEGORY = "♾️Mixlab/Utils"
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
        print(f"延迟执行: {delay_time}")
        time.sleep(delay_time)

        # 获取结束时间戳并计算间隔
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"实际延迟时间: {elapsed_time} 秒")        

        # 根据 replace_output 决定输出值
        return (max(0, replace_value),) if replace_output == "enable" else (any_input,)
        



# app 配置节点
class AppInfo:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "name": ("STRING",{"multiline": False,"default": "Mixlab-App","dynamicPrompts": False}),
                    "input_ids":("STRING",{"multiline": True,"default": "\n".join(["1","2","3"]),"dynamicPrompts": False}),
                    "output_ids":("STRING",{"multiline": True,"default": "\n".join(["5","9"]),"dynamicPrompts": False}),
                             },

                "optional":{
                    "IMAGE": ("IMAGE",),
                    "description":("STRING",{"multiline": True,"default": "","dynamicPrompts": False}),
                    "version":("INT", {
                        "default": 1, 
                        "min": 1, 
                        "max": 10000, 
                        "step": 1, 
                        "display": "number"  
                    }),
                    "share_prefix":("STRING",{"multiline": False,"default": "","dynamicPrompts": False}),
                    "link":("STRING",{"multiline": False,"default": "https://","dynamicPrompts": False}),
                    "category":("STRING",{"multiline": False,"default": "","dynamicPrompts": False}),
                    "auto_save": (["enable","disable"],),
                }

                }
    
    RETURN_TYPES = ()
    # RETURN_NAMES = ("IMAGE",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab"

    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    # OUTPUT_IS_LIST = (True,)

    def run(self,name,input_ids,output_ids,IMAGE,description,version,share_prefix,link,category,auto_save):
        name=name[0]
        
        im=None
        if IMAGE:
            im=IMAGE[0][0]
            #TODO batch 的方式需要处理
            im=create_temp_file(im)
        # image [img,] img[batch,w,h,a] 列表里面是batch，

        input_ids=input_ids[0]
        output_ids=output_ids[0]
        description=description[0]
        version=version[0]
        share_prefix=share_prefix[0]
        link=link[0]
        category=category[0]
        
        # id=get_json_hash([name,im,input_ids,output_ids,description,version])

        return {"ui": {"json": [name,im,input_ids,output_ids,description,version,share_prefix,link,category]}, "result": ()}
    

    


class SwitchByIndex:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "A":(any_type,),
                "B":(any_type,),
                "index":("INT", {
                        "default": -1, 
                        "min": -1, 
                        "max": 1000, 
                        "step": 1, 
                        "display": "number"  
                    }),
                 "flat": (['off',"on"],),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("C",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    def run(self, A,B,index,flat):

        flat=flat[0]

        C=[]
        index=index[0]

        for a in A:    
            C.append(a)
        for b in B:
            C.append(b)

        if flat=='on':
            C=flatten_list(C)

        if index>-1:
            try:
                C=[C[index]]
            except Exception as e:
                C=[]
        
        return (C,)



class LimitNumber:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "number":(any_type,),
                "min_value":("INT", {
                        "default": 0, 
                        "min": 0, 
                        "max": 0xffffffffffffffff,
                        "step": 1, 
                        "display": "number"  
                    }),
                "max_value":("INT", {
                        "default": 1, 
                        "min": 1, 
                        "max": 0xffffffffffffffff,
                        "step": 1, 
                        "display": "number"  
                    }),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("number",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self, number, min_value, max_value):
        nn=number

        if isinstance(number, int):
            min_value=int(min_value)
            max_value=int(max_value)
        if isinstance(number, float):
            min_value=float(min_value)
            max_value=float(max_value)

        if number < min_value:
            nn= min_value
        elif number > max_value:
            nn= max_value
        
        return (nn,)



class ListStatistics:
    @staticmethod
    def count_types(lst):
        type_count = {}

        for item in lst:
            item_type = type(item).__name__
            if item_type not in type_count:
                type_count[item_type] = []

            if item_type in ['dict', 'str', 'int', 'float']:
                type_count[item_type].append(item)

        return type_count

# # 示例列表
# my_list = [1, 'hello', {'name': 'John'}, 3.14, {'age': 25}, 'world', 10]

# # 创建ListStatistics对象
# list_stats = ListStatistics()

# # 调用count_types方法进行统计
# result = list_stats.count_types(my_list)

# # 输出结果
# for item_type, values in result.items():
#     print(item_type + ':')
#     for value in values:
#         print(value)
#     print('---')

class TESTNODE_:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "ANY":(any_type,), },
                }
    
    RETURN_TYPES = (any_type,)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/__TEST"

    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    def run(self,ANY):
        print(ANY)
        # data=ANY
        list_stats = ListStatistics()

        # 调用count_types方法进行统计
        result = list_stats.count_types(ANY)
            
        return {"ui": {"data": result,"type":[str(type(ANY[0]))]}, "result": (ANY,)}



class CreateSeedNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("seed",)
  
    OUTPUT_NODE = True
    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    def run(self, seed):
        return (seed,)
    

class CreateCkptNames:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ckpt_names": ("STRING",{"multiline": True,"default": "\n".join(folder_paths.get_filename_list("checkpoints")),"dynamicPrompts": False}),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("ckpt_names",)
    
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (True,)

    # OUTPUT_NODE = True
    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    def run(self, ckpt_names):
        ckpt_names=ckpt_names.split('\n')
        ckpt_names = [name for name in ckpt_names if name.strip()]
        return (ckpt_names,)
    

class CreateSampler_names:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sampler_names": ("STRING",{"multiline": True,"default": "\n".join(comfy.samplers.KSampler.SAMPLERS),"dynamicPrompts": False}),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("sampler_names",)
    
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (True,)

    # OUTPUT_NODE = True
    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Utils"

    def run(self, sampler_names):
        sampler_names=sampler_names.split('\n')
        sampler_names = [name for name in sampler_names if name.strip()]
        return (sampler_names,)