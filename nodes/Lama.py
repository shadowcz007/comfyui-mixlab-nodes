import os,sys
import folder_paths

from PIL import Image
import importlib.util
import numpy as np

import torch

global _available
_available=False

def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None

if is_installed('simple_lama_inpainting')==False:
    import subprocess
    from packaging import version
    
    if version.parse(torch.__version__)>=version.parse('2.1'):
        # 安装
        print('#pip install simple_lama_inpainting')

        result = subprocess.run([sys.executable, '-s', '-m', 'pip', 'install', 'simple_lama_inpainting'], capture_output=True, text=True)

        #检查命令执行结果
        if result.returncode == 0:
            print("#install success")
            from simple_lama_inpainting import SimpleLama
            _available=True
        else:
            print("#install error")
    else:
        print('#pls check your torch version >= 2.1')

else:
    from simple_lama_inpainting import SimpleLama
    _available=True


def get_lama_path():
    try:
        return folder_paths.get_folder_paths('lama')[0]
    except:
        return os.path.join(folder_paths.models_dir, "lama")

llma_model_path=os.path.join(get_lama_path(), "big-lama.pt")
if not os.path.exists(llma_model_path):
    os.environ['LAMA_MODEL']=''
    print(f"## lama torchscript model not found: {llma_model_path},pls download from https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt")
else:
    os.environ['LAMA_MODEL'] = llma_model_path

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
    global _available
    available=_available
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "mask": ("MASK",),
                             },
                }
    
    RETURN_TYPES = ("IMAGE",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

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