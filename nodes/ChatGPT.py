import openai 
from swarm import Swarm, Agent

import time
import urllib.error
import re,json,os,string,random
import folder_paths
import hashlib
import codecs,sys
import importlib.util
import subprocess
import requests
from PIL import Image
from io import BytesIO
import torch
import numpy as np

python = sys.executable

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


# 从文本中提取json
def extract_json_strings(text):
    json_strings = []
    brace_level = 0
    json_str = ''
    in_json = False
    
    for char in text:
        if char == '{':
            brace_level += 1
            in_json = True
        if in_json:
            json_str += char
        if char == '}':
            brace_level -= 1
        if in_json and brace_level == 0:
            json_strings.append(json_str)
            json_str = ''
            in_json = False

    return json_strings[0] if len(json_strings)>0 else "{}"


def is_installed(package, package_overwrite=None,auto_install=True):
    is_has=False
    try:
        spec = importlib.util.find_spec(package)
        is_has=spec is not None
    except ModuleNotFoundError:
        pass

    package = package_overwrite or package

    if spec is None:
        if auto_install==True:
            print(f"Installing {package}...")
            # 清华源 -i https://pypi.tuna.tsinghua.edu.cn/simple
            command = f'"{python}" -m pip install {package}'
    
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ)

            is_has=True

            if result.returncode != 0:
                print(f"Couldn't install\nCommand: {command}\nError code: {result.returncode}")
                is_has=False
    else:
        print(package+'## OK')

    return is_has
  


# def is_installed(package):
#     try:
#         spec = importlib.util.find_spec(package)
#     except ModuleNotFoundError:
#         return False
#     return spec is not None


def get_unique_hash(string):
    hash_object = hashlib.sha1(string.encode())
    unique_hash = hash_object.hexdigest()
    return unique_hash

def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")

#  判断是否是azure服务
def is_azure_url(url):
    pattern = r'.*\.azure\.com$'
    if re.match(pattern, url):
        return True
    else:
        return False

def azure_client(key,url):
    client = openai.AzureOpenAI(
        api_key=key,
    # https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
    api_version="2023-07-01-preview",
    # https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal#create-a-resource
    azure_endpoint=url
    )
    return client

def openai_client(key,url):
    client = openai.OpenAI(
        api_key=key,
        base_url=url
    )
    return client

def ZhipuAI_client(key):
    try:
        if is_installed('zhipuai')==True:
            from zhipuai import ZhipuAI
    except:
        print("#install zhipuai error")

    client = ZhipuAI(
        api_key=key, # 填写您的 APIKey
    ) 
    return client


# 优先使用phi
def phi_sort(lst):
    return sorted(lst, key=lambda x: x.lower().count('phi'), reverse=True)

def get_llama_path():
    try:
        return folder_paths.get_folder_paths('llamafile')[0]
    except:
        return os.path.join(folder_paths.models_dir, "llamafile")

# def get_llama_models():
#     res=[]

#     model_path=get_llama_path()
#     if os.path.exists(model_path):
#         files = os.listdir(model_path)
#         for file in files:
#             if os.path.isfile(os.path.join(model_path, file)):
#                 res.append(file)
#         res=phi_sort(res)
#     return res

# llama_modes_list=get_llama_models()
# llama_modes_list=[]

# def get_llama_model_path(file_name):
#     model_path=get_llama_path()
#     mp=os.path.join(model_path,file_name)
#     return mp

# def llama_cpp_client(file_name):
#     try:
#         if is_installed('llama_cpp')==False:
#             import subprocess

#             # 安装
#             print('#pip install llama-cpp-python')
 
#             result = subprocess.run([sys.executable, '-s', '-m', 'pip', 
#                                      'install', 
#                                      'llama-cpp-python',
#                                      '--extra-index-url',
#                                      'https://abetlen.github.io/llama-cpp-python/whl/cu121'
#                                      ], capture_output=True, text=True)

#             #检查命令执行结果
#             if result.returncode == 0:
#                 print("#install success")
#                 from llama_cpp import Llama

