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


# # 把白色部分处理成黑色
# def convert_to_bw(image):
#     # 读取图片
#     # image = Image.open(image_path)
    
#     # 获取图片的宽度和高度
#     width, height = image.size
    
#     # 遍历图片的每个像素点
#     for x in range(width):
#         for y in range(height):
#             # 获取当前像素点的RGB值
#             r, g, b = image.getpixel((x, y))
            
#             # 判断当前像素点是否为白色
#             if r == 255 and g == 255 and b == 255:
#                 # 将白色部分处理成黑色
#                 image.putpixel((x, y), (0, 0, 0))
#             else:
#                 # 将非白色部分处理成白色
#                 image.putpixel((x, y), (255, 255, 255))
    
#     # 转换为黑白图
#     mask = image.convert("L")
    
#     # # 保存处理后的图片
#     # image.save("black_white_image.jpg")
    
#     # print("图片处理完成！")
#     return mask


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
            "refresh_rate": ("INT", {"default": 500, "min": 0,"step": 50, "max": 0xffffffffffffffff}),
        },
          "optional":{
              "prompt": ("PROMPT",),
              "slide": ("SLIDE",),
              "seed": ("SEED",),
              
            #   "seed": ("INT", {"default": 1, "min": 0, "max": 0xffffffffffffffff}),
                } }
    
    RETURN_TYPES = ('IMAGE','STRING','FLOAT',"INT")
    RETURN_NAMES = ("IMAGE","PROMPT","FLOAT","INT")
    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Screen"

    # INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (False,False,False,False)
  
    # 运行的函数
    def run(self,image_base64,refresh_rate ,prompt,slide,seed):
        im,mask=base64_save(image_base64)
        # print('##########prompt',prompt)
        return {"ui":{"refresh_rate": [refresh_rate]},"result": (im,prompt,slide,seed,)}


class FloatingVideo:
    @classmethod
    def INPUT_TYPES(s):
        return { "required":{
            "images": ("IMAGE",)
        }, }
    
    # RETURN_TYPES = ('IMAGE','MASK')
    RETURN_TYPES = ()
 
    OUTPUT_NODE = True
    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Screen"

    # INPUT_IS_LIST = True
    # OUTPUT_IS_LIST = (False,False,)
  
    # 运行的函数
    def run(self,images):
       
        results = list()
    
        for image in images:
            image=tensor2pil(image)
            # image_base64 = base64.b64encode(image.tobytes())

            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            results.append(image_base64)
  

        return { "ui": { "images_": results } }



# class SildeNode:
#     CATEGORY = "quicknodes"
#     @classmethod    
#     def INPUT_TYPES(s):
#         return { "required":{} }
#     RETURN_TYPES = ()
#     RETURN_NAMES = ()
#     FUNCTION = "func"
#     def func(self):
#         return ()