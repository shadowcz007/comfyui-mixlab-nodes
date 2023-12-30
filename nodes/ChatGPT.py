import openai 
import time
import urllib.error
import re,json

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



def chat(client, model_name,messages ):

        try_count = 0
        while True:
            try_count += 1
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages
                )
                break
            except openai.AuthenticationError as ex:
                raise ex
            except (urllib.error.HTTPError, openai.OpenAIError) as ex:
                if try_count >= 3:
                    raise ex
                time.sleep(3)
                continue

        finish_reason = response.choices[0].finish_reason
        if finish_reason != "stop":
            raise RuntimeError("API finished with unexpected reason: " + finish_reason)

        content=""
        try:
            content=response.choices[0].message.content
        except:
            content=response.choices[0].delta['content']

        return content


class ChatGPTNode:
    def __init__(self):
        # self.__client = OpenAI()
        self.session_history = []  # 用于存储会话历史的列表
        # self.seed=0
        self.system_content="You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key":("KEY", {"default": "", "multiline": True}),
                "api_url":("URL", {"default": "", "multiline": True}),
                "prompt": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                "system_content": ("STRING", 
                                   {
                                       "default": "You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible.", 
                                       "multiline": True,"dynamicPrompts": False
                                       }),
                "model": (["gpt-3.5-turbo","gpt-35-turbo","gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "gpt-4-0613","gpt-4-1106-preview"], 
                          {"default": "gpt-3.5-turbo"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
                "context_size":("INT", {"default": 1, "min": 0, "max":30, "step": 1}),
            },
             "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
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
                                 api_url, 
                                 prompt, 
                                 system_content,
                                   model, 
                                   seed,context_size,unique_id = None, extra_pnginfo=None):
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
        
        # 
        if is_azure_url(api_url):
            client=azure_client(api_key,api_url)
        else:
            client=openai_client(api_key,api_url)
            print('openai url')

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



class ShowTextForGPT:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True,"dynamicPrompts": False}),
            }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "♾️Mixlab/GPT"

    def run(self, text):
        # print(session_history)
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

    CATEGORY = "♾️Mixlab/GPT"

    def run(self, text,character,start_index):
        # print(text,character,start_index)
        b=1 if character in text else 0
        
        return (b+start_index,)

