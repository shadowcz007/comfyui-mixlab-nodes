import numpy as np
import torch
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
import base64,os
from io import BytesIO
import folder_paths
import json
from comfy.cli_args import args


MAX_RESOLUTION=8192

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def naive_cutout(img, mask,invert=True):
    """
    Perform a simple cutout operation on an image using a mask.

    This function takes a PIL image `img` and a PIL image `mask` as input.
    It uses the mask to create a new image where the pixels from `img` are
    cut out based on the mask.

    The function returns a PIL image representing the cutout of the original
    image using the mask.
    """

    img=img.convert("RGBA")
    mask=mask.convert("RGBA")

    empty = Image.new("RGBA", (img.size), 0)

    red, green, blue, alpha = mask.split()

    mask = mask.convert('L')
    # 黑白，要可调
    if invert==True:
        mask = mask.point(lambda x: 255 if x > 128 else 0)
    else:
        mask = mask.point(lambda x: 255 if x < 128 else 0)

    new_image = Image.merge('RGBA', (red, green, blue, mask))

    cutout = Image.composite(img.convert("RGBA"), empty,new_image)

    return cutout


# (h,w)
# (1072, 512) -- > [(536, 512),(536, 512)]
def split_mask_by_new_height(masks,new_height):
    split_masks = torch.split(masks, new_height, dim=0)
    return split_masks


def doMask(image,mask,save_image=False,filename_prefix="Mixlab",invert="invert",save_mask=False,prompt=None, extra_pnginfo=None):
   
    output_dir = (
            folder_paths.get_output_directory()
            if save_image
            else folder_paths.get_temp_directory()
        )

    (
        full_output_folder,
        filename,
        counter,
        subfolder,
         _,
    ) = folder_paths.get_save_image_path(filename_prefix, output_dir)

    

    image=tensor2pil(image)

    mask = mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])).movedim(1, -1).expand(-1, -1, -1, 3)
        
    mask=tensor2pil(mask)

    im=naive_cutout(image, mask,invert=='yes')

    # format="image/png",
    end="1" if invert=='invert' else ""
    image_file = f"{filename}_{counter:05}_{end}.png"
    mask_file = f"{filename}_{counter:05}_{end}_mask.png"

    # im_tensor=pil2tensor(im)
    image_path=os.path.join(full_output_folder, image_file)


    metadata = None
    if not args.disable_metadata:
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))

    im.save(image_path,pnginfo=metadata, compress_level=4)
    
    result= [{
                "filename": image_file,
                "subfolder": subfolder,
                "type": "output" if save_image else "temp"
            }]
    
    if save_mask:
        mask_path=os.path.join(full_output_folder, mask_file)
        mask.save(mask_path,
                    compress_level=4)
        
        result.append({
                "filename": mask_file,
                "subfolder": subfolder,
                "type": "output" if save_image else "temp"
            })
    

    return {
        "result":result,
        "image_path":image_path
    }



def load_image(fp):
    i = Image.open(fp)
    i = ImageOps.exif_transpose(i)
    image = i.convert("RGB")
    image = np.array(image).astype(np.float32) / 255.0
    image = torch.from_numpy(image)[None,]
    if 'A' in i.getbands():
        mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
        mask = 1. - torch.from_numpy(mask)
    else:
        mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
    return (image,mask)


# 获取图片s
def get_images_filepath(f):
    images = []
 
    if os.path.isdir(f):
        for root, dirs, files in os.walk(f):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    (im,mask)=load_image(file_path)
                    images.append({
                        "image":im,
                        "mask":mask,
                        "file_path":file_path
                    })
                except:
                    print('非图片',file_path)
 
    elif os.path.isfile(f):
        try:
            (im,mask)=load_image(f)
            images.append({
                        "image":im,
                        "mask":mask,
                        "file_path":f
                    })
        except:
            print('非图片',file_path)
    else:
        print('路径不存在或无效',f)

    return images




class SplitLongMask:

    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "long_mask": ("MASK",),
                                "count":("INT", {"default": 1, "min": 1, "max": 1024, "step": 1})
                            }
            }
    
    RETURN_TYPES = ('MASK',)

    FUNCTION = "run"

    CATEGORY = "Mixlab/mask"

    OUTPUT_IS_LIST = (True,)
  
    # 运行的函数
    def run(self,long_mask,count):
        masks=[]
        nh=long_mask.shape[0]//count

        if nh*count==long_mask.shape[0]:
            masks=split_mask_by_new_height(long_mask,nh)
        else:
            masks=split_mask_by_new_height(long_mask,long_mask.shape[0])

        return (masks,)




