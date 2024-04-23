 
import scipy.ndimage
import torch

import numpy as np 
# from PIL import Image, ImageDraw
from PIL import Image, ImageOps 

from comfy.cli_args import args
import cv2,os
from nodes import MAX_RESOLUTION, SaveImage, common_ksampler
import folder_paths,random

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def add_masks(mask1, mask2):
    mask1 = mask1.cpu()
    mask2 = mask2.cpu()
    cv2_mask1 = np.array(mask1) * 255
    cv2_mask2 = np.array(mask2) * 255

    if cv2_mask1.shape == cv2_mask2.shape:
        cv2_mask = cv2.add(cv2_mask1, cv2_mask2)
        return torch.clamp(torch.from_numpy(cv2_mask) / 255.0, min=0, max=1)
    else:
        return mask1
    

def grow(mask, expand, tapered_corners):
    c = 0 if tapered_corners else 1
    kernel = np.array([[c, 1, c],
                            [1, 1, 1],
                            [c, 1, c]])
    mask = mask.reshape((-1, mask.shape[-2], mask.shape[-1]))
    out = []
    for m in mask:
        output = m.numpy()
        for _ in range(abs(expand)):
            if expand < 0:
                output = scipy.ndimage.grey_erosion(output, footprint=kernel)
            else:
                output = scipy.ndimage.grey_dilation(output, footprint=kernel)
        output = torch.from_numpy(output)
        out.append(output)
    return torch.stack(out, dim=0)

def combine(destination, source, x, y):
    output = destination.reshape((-1, destination.shape[-2], destination.shape[-1])).clone()
    source = source.reshape((-1, source.shape[-2], source.shape[-1]))

    left, top = (x, y,)
    right, bottom = (min(left + source.shape[-1], destination.shape[-1]), min(top + source.shape[-2], destination.shape[-2]))
    visible_width, visible_height = (right - left, bottom - top,)

    source_portion = source[:, :visible_height, :visible_width]
    destination_portion = destination[:, top:bottom, left:right]
 
    #operation == "subtract":
    output[:, top:bottom, left:right] = destination_portion - source_portion
        
    output = torch.clamp(output, 0.0, 1.0)

    return output


class PreviewMask_(SaveImage):
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append =''.join(random.choice("abcdehijklmnopqrstupvxyzfg") for x in range(5))
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "mask": ("MASK",), 
                            }
            }
    
    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Mask"

    # 运行的函数
    def run(self, mask ):
        img=tensor2pil(mask)
        img=img.convert('RGB')
        img=pil2tensor(img) 
        return self.save_images(img, 'temp_', None,  None)


class OutlineMask:

    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "mask": ("MASK",),
                                "outline_width":("INT", {"default": 10,"min": 1, "max": MAX_RESOLUTION, "step": 1}),
                                "tapered_corners": ("BOOLEAN", {"default": True}),
                            }
            }
    
    RETURN_TYPES = ('MASK',)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Mask"

    # 运行的函数
    def run(self, mask, outline_width, tapered_corners):

        m1=grow(mask,outline_width,tapered_corners)
        m2=grow(mask,-outline_width,tapered_corners)

        m3=combine(m1,m2,0,0)

        return (m3,)
    

class MaskListReplace:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "masks": ("MASK",),
            "mask_replace": ("MASK",),
            "start_index":("INT", {"default": 0, "min": 0, "step": 1}),
            "end_index":("INT", {"default": 0, "min": 0, "step": 1}),
            "invert": ("BOOLEAN", {"default": False}),
        }
        }

    RETURN_TYPES = ("MASK",)
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Video"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    def run(self, masks,mask_replace,start_index,end_index,invert):
        mask_replace=mask_replace[0]
        start_index=start_index[0]
        end_index=end_index[0]
        invert=invert[0]
        
        new_masks=[]
        for i in range(len(masks)):
            if i>=start_index and i<=end_index:
                if invert:
                    new_masks.append(masks[i])
                else:
                    new_masks.append(mask_replace)
            else:
                if invert:
                    new_masks.append(mask_replace)
                else:
                    new_masks.append(masks[i])

        return (new_masks,)


class MaskListMerge:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "masks": ("MASK",),
        }
        }

    RETURN_TYPES = ("MASK",)
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Mask"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (False,)

    def run(self, masks):
        mask=masks[0]
        if isinstance(masks, list):
            for m in masks:
                # print(m.shape)
                mask = add_masks(mask, m)
        return (mask,)


class FeatheredMask:
    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "mask": ("MASK",),
                                "start_offset":("INT", {"default": 1, 
                                                        "min": -150, 
                                                        "max": 150, 
                                                        "step": 1,
                                                        "display": "slider"}),
                                "feathering_weight":("FLOAT", {"default": 0.1,
                                                                "min": 0.0,
                                                                "max": 1,
                                                                "step": 0.1,
                                                                "display": "slider"})
                            }
            }
    
    RETURN_TYPES = ('MASK',)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Mask"

    OUTPUT_IS_LIST = (True,)
  
    # 运行的函数
    def run(self,mask,start_offset, feathering_weight):
        # print(mask.shape,mask.size())
        
        num,_,_=mask.size()

        masks=[]

        for i in range(num):
            mm=mask[i]
            image=tensor2pil(mm)

            # Open the image using PIL
            image = image.convert("L")
            if start_offset>0:
                image=ImageOps.invert(image)

            # Convert the image to a numpy array
            image_np = np.array(image)

            # Use Canny edge detection to get black contours
            edges = cv2.Canny(image_np, 30, 150)

            for i in range(0,abs(start_offset)):
                # int(100*feathering_weight)
                a=int(abs(start_offset)*0.1*i)
                # Dilate the black contours to make them wider
                kernel = np.ones((a, a), np.uint8)

                dilated_edges = cv2.dilate(edges, kernel, iterations=1)
                # dilated_edges = cv2.erode(edges, kernel, iterations=1)
                # Smooth the dilated edges using Gaussian blur
                smoothed_edges = cv2.GaussianBlur(dilated_edges, (5, 5), 0)

                # Adjust the feathering weight
                feathering_weight = max(0, min(feathering_weight, 1))

                # Blend the smoothed edges with the original image to achieve feathering effect
                image_np = cv2.addWeighted(image_np, 1, smoothed_edges, feathering_weight, feathering_weight)

            # Convert the result back to PIL image
            result_image = Image.fromarray(np.uint8(image_np))
            result_image=result_image.convert("L")

            if start_offset>0:
                result_image=ImageOps.invert(result_image)
            
            result_image=result_image.convert("L")
            mt=pil2tensor(result_image)
            masks.append(mt)
         
            # print( mt.size())
        return (masks,)
