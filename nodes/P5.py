import torch
import numpy as np
from PIL import Image
import base64
import io
import comfy.utils

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)




def base64_to_image(base64_string):
    # 去除前缀
    prefix, base64_data = base64_string.split(",", 1)
    
    # 从base64字符串中解码图像数据
    image_data = base64.b64decode(base64_data)
    
    # 创建一个内存流对象
    image_stream = io.BytesIO(image_data)
    
    # 使用PIL的Image模块打开图像数据
    image = Image.open(image_stream)
    
    return image

class P5Input:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "frames":("IMAGEBASE64",), 
                             },
                }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("frames",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Video"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (False,)

    def run(self, frames):
        # print(images)
        ims=[]
        for im in frames['base64']:
            image = base64_to_image(im)
            image=image.convert('RGB')
            image=pil2tensor(image)
            ims.append(image)

        if len(ims)==0:
            image1 = Image.new('RGB', (512, 512), color='black')
            return (pil2tensor(image1),)
        image1 = ims[0]
        for image2 in ims[1:]:
            if image1.shape[1:] != image2.shape[1:]:
                image2 = comfy.utils.common_upscale(image2.movedim(-1, 1), image1.shape[2], image1.shape[1], "bilinear", "center").movedim(1, -1)
            image1 = torch.cat((image1, image2), dim=0)
        return (image1,)
