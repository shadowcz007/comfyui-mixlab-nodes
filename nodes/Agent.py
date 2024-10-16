import openai 
import time
import urllib.error
import re,json,os,string,random
import folder_paths
import hashlib
import sys
import importlib.util
import subprocess

import torch
import numpy as np

python = sys.executable

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

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
  

if is_installed('json_repair'):
    from json_repair import repair_json

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

# text2json
def text_to_json(text):
    text=extract_json_strings(text)
    good_json_string = repair_json(text)
    # 将 JSON 字符串解析为 Python 对象
    data = json.loads(good_json_string)
    return data


def save_to_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
            print(e)

def read_from_json(file_path):
    data = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:  # 使用 'r' 模式打开文件
            data = json.load(f)
    except Exception as e:
        print('#read_from_json', e)
        return None
    return data


default_agent={
                    "username":"shadow",
                    "profile_id":"ML000",
                    "skills":"Design Hacker,Programmer,Architect,Experience Designer".split(",")
                }


def create_default_file(agent_dir):
    fp=os.path.join(agent_dir,'shadow.json')
    if not os.path.exists(fp):
        save_to_json(fp,default_agent)

def get_social_profile_dir():
    try:
        return folder_paths.get_folder_paths('agent')[0]
    except:
        agent_dir=os.path.join(folder_paths.models_dir, "agent")
        if not os.path.exists(agent_dir):
            os.makedirs(agent_dir, exist_ok=True)
            create_default_file(agent_dir)
        return agent_dir

def save_social_profile_config(agent_dir,file_name,data):
     save_to_json(os.path.join(agent_dir,file_name),data)


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


if is_installed('swarm','git+https://github.com/openai/swarm.git'):
    from swarm import Swarm, Agent


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