#                 subprocess.run([sys.executable, '-s', '-m', 'pip', 
#                                      'install', 
#                                      'llama-cpp-python[server]'
#                                      ], capture_output=True, text=True)

#             else:
#                 print("#install error")
            
#         else:
#             from llama_cpp import Llama
#     except:
#         print("#install llama-cpp-python error")

#     if file_name:
#         mp=get_llama_model_path(file_name)
#         # file_name=get_llama_models()[0]
#         # model_path=os.path.join(folder_paths.models_dir, "llamafile")
#         # mp=os.path.join(model_path,file_name)

#         llm = Llama(model_path=mp, chat_format="chatml",n_gpu_layers=-1,n_ctx=512)

#         return llm


if is_installed('json_repair'):
    from json_repair import repair_json


def chat(client, model_name,messages,max_tokens=4096,temperature=0.6 ):
        print('#chat',model_name,messages)
        try_count = 0
        while True:
            try_count += 1
            try:
                if hasattr(client, "chat"):
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                else:
                    # 是llama的
                    response = client.create_chat_completion_openai_v1(
                        messages=messages,
                        # response_format={
                        #     "type": "json_object",
                        # },
                        # temperature=0.7,
                    )

                break
            except openai.AuthenticationError as ex:
                raise ex
            except (urllib.error.HTTPError, openai.OpenAIError) as ex:
                if try_count >= 3:
                    raise ex
                time.sleep(3)
                continue
        
        # print(response.keys())
        finish_reason = response.choices[0].finish_reason
        if finish_reason != "stop":
            raise RuntimeError("API finished with unexpected reason: " + finish_reason)

        content=""
        try:
            content=response.choices[0].message.content
        except:
            content=response.choices[0].delta['content']

        return content


llm_apis=[
            {
                "value": "https://api.openai.com/v1",
                "label": "openai"
            },
            {
                "value": "https://openai.api2d.net/v1",
                "label": "api2d"
            },
            # {
            #     "value": "https://docs-test-001.openai.azure.com",
            #     "label": "https://docs-test-001.openai.azure.com"
            # },
             
            {
                "value": "https://api.moonshot.cn/v1",
                "label": "Kimi"
            },
            {
                "value": "https://api.deepseek.com/v1",
                "label": "DeepSeek-V2"
            },
            {
                "value": "https://api.siliconflow.cn/v1",
                "label": "SiliconCloud"
            }]
        
llm_apis_dict = {api["label"]: api["value"] for api in llm_apis}


