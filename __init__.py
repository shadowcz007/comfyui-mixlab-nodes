#
import os
import subprocess
import importlib.util
import sys,json
import urllib
import hashlib
import datetime


python = sys.executable


from server import PromptServer

try:
    import aiohttp
    from aiohttp import web
except ImportError:
    print("Module 'aiohttp' not installed. Please install it via:")
    print("pip install aiohttp")
    print("or")
    print("pip install -r requirements.txt")
    sys.exit()
   
def is_installed(package, package_overwrite=None):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        pass

    package = package_overwrite or package

    if spec is None:
        print(f"Installing {package}...")
        # 清华源 -i https://pypi.tuna.tsinghua.edu.cn/simple
        command = f'"{python}" -m pip install {package}'
  
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ)

        if result.returncode != 0:
            print(f"Couldn't install\nCommand: {command}\nError code: {result.returncode}")
    else:
        print(package+'## OK')
        
try:
    import OpenSSL
except ImportError:
    print("Module 'pyOpenSSL' not installed. Please install it via:")
    print("pip install pyOpenSSL")
    print("or")
    print("pip install -r requirements.txt")
    is_installed('pyOpenSSL')
    sys.exit()

try:
    import watchdog
except ImportError:
    print("Module 'watchdog' not installed. Please install it via:")
    print("pip install watchdog")
    print("or")
    print("pip install -r requirements.txt")
    is_installed('watchdog')
    sys.exit()



def install_openai():
    # Helper function to install the OpenAI module if not already installed
    try:
        importlib.import_module('openai')
    except ImportError:
        import pip
        pip.main(['install', 'openai'])

install_openai()


current_path = os.path.abspath(os.path.dirname(__file__))



def calculate_md5(string):
    encoded_string = string.encode()
    md5_hash = hashlib.md5(encoded_string).hexdigest()
    return md5_hash


def create_key(key_p,crt_p):
    import OpenSSL
    # 生成自签名证书
    # 生成私钥
    private_key = OpenSSL.crypto.PKey()
    private_key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

    # 生成CSR
    csr = OpenSSL.crypto.X509Req()
    csr.get_subject().CN = "mixlab.com"  # 设置证书的通用名称
    csr.set_pubkey(private_key)
    csr.sign(private_key, "sha256")
    # 生成证书
    certificate = OpenSSL.crypto.X509()
    certificate.set_serial_number(1)
    certificate.gmtime_adj_notBefore(0)
    certificate.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 设置证书的有效期
    certificate.set_issuer(csr.get_subject())
    certificate.set_subject(csr.get_subject())
    certificate.set_pubkey(csr.get_pubkey())
    certificate.sign(private_key, "sha256")
    # 保存私钥到文件
    with open(key_p, "wb") as f:
        f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key))

    # 保存证书到文件
    with open(crt_p, "wb") as f:
        f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate))
    return


def create_for_https():
    # print("#####path::", current_path)
    https_key_path=os.path.join(current_path, "https")
    crt=os.path.join(https_key_path, "certificate.crt")
    key=os.path.join(https_key_path, "private.key")
    # print("##https_key_path", crt,key)
    if not os.path.exists(https_key_path):
        # 使用mkdir()方法创建新目录
        os.mkdir(https_key_path)
    if not os.path.exists(crt):
        create_key(key,crt)

    print('https_key OK: ', crt,key)
    return (crt,key)



# workflow  目录下的所有json
def read_workflow_json_files_all(folder_path):
    print('#read_workflow_json_files_all',folder_path)
    json_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))

    data = []
    for file_path in json_files:
        try:
            with open(file_path) as json_file:
                json_data = json.load(json_file)
                creation_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
                numeric_timestamp = creation_time.timestamp()
                file_info = {
                    'filename': os.path.basename(file_path),
                    'category': os.path.dirname(file_path),
                    'data': json_data,
                    'date': numeric_timestamp
                }
                data.append(file_info)
        except Exception as e:
            print(e)
    
    sorted_data = sorted(data, key=lambda x: x['date'], reverse=True)
    return sorted_data

