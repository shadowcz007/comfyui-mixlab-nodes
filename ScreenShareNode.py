import os,io
from PIL import Image, ImageOps
import numpy as np
import torch
import folder_paths


def load_image(fp,white_bg=False):
    i = Image.open(fp)
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
            "image_path": ("CHEESE",)
        },
          "optional":{
                    "seed": ("INT", {"default": 1, "min": 0, "max": 0xffffffffffffffff}),
                } }
    
    RETURN_TYPES = ('IMAGE','MASK')

    FUNCTION = "run"

    CATEGORY = "Mixlab/image"

    # INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (False,False,)
  
    # 运行的函数
    def run(self,image_path,seed):
        np=os.path.join(folder_paths.get_temp_directory(),image_path)
        print(seed,np)

        (im,mask)=load_image(np)
  
        return (im,mask)