class ChatGPTNode:
    def __init__(self):
        # self.__client = OpenAI()
        self.session_history = []  # 用于存储会话历史的列表
        # self.seed=0
        self.system_content="You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."

    @classmethod
    def INPUT_TYPES(cls):

        model_list=[ 
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4o",
            "gpt-4o-2024-05-13",
            "gpt-4",
            "gpt-4-0314",
            "gpt-4-0613",
            "gpt-3.5-turbo-0301",
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            "qwen-turbo",
            "qwen-plus",
            "qwen-long",
            "qwen-max",
            "qwen-max-longcontext",
            "glm-4",
            "glm-3-turbo",
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
            "deepseek-chat",
            "Qwen/Qwen2-7B-Instruct",
            "THUDM/glm-4-9b-chat",
            "01-ai/Yi-1.5-9B-Chat-16K",
            "meta-llama/Meta-Llama-3.1-8B-Instruct"
                    ]
        
        return {
            "required": {
                # "api_key":("KEY", {"default": "", "multiline": True,"dynamicPrompts": False}),
                # "api_key":("STRING", {"forceInput": True,}),
               
                "prompt": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                "system_content": ("STRING", 
                                   {
                                       "default": "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible.", 
                                       "multiline": True,"dynamicPrompts": False
                                       }),
                 
                "model": ( model_list, 
                    {"default": model_list[0]}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
                "context_size":("INT", {"default": 1, "min": 0, "max":30, "step": 1}),
                "api_url":(list(llm_apis_dict.keys()), 
                    {"default": list(llm_apis_dict.keys())[0]}),
            },
             "optional":{
                    "api_key":("STRING", {"forceInput": True,}),
                    "custom_model_name":("STRING", {"forceInput": True,}), #适合自定义model
                     "custom_api_url":("STRING", {"forceInput": True,}), #适合自定义model
                },
             
        }

    RETURN_TYPES = ("STRING","STRING","STRING",)
    RETURN_NAMES = ("text","messages","session_history",)
    FUNCTION = "generate_contextual_text"
    CATEGORY = "♾️Mixlab/GPT"
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,False,)

    
    def generate_contextual_text(self,
                                #  api_key,
                                 prompt, 
                                 system_content,
                                 model, 
                                seed,
                                context_size,
                                api_url,
                                api_key=None,
                                custom_model_name=None,
                                custom_api_url=None,
                                ):
        
        if custom_model_name!=None:
            model=custom_model_name

        api_url=llm_apis_dict[api_url] if api_url in llm_apis_dict else ""

        if custom_api_url!=None:
            api_url=custom_api_url

        if api_key==None:
            api_key="lm_studio"

        # print(api_key!='',api_url,prompt,system_content,model,seed)
        # 可以选择保留会话历史以维持上下文记忆
        # 或者在此处清除会话历史 self.session_history.clear()
        # if seed!=self.seed:
        #     self.seed=seed
        #     self.session_history=[]
        
        # 把系统信息和初始信息添加到会话历史中
        if system_content:
            self.system_content=system_content
            # self.session_history=[]
            # self.session_history.append({"role": "system", "content": system_content})
        print("api_key,api_url",api_key,api_url)
        # 
        if is_azure_url(api_url):
            client=azure_client(api_key,api_url)
        else:
            # 根据用户选择的模型，设置相应的接口和模型名称
            if model == "glm-4" :
                client = ZhipuAI_client(api_key)  # 使用 Zhipuai 的接口
                print('using Zhipuai interface')
            # elif model in llama_modes_list:
            #     #
            #     client=llama_cpp_client(model)
            else :
                client = openai_client(api_key,api_url)  # 使用 ChatGPT  的接口
                # print('using ChatGPT interface',api_key,api_url)

        # 把用户的提示添加到会话历史中
        # 调用API时传递整个会话历史

        def crop_list_tail(lst, size):
            if size >= len(lst):
                return lst
            elif size==0:
                return []
            else:
                return lst[-size:]
            
        session_history=crop_list_tail(self.session_history,context_size)

        messages=[{"role": "system", "content": self.system_content}]+session_history+[{"role": "user", "content": prompt}]

        response_content = chat(client,model,messages)
        
        self.session_history=self.session_history+[{"role": "user", "content": prompt}]+[{'role':'assistant',"content":response_content}]


        # if unique_id and extra_pnginfo and "workflow" in extra_pnginfo[0]:
        #     workflow = extra_pnginfo[0]["workflow"]
        #     node = next((x for x in workflow["nodes"] if str(x["id"]) == unique_id[0]), None)
        #     if node:
        #         node["widgets_values"] = ["",
        #                          api_url, 
        #                          prompt, 
        #                          system_content,
        #                            model,
        #                            seed,
        #                            context_size]
        
        return (response_content,json.dumps(messages, indent=4),json.dumps(self.session_history, indent=4),)


