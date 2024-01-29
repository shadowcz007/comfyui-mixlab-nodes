import os,sys
# import re,random,json
from PIL import Image
import numpy as np
# FONT_PATH= os.path.abspath(os.path.join(os.path.dirname(__file__),'../assets/王汉宗颜楷体繁.ttf'))
import folder_paths
#
import os
import json
import datetime

import folder_paths
from server import PromptServer
import importlib.util


def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None


class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")

app_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'../app'))

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

                option=os.path.basename(os.path.dirname(file_path))+'/'+os.path.basename(file_path)
                if os.path.dirname(file_path) == folder_path:
                    option=os.path.basename(file_path)

                file_info = {
                    'filename': os.path.basename(file_path),
                    'category': os.path.dirname(file_path),
                    'data': json_data,
                    'date': numeric_timestamp,
                    "option":option
                }
                data.append(file_info)
        except Exception as e:
            print(e)
    
    sorted_data = sorted(data, key=lambda x: x['date'], reverse=True)
    return sorted_data

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



try:
    if is_installed('websocket')==False:
        import subprocess

        # 安装
        print('#pip install websocket-client')

        result = subprocess.run([sys.executable, '-s', '-m', 'pip', 'install', 'websocket-client'], capture_output=True, text=True)

        #检查命令执行结果
        if result.returncode == 0:
            print("#install success")
            import websocket 
        else:
            print("#install error")
        
    else:
        import websocket 
        # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)

except:
    print("#websocket-client error")
#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import uuid
import json
import urllib.request
import urllib.parse

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break #Execution is done
        else:
            continue #previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images

prompt_text = """
{
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 8,
            "denoise": 1,
            "latent_image": [
                "5",
                0
            ],
            "model": [
                "4",
                0
            ],
            "negative": [
                "7",
                0
            ],
            "positive": [
                "6",
                0
            ],
            "sampler_name": "euler",
            "scheduler": "normal",
            "seed": 8566257,
            "steps": 20
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.ckpt"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 512,
            "width": 512
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "masterpiece best quality girl"
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "bad hands"
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": [
                "3",
                0
            ],
            "vae": [
                "4",
                2
            ]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "ComfyUI",
            "images": [
                "8",
                0
            ]
        }
    }
}
"""

# prompt = json.loads(prompt_text)
# #set the text prompt for our positive CLIPTextEncode
# prompt["6"]["inputs"]["text"] = "masterpiece best quality man"

# #set the seed for our KSampler node
# prompt["3"]["inputs"]["seed"] = 5

# ws = websocket.WebSocket()
# ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
# images = get_images(ws, prompt)

# #Commented out code to display the output images:

# # for node_id in images:
# #     for image_data in images[node_id]:
# #         from PIL import Image
# #         import io
# #         image = Image.open(io.BytesIO(image_data))
# #         image.show()



















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
    


#  app可以当成节点运行
class AppNode:
   
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "name": ([x['option'] for x in read_workflow_json_files_all(app_path)],),
                    "image":("IMAGE",),
                             }
                }
    
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab"

    OUTPUT_NODE = True
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)
    

    def run(self,name,input):
        print('#app_path',input)
        print(PromptServer.instance.port)

        return (name,)
    