# workflow  
def read_workflow_json_files(folder_path ):
    json_files = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            json_files.append(filename)

    data = []
    for file in json_files:
        file_path = os.path.join(folder_path, file)
        try:
            with open(file_path) as json_file:
                json_data = json.load(json_file)
                creation_time=datetime.datetime.fromtimestamp(os.path.getctime(file_path))
                numeric_timestamp = creation_time.timestamp()
                file_info = {
                    'filename': file,
                    'data': json_data,
                    'date': numeric_timestamp
                }
                data.append(file_info)
        except Exception as e:
            print(e)
    sorted_data = sorted(data, key=lambda x: x['date'], reverse=True)
    return sorted_data

def get_workflows():
    # print("#####path::", current_path)
    workflow_path=os.path.join(current_path, "workflow")
    # print('workflow_path: ',workflow_path)
    if not os.path.exists(workflow_path):
        # 使用mkdir()方法创建新目录
        os.mkdir(workflow_path)
    workflows=read_workflow_json_files(workflow_path)
    return workflows

def get_my_workflow_for_app(filename="my_workflow_app.json",category="",is_all=False):
    app_path=os.path.join(current_path, "app")
    if not os.path.exists(app_path):
        os.mkdir(app_path)

    category_path=os.path.join(app_path,category)
    if not os.path.exists(category_path):
        os.mkdir(category_path)

    apps=[]
    if filename==None:

        #TODO 支持目录内遍历 
        if is_all:
            data=read_workflow_json_files_all(category_path)
        else:
            data=read_workflow_json_files(category_path)
        
        i=0
        for item in data:
            # print(item)
            try:
                x=item["data"]
                # 管理员模式，读取全部数据
                if i==0 or is_all:
                    apps.append({
                        "filename":item["filename"],
                        # "category":item['category'],
                        "data":x,
                        "date":item["date"],
                    })
                else:
                    category=''
                    input=None
                    output=None
                    if 'category' in x['app']:
                        category=x['app']['category']
                    if 'input' in x['app']:
                        input=x['app']['input']
                    if 'output' in x['app']:
                        output=x['app']['output']
                    apps.append({
                        "filename":item["filename"],
                        "category":category,
                        "data":{
                            "app":{
                                "category":category,
                                "description":x['app']['description'],
                                "filename":(x['app']['filename'] if 'filename' in x['app'] else "") ,
                                "icon":(x['app']['icon'] if 'icon' in x['app'] else None),
                                "name":x['app']['name'],
                                "version":x['app']['version'],
                                "input":input,
                                "output":output
                            }
                        },
                        "date":item["date"]
                    })
                i+=1
            except Exception as e:
                print("发生异常：", str(e))
    else:
        app_workflow_path=os.path.join(category_path, filename)
        # print('app_workflow_path: ',app_workflow_path)
        try:
            with open(app_workflow_path) as json_file:
                apps = [{
                    'filename':filename,
                    'data':json.load(json_file)
                }]
        except Exception as e:
            print("发生异常：", str(e))
        
        if len(apps)==1 and category!='' and category!=None:
            data=read_workflow_json_files(category_path)
            
            for item in data:
                x=item["data"]
                # print(apps[0]['filename'] ,item["filename"])
                if apps[0]['filename']!=item["filename"]:
                    category=''
                    input=None
                    output=None
                    if 'category' in x['app']:
                        category=x['app']['category']
                    if 'input' in x['app']:
                        input=x['app']['input']
                    if 'output' in x['app']:
                        output=x['app']['output']
                    apps.append({
                        "filename":item["filename"],
                        # "category":category,
                        "data":{
                            "app":{
                                "category":category,
                                "description":x['app']['description'],
                                "filename":(x['app']['filename'] if 'filename' in x['app'] else "") ,
                                "icon":(x['app']['icon'] if 'icon' in x['app'] else None),
                                "name":x['app']['name'],
                                "version":x['app']['version'],
                                "input":input,
                                "output":output
                            }
                        },
                        "date":item["date"]
                    })

    return apps

def save_workflow_json(data):
    workflow_path=os.path.join(current_path, "workflow/my_workflow.json")
    with open(workflow_path, 'w') as file:
        json.dump(data, file)
    return workflow_path

def save_workflow_for_app(data,filename="my_workflow_app.json",category=""):
    app_path=os.path.join(current_path, "app")
    if not os.path.exists(app_path):
        os.mkdir(app_path)

    category_path=os.path.join(app_path,category)
    if not os.path.exists(category_path):
        os.mkdir(category_path)
    
    app_workflow_path=os.path.join(category_path, filename)
 
    try:
        output_str = json.dumps(data['output'])
        data['app']['id']=calculate_md5(output_str)
        # id=data['app']['id']
    except Exception as e:
        print("发生异常：", str(e))
    
    with open(app_workflow_path, 'w') as file:
        json.dump(data, file)
    return filename