class SiliconflowFreeNode:
    def __init__(self):
        # self.__client = OpenAI()
        self.session_history = []  # 用于存储会话历史的列表
        # self.seed=0
        self.system_content="You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."

    @classmethod
    def INPUT_TYPES(cls):
        model_list= [ 
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2-7B-Instruct", 
            "THUDM/glm-4-9b-chat",
            "01-ai/Yi-1.5-9B-Chat-16K",
            "meta-llama/Meta-Llama-3.1-8B-Instruct"
            ]
        return {
            "required": {
                "api_key":("STRING", {"forceInput": True,}),
                "prompt": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                "system_content": ("STRING", 
                                   {
                                       "default": "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible.", 
                                       "multiline": True,"dynamicPrompts": False
                                       }),
                "model": ( model_list, 
                    {"default": model_list[0]}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
                "context_size":("INT", {"default": 1, "min": 0, "max":30, "step": 1}),
                "max_tokens":("INT", {"default": 512, "min": 512, "max":200000, "step": 1}),
            },
               "optional":{
                    "custom_model_name":("STRING", {"forceInput": True,}), #适合自定义model
                },
        }

    RETURN_TYPES = ("STRING","STRING","STRING",)
    RETURN_NAMES = ("text","messages","session_history",)
    FUNCTION = "generate_contextual_text"
    CATEGORY = "♾️Mixlab/GPT"
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,False,)

    
    def generate_contextual_text(self,
                                api_key,
                                prompt, 
                                system_content,
                                model, 
                                seed,
                                context_size,
                                max_tokens,
                                custom_model_name=None):

        if custom_model_name!=None:
            model=custom_model_name

        api_url="https://api.siliconflow.cn/v1"
        
        # 把系统信息和初始信息添加到会话历史中
        if system_content:
            self.system_content=system_content
            # self.session_history=[]
            # self.session_history.append({"role": "system", "content": system_content})
        
        # 
        client = openai_client(api_key,api_url)  # 使用 ChatGPT  的接口
        # print('using ChatGPT interface',api_key,api_url)

        # 把用户的提示添加到会话历史中
        # 调用API时传递整个会话历史

        def crop_list_tail(lst, size):
            if size >= len(lst):
                return lst
            elif size==0:
                return []
            else:
                return lst[-size:]
            
        session_history=crop_list_tail(self.session_history,context_size)

        messages=[{"role": "system", "content": self.system_content}]+session_history+[{"role": "user", "content": prompt}]

        response_content = chat(client,model,messages,max_tokens)
        
        self.session_history=self.session_history+[{"role": "user", "content": prompt}]+[{'role':'assistant',"content":response_content}]

        return (response_content,json.dumps(messages, indent=4),json.dumps(self.session_history, indent=4),)



class SiliconflowTextToImageNode:
   
    @classmethod
    def INPUT_TYPES(cls):
        model_list= [ 
            "black-forest-labs/FLUX.1-schnell", 
            ]
        return {
            "required": {
                "api_key":("STRING", {"forceInput": True,}),
                "prompt": ("STRING", {"multiline": True,"dynamicPrompts": False}), 
                "width": ("INT", {"default": 512, "min": 512, "max": 4096, "step": 8}), 
                "height": ("INT", {"default": 512, "min": 512, "max": 4096, "step": 8}), 
                "model": ( model_list, 
                    {"default": model_list[0]}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}), 
            },
               "optional":{
                    "custom_model_name":("STRING", {"forceInput": True,}), #适合自定义model
                },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "generate_contextual_text"
    CATEGORY = "♾️Mixlab/Image"
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    
    def generate_contextual_text(self,
                                api_key,
                                prompt, 
                                width,
                                height,
                                model, 
                                seed,
                                custom_model_name=None):

        if custom_model_name!=None:
            model=custom_model_name

        url=f"https://api.siliconflow.cn/v1/{model}/text-to-image"

        headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
        }
        post_data = {
            "prompt":prompt,
            "image_size": f'{width}x{height}',
        }

        empty_img= pil2tensor(Image.new('RGB', (1, 1), color='white'))
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(post_data))
            response_data = response.json()

            if response_data.get('code') == 20021:
                return  (empty_img,)

            image_url = response_data['images'][0]['url']
             
            # Fetch the image using the image URL and read it with PIL
            image_response = requests.get(image_url)
            image = Image.open(BytesIO(image_response.content))

            image=pil2tensor(image)
            return (image,)
        except Exception as error:
            print(error)
            return (empty_img,)



