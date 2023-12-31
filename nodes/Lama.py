import os
import folder_paths
from simple_lama_inpainting import SimpleLama
from PIL import Image

import numpy as np

import torch


os.environ['LAMA_MODEL'] =  os.path.join(folder_paths.models_dir, "lama/big-lama.pt")
if os.environ.get("LAMA_MODEL"):
    model_path=os.environ.get("LAMA_MODEL")
    if not os.path.exists(model_path):
        os.environ['LAMA_MODEL']=''
        raise FileNotFoundError(
            f"lama torchscript model not found: {model_path}"
                )

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


# simple_lama = SimpleLama()

# img_path = "image.png"
# mask_path = "mask.png"

# image = Image.open(img_path)
# mask = Image.open(mask_path).convert('L')

# result = simple_lama(image, mask)
# result.save("inpainted.png")


class LaMaInpainting:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "mask": ("MASK",),
                             },

            
                }
    
    RETURN_TYPES = ("IMAGE",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/image"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    global simple_lama
    simple_lama = None
    def run(self,image,mask):
        global simple_lama

        result=[]
        if simple_lama==None:
            simple_lama = SimpleLama()
        else:
            simple_lama.model.to("cuda" if torch.cuda.is_available() else "cpu")

        for i in range(len(image)):
            im=image[i]
            ma=mask[i]
            im=tensor2pil(im)
            ma=tensor2pil(ma)
            ma =ma.convert('L')
            
            res = simple_lama(im, ma)
            res=pil2tensor(res)
            result.append(res)
        # result.save("inpainted.png")
        if simple_lama.device=='cuda':
            simple_lama.model.to('cpu')

        return (result,)