def get_nodes_map():
    # print("#####path::", current_path)
    data_path=os.path.join(current_path, "data")
    print('data_path: ',data_path)
    # if not os.path.exists(data_path):
    #     # 使用mkdir()方法创建新目录
    #     os.mkdir(data_path)
    json_data={}
    nodes_map=os.path.join(current_path, "data/extension-node-map.json")
    if os.path.exists(nodes_map):
        with open(nodes_map) as json_file:
            json_data = json.load(json_file)

    return json_data


# 保存原始的 get 方法
_original_request = aiohttp.ClientSession._request

# 定义新的 get 方法
async def new_request(self, method, url, *args, **kwargs):
   # 检查环境变量以确定是否使用代理
    proxy = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY') or os.environ.get('http_proxy') or os.environ.get('https_proxy') 
    # print('Proxy Config:',proxy)
    if proxy and 'proxy' not in kwargs:
        kwargs['proxy'] = proxy
        print('Use Proxy:',proxy)
    # 调用原始的 _request 方法
    return await _original_request(self, method, url, *args, **kwargs)

# 应用 Monkey Patch
aiohttp.ClientSession._request = new_request
import socket

async def check_port_available(address, port):
    #检查端口是否可用
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((address, port))
            return True
        except socket.error:
            return False

# https
async def new_start(self, address, port, verbose=True, call_on_start=None):
    try:
        runner = web.AppRunner(self.app, access_log=None)
        await runner.setup()

        if not await check_port_available(address, port):
            raise RuntimeError(f"Port {port} is already in use.")

        site = web.TCPSite(runner, address, port)
        await site.start()

        import ssl
        crt, key = create_for_https()
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(crt, key)

        success = False
        for i in range(10):  # 尝试最多10次
            if await check_port_available(address, port + 1 + i):
                https_port = port + 1 + i
                site2 = web.TCPSite(runner, address, https_port, ssl_context=ssl_context)
                await site2.start()
                success = True
                break

        if not success:
            raise RuntimeError(f"Ports {port + 1} to {port + 10} are all in use.")

        if address == '':
            address = '0.0.0.0'
        if verbose:
            print("\033[93mStarting server\n")
            print("\033[93mTo see the GUI go to: http://{}:{}".format(address, port))
            print("\033[93mTo see the GUI go to: https://{}:{}\033[0m".format(address, https_port))
        if call_on_start is not None:
            call_on_start(address, port)

    except Exception as e:
        print(f"Error starting the server: {e}")

        # import webbrowser
        # if os.name == 'nt' and address == '0.0.0.0':
        #     address = '127.0.0.1'
        # webbrowser.open(f"https://{address}")
        # webbrowser.open(f"http://{address}:{port}")


PromptServer.start=new_start

# 创建路由表
routes = PromptServer.instance.routes

@routes.post('/mixlab')
async def mixlab_hander(request):
    config=os.path.join(current_path, "nodes/config.json")
    data={}
    try:
        if os.path.exists(config):
            with open(config, 'r') as f:
                data = json.load(f)
                # print(data)
    except Exception as e:
            print(e)
    return web.json_response(data)


@routes.get('/mixlab/app')
async def mixlab_app_handler(request):
    html_file = os.path.join(current_path, "web/index.html")
    if os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_data = f.read()
            return web.Response(text=html_data, content_type='text/html')
    else:
        return web.Response(text="HTML file not found", status=404)
    

@routes.post('/mixlab/workflow')
async def mixlab_workflow_hander(request):
    data = await request.json()
    result={}
    try:
        if 'task' in data:
            if data['task']=='save':
                file_path=save_workflow_json(data['data'])
                result={
                    'status':'success',
                    'file_path':file_path
                }
            elif data['task']=='save_app':
                category=""
                if "category" in data:
                    category=data['category']
                file_path=save_workflow_for_app(data['data'],data['filename'],category)
                result={
                    'status':'success',
                    'file_path':file_path
                }
            elif data['task']=='my_app':
                filename=None
                category=""
                admin=False
                if 'filename' in data:
                    filename=data['filename']
                if 'category' in data:
                    category=data['category']
                if 'admin' in data:
                    admin=data['admin']
                result={
                    'data':get_my_workflow_for_app(filename,category,admin),
                    'status':'success',
                }
            elif data['task']=='list':
                result={
                    'data':get_workflows(),
                    'status':'success',
                }
    except Exception as e:
            print(e)

    return web.json_response(result)