class ShowTextForGPT:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True,"dynamicPrompts": False}),
            },
            "optional":{ 
                    "output_dir": ("STRING",{"forceInput": True,"default": "","multiline": True,"dynamicPrompts": False}), 
                }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "♾️Mixlab/Text"

    def run(self, text,output_dir=[""]):
        
        # 类型纠正
        texts=[]
        for t in text:
            if not isinstance(t, str):
                t = str(t)
            texts.append(t)

        text=texts

        if len(output_dir)==1 and (output_dir[0]=='' or os.path.dirname(output_dir[0])==''):
            t='\n'.join(text)
            output_dir=[
                os.path.join(folder_paths.get_temp_directory(),
                             get_unique_hash(t)+'.txt'
                             )
            ]
        elif len(output_dir)==1:
            base=os.path.basename(output_dir[0])
            t='\n'.join(text)
            if base=='' or os.path.splitext(base)[1]=='':
                base=get_unique_hash(t)+'.txt'
            output_dir=[
                os.path.join(output_dir[0],
                             base
                             )
            ]
        # elif len(output_dir)>1:

        

        if len(output_dir)==1 and len(text)>1:
            output_dir=[output_dir[0] for _ in range(len(text))]
        
        for i in range(len(text)):

            o_fp=output_dir[i]
            dirp=os.path.dirname(o_fp)
            if dirp=='':
                dirp=folder_paths.get_temp_directory()
                o_fp=os.path.join(folder_paths.get_temp_directory(),o_fp
                             )

            if not os.path.exists(dirp):
                os.mkdir(dirp)

            if not os.path.splitext(o_fp)[1].lower()=='.txt':
                o_fp=o_fp+'.txt'

            t=text[i]
            with open(o_fp, 'w') as file:
                file.write(t)

        # print(text)
        return {"ui": {"text": text}, "result": (text,)}
        


class CharacterInText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                 "text": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                 "character": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                 "start_index": ("INT", {
                    "default": 1,
                    "min": 0, #Minimum value
                    "max": 1024, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
            }
        }

    INPUT_IS_LIST = False
    RETURN_TYPES = ("INT",)
    FUNCTION = "run"
    # OUTPUT_NODE = True
    OUTPUT_IS_LIST = (False,)

    CATEGORY = "♾️Mixlab/Text"

    def run(self, text,character,start_index):
        # print(text,character,start_index)
        b=1 if character.lower() in text.lower() else 0
        
        return (b+start_index,)