# mask始终会被拍平,([2, 568, 512]) -- > ([1136, 512])
class TransparentImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "images": ("IMAGE",),
                                "masks": ("MASK",),
                                "invert": (["invert", ""],),
                                "save": (["yes", "no"],),
                            },
                "optional":{
                    "filename_prefix":("STRING", {"multiline": False,"default": "Mixlab_save"})
                },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
            }
    
    RETURN_TYPES = ('STRING',)

    OUTPUT_NODE = True

    FUNCTION = "run"

    CATEGORY = "Mixlab/image"

    # INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    # OUTPUT_NODE = True

    # 运行的函数
    def run(self,images,masks,invert,save,filename_prefix,prompt=None, extra_pnginfo=None):
        ui_images=[]
        image_paths=[]
        
        count=images.shape[0]
        masks_new=[]
        nh=masks.shape[0]//count

        if nh*count==masks.shape[0]:
            masks_new=split_mask_by_new_height(masks,nh)
        else:
            masks_new=split_mask_by_new_height(masks,masks.shape[0])


        is_save=True if save=='yes' else False
        # filename_prefix += self.prefix_append
        for i in range(len(images)):
            image=images[i]
            mask=masks_new[i]

            result=doMask(image,mask,is_save,filename_prefix,invert,not is_save,prompt, extra_pnginfo)

            for item in result["result"]:
                ui_images.append(item)

            image_paths.append(result['image_path'])
        
        # ui.images 节点里显示图片，和 传参，image_path自定义的数据，需要写节点的自定义ui
        # result 里输出给下个节点的数据 

        return {"ui":{"images": ui_images,"image_paths":image_paths},"result": (image_paths,)}
        


''' 
("STRING",{"multiline": False,"default": "Hello World!"})
对应 widgets.js 里：
const defaultVal = inputData[1].default || ""; 
const multiline = !!inputData[1].multiline;
    '''

# 支持按照时间排序
# 支持输出1张
#
class LoadImagesFromPath:

    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "file_path": ("STRING",{"multiline": False,"default": ""})
                            },
                "optional":{
                    "newest_files": (["enable", "disable"],),
                    "index_variable":("INT", {
                        "default": -1, 
                        "min": -1, #Minimum value
                        "max": 2048, #Maximum value
                        "step": 1, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    }),
                    "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                }
            }
    
    RETURN_TYPES = ('IMAGE','MASK')

    FUNCTION = "run"

    CATEGORY = "Mixlab/image"

    # INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,)
  
    # 运行的函数
    def run(self,file_path,newest_files,index_variable,seed):

        images=get_images_filepath(file_path)

        # 排序
        sorted_files = sorted(images, key=lambda x: os.path.getmtime(x['file_path']), reverse=(newest_files=='enable'))

        imgs=[]
        masks=[]

        for im in sorted_files:
            imgs.append(im['image'])
            masks.append(im['mask'])
        
        # print('index_variable',index_variable)
        if index_variable!=-1:
            imgs=[imgs[index_variable]] if index_variable < len(imgs) else None
            masks=[masks[index_variable]] if index_variable < len(masks) else None

        return (imgs,masks)



class ImagesCrop:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "images": ("IMAGE",),
                              "width": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
                              "height": ("INT", {"default": 512, "min": 64, "max": MAX_RESOLUTION, "step": 8}),
                              "x": ("INT", {"default": 0, "min": 0, "max": MAX_RESOLUTION, "step": 8}),
                              "y": ("INT", {"default": 0, "min": 0, "max": MAX_RESOLUTION, "step": 8}),
                              }}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "crop"

    CATEGORY = "Mixlab/image"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)


    def crop(self, images, width, height, x, y):
        width=width[0]
        height=height[0]
        x=x[0]
        y=y[0]
        cropped_images = []
        for img in images:
            im=tensor2pil(img)
            cropped_img = im.crop((x, y, x + width, y + height))
            cropped_images.append(pil2tensor(cropped_img))
        return (cropped_images,)