@routes.post('/mixlab/nodes_map')
async def nodes_map_hander(request):
    data = await request.json()
    result={}
    try: 
        result={
            'data':get_nodes_map(),
            'status':'success',
                }
    except Exception as e:
            print(e)

    return web.json_response(result)


# 扩展api接口
# from server import PromptServer
# from aiohttp import web

# @routes.post('/ws_image')
# async def my_hander_method(request):
#     post = await request.post()
#     x = post.get("something")
#     return web.json_response({})


# 导入节点
from .nodes.PromptNode import EmbeddingPrompt,RandomPrompt,PromptSlide,PromptSimplification,PromptImage,JoinWithDelimiter
from .nodes.ImageNode import SaveImageToLocal,SplitImage,GridOutput,GetImageSize_,MirroredImage,ImageColorTransfer,NoiseImage,TransparentImage,GradientImage,LoadImagesFromPath,LoadImagesFromURL,ResizeImage,TextImage,SvgImage,Image3D,ShowLayer,NewLayer,MergeLayers,CenterImage,AreaToMask,SmoothMask,SplitLongMask,ImageCropByAlpha,EnhanceImage,FaceToMask
from .nodes.Vae import VAELoader,VAEDecode
from .nodes.ScreenShareNode import ScreenShareNode,FloatingVideo
from .nodes.Clipseg import CLIPSeg,CombineMasks
from .nodes.ChatGPT import ChatGPTNode,ShowTextForGPT,CharacterInText
from .nodes.Audio import GamePal,SpeechRecognition,SpeechSynthesis
from .nodes.Utils import CreateLoraNames,CreateSampler_names,CreateCkptNames,CreateSeedNode,TESTNODE_,AppInfo,IntNumber,FloatSlider,TextInput,ColorInput,FontInput,TextToNumber,DynamicDelayProcessor,LimitNumber,SwitchByIndex,MultiplicationNode
from .nodes.Mask import OutlineMask,FeatheredMask


# 要导出的所有节点及其名称的字典
# 注意：名称应全局唯一
NODE_CLASS_MAPPINGS = {
    "AppInfo":AppInfo,
    "TESTNODE_":TESTNODE_,
    "RandomPrompt":RandomPrompt,
    "EmbeddingPrompt":EmbeddingPrompt,
    "PromptSlide":PromptSlide,
    "PromptSimplification":PromptSimplification,
    "PromptImage":PromptImage,
    "MirroredImage":MirroredImage,
    "NoiseImage":NoiseImage,
    "GradientImage":GradientImage,
    "TransparentImage":TransparentImage,
    "ResizeImageMixlab":ResizeImage,
    "LoadImagesFromPath":LoadImagesFromPath,
    "LoadImagesFromURL":LoadImagesFromURL,
    "TextImage":TextImage,
    "EnhanceImage":EnhanceImage,
    "SvgImage":SvgImage,
    "3DImage":Image3D, 
    "ImageColorTransfer":ImageColorTransfer,
    "ShowLayer":ShowLayer,
    "NewLayer":NewLayer,
    "SplitImage":SplitImage,
    "CenterImage":CenterImage,
    "GridOutput":GridOutput,
    "MergeLayers":MergeLayers,
    "SplitLongMask":SplitLongMask,
    "FeatheredMask":FeatheredMask,
    "SmoothMask":SmoothMask,
    "FaceToMask":FaceToMask,
    "AreaToMask":AreaToMask,
    "ImageCropByAlpha":ImageCropByAlpha,
    "VAELoaderConsistencyDecoder":VAELoader,
    "SaveImageToLocal":SaveImageToLocal,
    "VAEDecodeConsistencyDecoder":VAEDecode,
    "ScreenShare":ScreenShareNode,
    "FloatingVideo":FloatingVideo,
    "CLIPSeg_":CLIPSeg,
    "CombineMasks_":CombineMasks,
    "ChatGPTOpenAI":ChatGPTNode,
    "ShowTextForGPT":ShowTextForGPT,
    "CharacterInText":CharacterInText,
    "SpeechRecognition":SpeechRecognition,
    "SpeechSynthesis":SpeechSynthesis,
    "Color":ColorInput,
    "FloatSlider":FloatSlider,
    "IntNumber":IntNumber,
    "TextInput_":TextInput,
    "Font":FontInput,
    "TextToNumber":TextToNumber,
    "DynamicDelayProcessor":DynamicDelayProcessor,
    "MultiplicationNode":MultiplicationNode,
    "GetImageSize_":GetImageSize_,
    "SwitchByIndex":SwitchByIndex,
    "LimitNumber":LimitNumber, 
    "OutlineMask":OutlineMask,
    "JoinWithDelimiter":JoinWithDelimiter,
    "Seed_":CreateSeedNode,
    "CkptNames_":CreateCkptNames,
    "SamplerNames_":CreateSampler_names,
    "LoraNames_":CreateLoraNames
    # "LaMaInpainting":LaMaInpainting
    # "GamePal":GamePal
}