class TextSplitByDelimiter:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                "delimiter":("STRING", {"multiline": False,"default":",","dynamicPrompts": False}),
                "start_index": ("INT", {
                    "default": 0,
                    "min": 0, #Minimum value
                    "max": 1000, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                 "skip_every": ("INT", {
                    "default": 0,
                    "min": 0, #Minimum value
                    "max": 10, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "max_count": ("INT", {
                    "default": 10,
                    "min": 1, #Minimum value
                    "max": 1000, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
            }
        }

    INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING",)
    FUNCTION = "run"
    # OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "♾️Mixlab/Text"

    def run(self, text,delimiter,start_index,skip_every,max_count):
         
        if delimiter=="":
            arr=[text.strip()]
        else:
            delimiter=codecs.decode(delimiter, 'unicode_escape')
            arr= [line for line in text.split(delimiter) if line.strip()]

        arr= arr[start_index:start_index + max_count * (skip_every+1):(skip_every+1)]

        return (arr,)


class JsonRepair:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_string":("STRING", {"forceInput": True,}), 
                "key":("STRING", {"multiline": False,"dynamicPrompts": False,"default": ""}),
            },
            "optional":{
                "json_string2":("STRING", {"forceInput": True,})
            },
        }

    INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING","STRING",)
    RETURN_NAMES = ("json_string","value",)
    FUNCTION = "run"
    # OUTPUT_NODE = True
    OUTPUT_IS_LIST = (False,False,)

    CATEGORY = "♾️Mixlab/GPT"

    def run(self, json_string,key="",json_string2=None):

        if not isinstance(json_string, str):
            json_string=json.dumps(json_string)
    
        json_string=extract_json_strings(json_string)
        # print(json_string)
        good_json_string = repair_json(json_string)

        # 将 JSON 字符串解析为 Python 对象
        data = json.loads(good_json_string)

        if json_string2!=None:
            if not isinstance(json_string2, str):
                json_string2=json.dumps(json_string2)
    
            json_string2=extract_json_strings(json_string2)
            # print(json_string)
            good_json_string2 = repair_json(json_string2)

            # 将 JSON 字符串解析为 Python 对象
            data2 = json.loads(good_json_string2)

            data={**data, **data2}


        v=""
        if key!="" and (key in data):
            v=data[key]

        # 将 Python 对象转换回 JSON 字符串，确保中文字符不被转义
        json_str_with_chinese = json.dumps(data, ensure_ascii=False)

        return (json_str_with_chinese,v,)
    

# 以下为固定提示词的LLM节点示例
class SimulateDevDesignDiscussions:
    
    @classmethod
    def INPUT_TYPES(cls):

        model_list=[ 
            "gpt-4o",
            "gpt-4o-2024-05-13",
            "gpt-4",
            "gpt-4-0314",
            "gpt-4-0613",
            "qwen-turbo",
            "qwen-plus",
            "qwen-long",
            "qwen-max",
            "qwen-max-longcontext",
            "glm-4",
            "glm-3-turbo",
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
            "deepseek-chat",
            "Qwen/Qwen2-7B-Instruct",
            "THUDM/glm-4-9b-chat",
            "01-ai/Yi-1.5-9B-Chat-16K"
                    ]
        
        return {
            "required": {
                "subject": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                "model": ( model_list, 
                    {"default": model_list[0]}),
                "api_url":(list(llm_apis_dict.keys()), 
                    {"default": list(llm_apis_dict.keys())[0]}),
            },
             "optional":{
                    "api_key":("STRING", {"forceInput": True,}),
                    "custom_model_name":("STRING", {"forceInput": True,}), #适合自定义model
                     "custom_api_url":("STRING", {"forceInput": True,}), #适合自定义model
                },
             
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "generate_contextual_text"
    CATEGORY = "♾️Mixlab/GPT"
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def generate_contextual_text(self,
                                 subject, 
                                 model, 
                                api_url,
                                api_key=None,
                                custom_model_name=None,
                                custom_api_url=None,
                                ):
        
        # 设置黄色文本的ANSI转义序列
        YELLOW = "\033[33m"
        # 重置文本颜色的ANSI转义序列
        RESET = "\033[0m"

        if custom_model_name!=None:
            model=custom_model_name

        api_url=llm_apis_dict[api_url] if api_url in llm_apis_dict else ""

        if custom_api_url!=None:
            api_url=custom_api_url

        if api_key==None:
            api_key="lm_studio"

        print("api_key,api_url",api_key,api_url)
        # 
        if is_azure_url(api_url):
            client=azure_client(api_key,api_url)
        else:
            # 根据用户选择的模型，设置相应的接口和模型名称
            if model == "glm-4" :
                client = ZhipuAI_client(api_key)  # 使用 Zhipuai 的接口
                print('using Zhipuai interface')
            else :
                client = openai_client(api_key,api_url)  # 使用 ChatGPT  的接口
               
  
        
        # 以下为多智能体框架
        client = Swarm(client=client)

        # 定义两个代理：软件系统架构师和设计师
        software_architect_agent = Agent(
            name="Software Architect",
            instructions='''用脱口秀的风格回答编程问题，简短且口语化。

        输出格式
        ====

        *   答案格式：`程序员：xxxxxxxxx`

        示例
        ==

        **输入：**  
        如何优化代码性能？

        **输出：**  
        程序员：兄弟，先把那些循环里的debug信息删掉，CPU都快哭了。'''
        )

        designer_agent = Agent(
            name="Designer",
            instructions='''回答问题时，请扮演一位具有多年空间设计和用户体验设计经验的设计师。你的回答应当天马行空，但又富有深度，带有苏格拉底的思考方式，并且使用脱口秀的风格。回答要简短且非常口语化。格式如下：

        设计师：\[回答内容\]

        Output Format
        =============

        *   回答应当使用“设计师：\[回答内容\]”的格式。
        *   回答应当简短、口语化，富有创意和深度。

        Examples
        ========

        **Example 1:**

        主持人：你觉得未来的家会是什么样子？

        设计师：未来的家？想象一下，房子会像变形金刚一样，随时变形满足你的需求。今天是健身房，明天是电影院，后天是游戏场。家不再是四面墙，而是一个随心所欲的魔法空间。

        **Example 2:**

        主持人：你怎么看待极简主义设计？

        设计师：极简主义？就像吃寿司，去掉所有不必要的装饰，只留下最精华的部分。让空间呼吸，让心灵自由。

        **Example 3:**

        主持人：你觉得色彩在设计中有多重要？

        设计师：色彩？哦，那可是设计的灵魂！就像人生中的调味料，一点红色让你激情澎湃，一点蓝色让你心如止水。色彩决定了空间的情绪基调。'''
        )

        # 定义一个函数，用于转移问题到designer_agent
        def transfer_to_designer_agent():
            return designer_agent

        # 将转移函数添加到软件系统架构师和设计师的函数列表中
        software_architect_agent.functions.append(transfer_to_designer_agent)

        # 问题生成
        host_agent = Agent(
            name="Host",
            instructions='''
        为播客的主持人生成4到5个问题，这些问题有些是针对设计师问的，有些是针对程序员问的。

        *   主持人：你知道如何开发一款APP产品，从想法到上线吗？
        *   主持人：站在设计师的角度，你怎么看？
        *   主持人：不知道程序员又是怎么想的呢？
        *   主持人：感谢大家的参与，今天收获蛮大的

        Steps
        =====

        1.  确定问题的对象：设计师或程序员。
        2.  根据对象设计相关的问题，确保问题的多样性和深度。
        3.  整理问题，使其符合播客主持人的风格和语气。

        Output Format
        =============

        问题列表，每个问题以“主持人：”开头，不要出现序号。

        Examples
        ========

        *   主持人：作为一名设计师，你是如何开始一个新项目的？
        *   主持人：程序员在开发过程中遇到的最大挑战是什么？
        *   主持人：设计师在团队协作中扮演什么角色？
        *   主持人：程序员如何确保代码的质量和稳定性？
        *   主持人：感谢大家的参与，今天的讨论非常有意义。

        Notes
        =====

        *   确保问题针对不同的角色（设计师和程序员）。
        *   保持问题的多样性，涵盖从项目开始到完成的各个阶段。
        *   确保问题能引导出深入的讨论和见解。
        ''')


        response = client.run(agent=host_agent, messages=[{
            "role":"user",
            "content":f"主题是‘{subject}’"
        }],model_override=model)

        content=response.messages[-1]["content"]
        print(f"{YELLOW}{content}{RESET}")

        texts=content.split("\n")

        # texts='''
        # 主持人：你知道如何开发一款APP产品，从想法到上线吗？
        # 主持人：站在设计师的角度，你怎么看？
        # 主持人：不知道程序员又是怎么想的呢？
        # 主持人：感谢大家的参与，今天收获蛮大的
        # '''.split("\n")

        messages=[]

        texts = [text.strip() for text in texts if text.strip()]

        result=[]

        for text in texts:
            messages.append({
                "role": "user",
                "content": text
            })

            # 运行客户端，使用软件系统架构师作为初始代理
            response = client.run(agent=software_architect_agent, messages=messages,model_override=model)

            print(f"{text}")
            result.append(text)

            # 输出最后一个响应消息的内容
            content=response.messages[-1]["content"]
            print(f"{YELLOW}{content}{RESET}")
            
            result.append(content)

            messages.append({
                "role":"assistant",
                "content":content
            })

        
        return ("\n".join(result),)

