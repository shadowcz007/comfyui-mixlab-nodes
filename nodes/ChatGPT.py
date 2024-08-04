import openai 
import time
import urllib.error
import re,json,os,string,random
import folder_paths
import hashlib
import codecs,sys
import importlib.util


def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None


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
        if is_installed('zhipuai')==False:
            import subprocess

            # 安装
            print('#pip install zhipuai')

            result = subprocess.run([sys.executable, '-s', '-m', 'pip', 'install', 'zhipuai'], capture_output=True, text=True)

            #检查命令执行结果
            if result.returncode == 0:
                print("#install success")
                from zhipuai import ZhipuAI
            else:
                print("#install error")
            
        else:
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

    


def chat(client, model_name,messages ):
        print('#chat',model_name,messages)
        try_count = 0
        while True:
            try_count += 1
            try:
                if hasattr(client, "chat"):
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages
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
                                seed,context_size,custom_model_name=None):

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

        response_content = chat(client,model,messages)
        
        self.session_history=self.session_history+[{"role": "user", "content": prompt}]+[{'role':'assistant',"content":response_content}]

        return (response_content,json.dumps(messages, indent=4),json.dumps(self.session_history, indent=4),)




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
