import torch
import numpy as np
from PIL import Image,ImageSequence,ImageOps
import base64
import io
import comfy.utils
import folder_paths
import node_helpers


# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def load_image_to_tensor( image):
    image_path = folder_paths.get_annotated_filepath(image)
        
    img = node_helpers.pillow(Image.open, image_path)
        
    output_images = []
    output_masks = []
    w, h = None, None

    excluded_formats = ['MPO']
        
    for i in ImageSequence.Iterator(img):
        i = node_helpers.pillow(ImageOps.exif_transpose, i)

        if i.mode == 'I':
            i = i.point(lambda i: i * (1 / 255))
        image = i.convert("RGB")

        if len(output_images) == 0:
            w = image.size[0]
            h = image.size[1]
            
        if image.size[0] != w or image.size[1] != h:
            continue
            
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        if 'A' in i.getbands():
            mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
        output_images.append(image)
        output_masks.append(mask.unsqueeze(0))

    if len(output_images) > 1 and img.format not in excluded_formats:
        output_image = torch.cat(output_images, dim=0)
        output_mask = torch.cat(output_masks, dim=0)
    else:
        output_image = output_images[0]
        output_mask = output_masks[0]

    return (output_image, output_mask)

          

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

    CATEGORY = "♾️Mixlab/Input"

    OUTPUT_NODE = True
    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self, frames):
        ims=[]
        for im in frames['images']:
            # print(im)
            if 'type' in im and (not f"[{im['type']}]" in im['name']):
                im['name']=im['name']+" "+f"[{im['type']}]"
                
            output_image, output_mask = load_image_to_tensor(im['name'])
            ims.append(output_image)

        if len(ims)==0:
            image1 = Image.new('RGB', (512, 512), color='black')
            return (pil2tensor(image1),)
        image1 = ims[0]
        for image2 in ims[1:]:
            if image1.shape[1:] != image2.shape[1:]:
                image2 = comfy.utils.common_upscale(image2.movedim(-1, 1), image1.shape[2], image1.shape[1], "bilinear", "center").movedim(1, -1)
            image1 = torch.cat((image1, image2), dim=0)

        # 用于节点提示:p5节点提示有多少帧
        return {"ui": {"_info": [len(frames['images'])]}, "result": (image1,)}
