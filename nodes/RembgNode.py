import os,sys
import folder_paths

from PIL import Image
import importlib.util

import comfy.utils
import numpy as np
import torch


U2NET_HOME=os.path.join(folder_paths.models_dir, "rembg")
os.environ["U2NET_HOME"] = U2NET_HOME

global _available
_available=False

def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None


try:
    if is_installed('rembg')==False:
        import subprocess

        # 安装
        print('#pip install rembg[gpu]')

        result = subprocess.run([sys.executable, '-s', '-m', 'pip', 'install', 'rembg[gpu]'], capture_output=True, text=True)

        #检查命令执行结果
        if result.returncode == 0:
            print("#install success")
            from rembg import new_session, remove
            _available=True
        else:
            print("#install error")
        
    else:
        from rembg import new_session, remove
        _available=True

except:
    _available=False


def run_bg(model_name= "unet",images=[]):
    # model_name = "unet" # "isnet-general-use"
    rembg_session = new_session(model_name)
    masks=[]
    rgba_images=[]
    rgb_images=[]
    # 进度条
    pbar = comfy.utils.ProgressBar(len(images) )
    for img in images:
        # use the post_process_mask argument to post process the mask to get better results.
        mask = remove(img, session=rembg_session,only_mask=True,post_process_mask=True)
        # mask=mask.convert('L')
        # masks.append(mask)
        if model_name=="u2net_cloth_seg":
            width, original_height = mask.size
            num_slices = original_height // img.height
            for i in range(num_slices):
                top = i * img.height
                bottom = (i + 1) * img.height
                slice_image = mask.crop((0, top, width, bottom))
                slice_mask=slice_image.convert('L')
                masks.append(slice_mask)

                # rgba图
                image_rgba = img.convert("RGBA")
                image_rgba.putalpha(slice_mask)
                rgba_images.append(image_rgba)

                #rgb
                rgb_image = Image.new("RGB", image_rgba.size, (0, 0, 0))
                rgb_image.paste(image_rgba, mask=image_rgba.split()[3])
                rgb_images.append(rgb_image)

        else:
            mask=mask.convert('L')    
            # mask.save(output_path)
            masks.append(mask)

            # rgba图
            image_rgba = img.convert("RGBA")
            image_rgba.putalpha(mask)
            rgba_images.append(image_rgba)

            #rgb
            rgb_image = Image.new("RGB", image_rgba.size, (0, 0, 0))
            rgb_image.paste(image_rgba, mask=image_rgba.split()[3])
            rgb_images.append(rgb_image)
            
        pbar.update(1)
    return (masks,rgba_images,rgb_images)


# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


class RembgNode_:

    global _available
    available=_available
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "model_name": (["u2net",
                            "u2netp",
                            "u2net_human_seg",
                            "u2net_cloth_seg",
                            "silueta",
                            "isnet-general-use",
                            "isnet-anime",
                            # "sam"
                            ],),
            
                             },
                }
    
    RETURN_TYPES = ("MASK","IMAGE","RGBA",)
    RETURN_NAMES = ("masks","images","RGBAs")

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Mask"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,True,)
  
    def run(self,image,model_name):
        # 兼容list输入和batch输入

        model_name=model_name[0]

        images=[]
        
        for ims in image:
            for im in ims:
                im=tensor2pil(im)
                images.append(im)

        masks,rgba_images,rgb_images=run_bg(model_name,images)

        masks=[pil2tensor(m) for m in masks]

        rgba_images=[pil2tensor(m) for m in rgba_images]

        rgb_images=[pil2tensor(m) for m in rgb_images]

        return (masks,rgb_images,rgba_images,)