# 以下为固定提示词的LLM节点示例
class SimulateDevDesignDiscussions:
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "subject": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                "model": ( model_list, 
                    {"default": model_list[0]}),
                "api_url":(list(llm_apis_dict.keys()), 
                    {"default": list(llm_apis_dict.keys())[0]}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
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
    CATEGORY = "♾️Mixlab/Agent"
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def generate_contextual_text(self,
                                 subject, 
                                 model, 
                                api_url,
                                seed,
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
        
        # 定义一个函数，用于转移问题到designer_agent
        def transfer_to_designer_agent():
            return designer_agent

        # 将转移函数添加到软件系统架构师和设计师的函数列表中
        software_architect_agent.functions.append(transfer_to_designer_agent)

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



class AvatarGeneratorAgent:
    
    @classmethod
    def INPUT_TYPES(cls):

        return {
            "required": {
                "subject": ("STRING", {"multiline": True,"dynamicPrompts": False}),
                "social_profile":("STRING", {"forceInput": True}),
                "model": ( model_list, 
                    {"default": model_list[0]}),
                "api_url":(list(llm_apis_dict.keys()), 
                    {"default": list(llm_apis_dict.keys())[0]}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1}),
            },
             "optional":{
                    "api_key":("STRING", {"forceInput": True,}),
                    "custom_model_name":("STRING", {"forceInput": True,}), #适合自定义model
                     "custom_api_url":("STRING", {"forceInput": True,}), #适合自定义model
                },
             
        }

    RETURN_TYPES = ("STRING","STRING","STRING",)
    RETURN_NAMES = ("subject","result","role_desc",)
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Agent"

    def run(self, subject,  social_profile,  model, 
              api_url, seed, api_key=None, custom_model_name=None, custom_api_url=None):
        
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

        # 定义1个代理：生成器

        # instructions
        def generator_instructions(context_variables):
            # user = context_variables.get("name", "User")
            user=json.dumps(context_variables)
            return f'''根据用户的背景信息{user},生成角色新的技能挑战，欢迎并根据提供的信息创意性地整合和演变技能挑战，包含任务控制在3个以内。'''+'''
步骤
==

1.  **欢迎用户**

    *   欢迎用户并提及其用户名。
    *   简要介绍涉及到的信息要点（如果有功能和用途等）。
2.  **生成技能挑战**

    *   根据用户的技能，设计创意性的技能挑战。
    *   每个挑战需要整合用户的多个技能。
    *   挑战数量控制在3个以内。

输出格式
====

*   输出格式为段落。每个段落包含欢迎信息、涉及到的信息要点。

示例1
==

**输入：**

{
  "username": "shadow",
  "profile_id": "ML000",
  "skills": ["Design Hacker", "Programmer", "Architect", "Experience Designer", "设计黑客"]
}

信息：Mothbox是一款低成本、高性能的昆虫监测设备，旨在帮助野外生物学家在丛林深处进行部署，同时也适合在家中研究生物多样性。所有物理设计、电子原理图、Pi脚本和昆虫识别的人工智能都是免费开源的，用户可以自行构建、分享和改进。Mothbox利用超高分辨率传感器和开源AI脚本进行昆虫监测，提供高度本地化的环境健康数据，特别适用于研究飞蛾和甲虫等高度多样化的昆虫。


**输出：**  
欢迎shadow！我们很高兴你对Mothbox感兴趣。Mothbox是一款低成本、高性能的昆虫监测设备，旨在帮助野外生物学家在丛林深处进行部署，同时也适合在家中研究生物多样性。所有物理设计、电子原理图、Pi脚本和昆虫识别的人工智能都是免费开源的，用户可以自行构建、分享和改进。

根据你的技能，我们为你设计了以下创意性技能挑战：

1.  **设计和构建一个模块化的Mothbox外壳**：利用你的建筑师和设计黑客技能，创造一个可以适应不同环境和需求的模块化外壳设计。
2.  **开发一个用户友好的界面**：作为一名程序员和体验设计师，设计一个直观的用户界面，使用户可以轻松地配置和监测Mothbox。
3.  **优化昆虫识别算法**：结合你的程序员和设计黑客技能，改进现有的开源AI脚本，提高昆虫识别的准确性和速度。

我们期待看到你如何运用你的多重技能来挑战和改进Mothbox！



示例2
==

**输入：**


{
  "username": "meadow",
  "profile_id": "ML002",
  "skills": ["体验设计师", "作家"]
}

信息：苹果发布新的iPad mini，AI功能来了


**输出：**  
欢迎meadow！我们很高兴你对苹果发布的新的iPad mini感兴趣。新的iPad mini不仅带来了更强大的硬件，还加入了令人期待的AI功能，进一步提升了用户体验。

根据你的技能，我们为你设计了以下创意性技能挑战：

1.  **设计一个AI驱动的用户体验测试平台**：利用你的体验设计师技能，创建一个平台，使用户可以通过iPad mini的AI功能进行用户体验测试，收集和分析数据，优化应用和服务。

2.  **撰写一篇关于AI在移动设备上应用的深度文章**：作为一名作家，撰写一篇详细的文章，探讨AI功能如何改变了iPad mini的使用体验，并预测未来的发展趋势。

3.  **开发一个互动的iPad mini用户指南**：结合你的体验设计师和作家技能，设计并编写一个互动的用户指南，使新用户可以轻松上手iPad mini，充分利用其AI功能。

我们期待看到你如何运用你的多重技能来挑战和改进iPad mini的用户体验！
'''.strip()

        # 用于更新用户信息
        def update_account_details(context_variables: dict):
            profile_id = context_variables.get("profile_id", None)
            username = context_variables.get("username", None)
            skills = context_variables.get("skills", None)
            file_name=context_variables.get('file_name','agent.json')
            if skills:
                skills=",".join(skills)
            print(f"Account Details: {username} {profile_id} {skills}")

            # 
            save_social_profile_config(get_social_profile_dir(),file_name,context_variables)
            return "Success"

        generator_agent = Agent(
            name="generator_agent",
            instructions=generator_instructions,
            functions=[update_account_details],
        )

        # dict
        context_variables = json.loads(social_profile)

        response = client.run(
            messages=[{"role": "user", "content":subject}],
            agent=generator_agent,
            context_variables=context_variables,
            model_override=model
        )
        result=response.messages[-1]["content"]
        print(f"{YELLOW}{result}{RESET}")


        # 答案生成

        def answer_instructions(context_variables):
            # user = context_variables.get("name", "User")
            user=json.dumps(context_variables)

            return '''
                根据提供的金句，先判断属于哪个领域的信息，然后选择最不相关的其他领域里的新概念，结合用户的'''+user+'''信息，生成一个新的职业标签。目的是激发新灵感的产生。

        Steps
        =====

        1.  **判断领域**: 根据提供的金句，判断其所属领域。
        2.  **选择不相关概念**: 从其他领域中选择一个最不相关的新概念。
        3.  **结合用户信息**: 将上述步骤中的信息与用户的user信息结合。
        4.  **生成职业标签**: 生成一个新的职业标签，激发新灵感。

        Output Format
        =============

        用JSON格式输出新的职业标签:

        ```
        { "result": "new_tag" }
        ```

        Examples
        ========

        **Example 1:**

        *   Input:
            *   金句: "科技是第一生产力"
            *   user信息: "对金融科技有浓厚兴趣"
        *   Output:

            ```
            { "result": "金融科技园艺师" }
            ```

        **Example 2:**

        *   Input:
            *   金句: "艺术是心灵的镜子"
            *   user信息: "喜欢编程和数据分析"
        *   Output:

            ```
            { "result": "数据分析画家" }
            ```

        Notes
        =====

        *   确保新概念与原领域尽量不相关。
        *   职业标签应有创意且能激发灵感。'''.strip()

        answer_agent = Agent(
                    name="Answer",
                    instructions=answer_instructions)

        response = client.run(
            messages=[{"role": "user", "content": result}],
            agent=answer_agent,
            context_variables=context_variables,
            model_override=model
        )
        content=response.messages[-1]["content"]

        answer_json=text_to_json(content)

        print(f"{YELLOW}{content}{RESET}") 

        
        new_tag=None
        if "result" in answer_json:
            new_tag=answer_json['result']
            context_variables['skills'].append(new_tag)

        role_desc=""

        if new_tag!=None:
            response = client.run(
                messages=[{"role": "user", "content": f"请80%参考{new_tag},20%特征参考我的数字分身信息，描绘一张游戏人物的角色设计图，直接输出角色设计图的描述给我，不要多余的不相关信息"}],
                agent=generator_agent,
                context_variables=context_variables,
                model_override=model
            )

            role_desc=response.messages[-1]["content"]
            print(f"{YELLOW}{role_desc}{RESET}") 


        response = client.run(
            messages=[{"role": "user", "content": "请更新我的数字分身信息"}],
            agent=generator_agent,
            context_variables=context_variables,
            model_override=model
        )

        content=response.messages[-1]["content"]
        print(f"{YELLOW}{content}{RESET}")
        
        return (subject,result,role_desc,)

