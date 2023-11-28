import os,io
from PIL import Image, ImageOps
import numpy as np
import torch
import folder_paths
import base64
from io import BytesIO


# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


def base64_save(base64_data):
    # base64_data = "data:image/png;base64,iVBORw0KG..."
    data = base64_data.split(",")[1]
    decoded_data = base64.b64decode(data)

    # 保存图像为本地文件
    image = Image.open(BytesIO(decoded_data))
    # image.save(fp)
    image,mask=load_image(image)
    return (image,mask)


def load_image(i,white_bg=False):
    # i = Image.open(fp)
    image = i.convert("RGB")
    image = np.array(image).astype(np.float32) / 255.0
    image = torch.from_numpy(image)[None,]
    if 'A' in i.getbands():
        mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
        mask = 1. - torch.from_numpy(mask)
        if white_bg==True:
            nw = mask.unsqueeze(0).unsqueeze(-1).repeat(1, 1, 1, 3)
            # 将mask的黑色部分对image进行白色处理
            image[nw == 1] = 1.0
    else:
        mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
    return (image,mask)


class ScreenShareNode:
    @classmethod
    def INPUT_TYPES(s):
        return { "required":{
            "image_base64": ("CHEESE",),
        },
          "optional":{
              "prompt": ("PROMPT",),
                    "seed": ("INT", {"default": 1, "min": 0, "max": 0xffffffffffffffff}),
                } }
    
    RETURN_TYPES = ('IMAGE','MASK','STRING')

    FUNCTION = "run"

    CATEGORY = "Mixlab/image"

    # INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (False,False,False)
  
    # 运行的函数
    def run(self,image_base64,prompt,seed):
        im,mask=base64_save(image_base64)
        print('##########prompt',prompt)
        return (im,mask,prompt)
    

class FloatingVideo:
    @classmethod
    def INPUT_TYPES(s):
        return { "required":{
            "images": ("IMAGE",)
        }, "optional":{
                    "seed": ("INT", {"default": 1, "min": 0, "max": 0xffffffffffffffff}),
                } }
    
    # RETURN_TYPES = ('IMAGE','MASK')
    RETURN_TYPES = ()
 
    OUTPUT_NODE = True
    FUNCTION = "run"

    CATEGORY = "Mixlab/image"

    # INPUT_IS_LIST = True
    # OUTPUT_IS_LIST = (False,False,)
  
    # 运行的函数
    def run(self,images,seed):
       
        results = list()
    
        for image in images:
            image=tensor2pil(image)
            # image_base64 = base64.b64encode(image.tobytes())

            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            results.append(image_base64)
  

        return { "ui": { "images": results } }

