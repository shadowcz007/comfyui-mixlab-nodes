import torch
from PIL import Image, ImageOps, ImageSequence, ImageFile
from PIL.PngImagePlugin import PngInfo

import numpy as np
import os
import folder_paths 
import node_helpers
import hashlib

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# tensor 取hash值
def tensor_to_hash(tensor):
    # 将 Tensor 转换为 NumPy 数组
    np_array = tensor.cpu().numpy()
    
    # 将 NumPy 数组转换为字节数据
    byte_data = np_array.tobytes()
    
    # 计算哈希值
    hash_value = hashlib.md5(byte_data).hexdigest()
    
    return hash_value


def create_temp_file(image):
    output_dir = folder_paths.get_temp_directory()

    (
            full_output_folder,
            filename,
            counter,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path('material', output_dir)

    
    image=tensor2pil(image)
 
    image_file = f"{filename}_{counter:05}.png"
     
    image_path=os.path.join(full_output_folder, image_file)

    image.save(image_path,compress_level=4)

    return (image_path,[{
    "filename": image_file,
    "subfolder": subfolder,
    "type": "temp"
    }])


# image - tensor - 文件路径
# loadImage的方法（ 文件路径 - image-mask ）
class EditMask:

    def __init__(self):
        self.image_id = None

    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    {"image": ("IMAGE",), # 表示一个张量
                     
                     },

                    "optional":{
                            "image_update": ("IMAGE_FILE",)
                        },
                   
                }

    CATEGORY = "♾️Mixlab/Mask"

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")

    FUNCTION = "edit"

    OUTPUT_NODE = True

    def edit(self, image,image_update=None):

        # 根据image输入来判断是否是新的图片
        if self.image_id==None:
            self.image_id=tensor_to_hash(image)
            image_update=None
        else:
            image_id=tensor_to_hash(image)
            if image_id!=self.image_id:
                image_update=None
                self.image_id=image_id


        image_path=None
        # print('#image_update',self.image_id,image_update)
        if image_update==None:
            print('--')
        else:
            if 'images' in image_update:
                images=image_update['images']
                filename=images[0]['filename']
                subfolder=images[0]['subfolder']
                type=images[0]['type']
                name, base_dir=folder_paths.annotated_filepath(filename)
                if type.endswith("output"):
                    base_dir = folder_paths.get_output_directory() 
                elif type.endswith("input"):
                    base_dir = folder_paths.get_input_directory() 
                elif type.endswith("temp"):
                    base_dir = folder_paths.get_temp_directory() 
                #base_dir = folder_paths.get_input_directory()  
                # print(base_dir,subfolder, name)
                image_path = os.path.join(base_dir,subfolder, name)
        
        if image_path==None:
            image_path,images=create_temp_file(image)

        print('#image_path',os.path.exists(image_path),image_path)
        # image_path = folder_paths.get_annotated_filepath(image) #文件名
        
        if not os.path.exists(image_path):
            image_path,images=create_temp_file(image)


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
                # 尺寸不对，需要按照image来
                mask = torch.zeros((h, w), dtype=torch.float32, device="cpu")

            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        return {"ui":{"images": images},"result": (output_image, output_mask)}

        # return (output_image, output_mask)