# 一个包含节点友好/可读的标题的字典
NODE_DISPLAY_NAME_MAPPINGS = {
    "AppInfo":"AppInfo ♾️Mixlab",
    "ResizeImageMixlab":"ResizeImage ♾️Mixlab",
    "RandomPrompt": "Random Prompt ♾️Mixlab",
    "SplitLongMask":"Splitting a long image into sections",
    "VAELoaderConsistencyDecoder":"Consistency Decoder Loader",
    "VAEDecodeConsistencyDecoder":"Consistency Decoder Decode",
    "ScreenShare":"ScreenShare ♾️Mixlab",
    "FloatingVideo":"FloatingVideo ♾️Mixlab",
    "ChatGPTOpenAI":"ChatGPT ♾️Mixlab",
    "ShowTextForGPT":"ShowTextForGPT ♾️Mixlab",
    "MergeLayers":"MergeLayers ♾️Mixlab",
    "SpeechSynthesis":"SpeechSynthesis ♾️Mixlab",
    "SpeechRecognition":"SpeechRecognition ♾️Mixlab",
    "3DImage":"3DImage ♾️Mixlab",
    "DynamicDelayProcessor":"DynamicDelayByText ♾️Mixlab",
    "LaMaInpainting":"LaMaInpainting ♾️Mixlab",
    "PromptSlide":"PromptSlide ♾️Mixlab",
    "PromptGenerate_Mix":"PromptGenerate ♾️Mixlab",
    "ChinesePrompt_Mix":"ChinesePrompt ♾️Mixlab",
    "GamePal":"GamePal ♾️Mixlab",
    "RembgNode_Mix":"Removebg",
    "LoraNames_":"LoraName_TriggerWords.safetensors"
}

# web ui的节点功能
WEB_DIRECTORY = "./web"

print('--------------')
print('\033[91m ### Mixlab Nodes: \033[93mLoaded')

try:
    from .nodes.Lama import LaMaInpainting
    print('LaMaInpainting.available',LaMaInpainting.available)
    if LaMaInpainting.available:
        NODE_CLASS_MAPPINGS['LaMaInpainting']=LaMaInpainting
except Exception as e:
    print('LaMaInpainting.available',False,e)

try:
    from .nodes.ClipInterrogator import ClipInterrogator
    print('ClipInterrogator.available',ClipInterrogator.available)
    if ClipInterrogator.available:
        NODE_CLASS_MAPPINGS['ClipInterrogator']=ClipInterrogator
except Exception as e:
    print('ClipInterrogator.available',False,e)

try:
    from .nodes.TextGenerateNode import PromptGenerate,ChinesePrompt
    print('PromptGenerate.available',PromptGenerate.available)
    if PromptGenerate.available:
        NODE_CLASS_MAPPINGS['PromptGenerate_Mix']=PromptGenerate
    print('ChinesePrompt.available',ChinesePrompt.available)
    if ChinesePrompt.available:
        NODE_CLASS_MAPPINGS['ChinesePrompt_Mix']=ChinesePrompt
except Exception as e:
    print('TextGenerateNode.available',False,e)

try:
    from .nodes.RembgNode import RembgNode_
    print('RembgNode_.available',RembgNode_.available)
    if RembgNode_.available:
        NODE_CLASS_MAPPINGS['RembgNode_Mix']=RembgNode_
except Exception as e:
    print('RembgNode_.available',False,e)

print('\033[93m -------------- \033[0m')