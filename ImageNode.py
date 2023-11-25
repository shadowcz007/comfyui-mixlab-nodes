import numpy as np
import torch
from PIL import Image, ImageOps,ImageFilter
from PIL.PngImagePlugin import PngInfo
import base64,os
from io import BytesIO
import folder_paths
import json
from comfy.cli_args import args
import cv2 


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


def doMask(image,mask,save_image=False,filename_prefix="Mixlab",invert="yes",save_mask=False,prompt=None, extra_pnginfo=None):
   
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
    end="1" if invert=='yes' else ""
    image_file = f"{filename}_{counter:05}_{end}.png"
    mask_file = f"{filename}_{counter:05}_{end}_mask.png"

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
    
    im=im.convert('RGB')
    im_tensor=pil2tensor(im)

    return {
        "result":result,
        "image_path":image_path,
        "im_tensor":im_tensor
    }


# 提取不透明部分，裁切图片
def crop_image_remove_transparent(image):
    # 将PIL的Image类型转换为OpenCV的numpy数组
    image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGRA)

    # 分离图像的RGBA通道
    rgba = cv2.split(image_np)
    alpha = rgba[3]

    # 使用阈值将非透明部分转换为纯白色（255），透明部分转换为纯黑色（0）
    _, mask = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)

    # 查找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 获取最大轮廓的边界框
    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))

    # 使用边界框裁剪图像
    cropped_image = image_np[y:y+h, x:x+w]

    # 将裁剪后的图像转换为PIL的Image类型
    result_pil = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGRA2RGBA))

    return result_pil



def load_image(fp,white_bg=False):
    i = Image.open(fp)
    i = ImageOps.exif_transpose(i)
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


# 获取图片s
def get_images_filepath(f,white_bg=False):
    images = []
 
    if os.path.isdir(f):
        for root, dirs, files in os.walk(f):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    (im,mask)=load_image(file_path,white_bg)
                    images.append({
                        "image":im,
                        "mask":mask,
                        "file_path":file_path
                    })
                except:
                    print('非图片',file_path)
 
    elif os.path.isfile(f):
        try:
            (im,mask)=load_image(f,white_bg)
            images.append({
                        "image":im,
                        "mask":mask,
                        "file_path":f
                    })
        except:
            print('非图片',f)
    else:
        print('路径不存在或无效',f)

    return images




# 对轮廓进行平滑
def smooth_edges(alpha_channel, smoothness):

    # 将图像中的不透明物体提取出来
    # alpha_channel = image_rgba[:, :, 3]
    # 0：表示设定的阈值，即像素值小于或等于这个阈值的像素将被设置为0。
    # 255：表示设置的最大值，即像素值大于阈值的像素将被设置为255。
    _, mask = cv2.threshold(alpha_channel, 127, 255, cv2.THRESH_BINARY)

    # 对提取的不透明物体进行边缘检测
    # edges = cv2.Canny(mask, 100, 200)

    
    # 将一个整数变成最接近的奇数
    smoothness = smoothness if smoothness % 2 != 0 else smoothness + 1
    # 进行光滑处理
    smoothed_mask = cv2.GaussianBlur(mask, (smoothness, smoothness), 0)

    return smoothed_mask



class SmoothMask:
    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "mask": ("MASK",),
                                "smoothness":("INT", {"default": 1, 
                                                        "min":0, 
                                                        "max": 150, 
                                                        "step": 1,
                                                        "display": "slider"})
                            }
            }
    
    RETURN_TYPES = ('MASK',)

    FUNCTION = "run"

    CATEGORY = "Mixlab/mask"

    INPUT_IS_LIST = False

    OUTPUT_IS_LIST = (False,)
  
    # 运行的函数
    def run(self,mask,smoothness):
        # result = mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])).movedim(1, -1).expand(-1, -1, -1, 3)
        print('SmoothMask',mask.shape)
        mask=tensor2pil(mask)
    
        # 打开图像并将其转换为黑白图
        # image = mask.convert('L')

        # 应用羽化效果
        feathered_image = mask.filter(ImageFilter.GaussianBlur(smoothness))

        mask=pil2tensor(feathered_image)
           
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

    CATEGORY = "Mixlab/mask"

    OUTPUT_IS_LIST = (False,)
  
    # 运行的函数
    def run(self,mask,start_offset, feathering_weight):
        # print(mask.shape,mask.size())
        
        image=tensor2pil(mask)

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
        
        mask=pil2tensor(result_image)
        # print(mask.shape,mask.size())
        return mask




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



# 一个batch传进来 INPUT_IS_LIST = False
# mask始终会被拍平,([2, 568, 512]) -- > ([1136, 512])
# 原因是一个batch传来的
class TransparentImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "images": ("IMAGE",),
                                "masks": ("MASK",),
                                "invert": (["yes", "no"],),
                                "save": (["yes", "no"],),
                            },
                "optional":{
                    "filename_prefix":("STRING", {"multiline": False,"default": "Mixlab_save"})
                },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
            }
    
    RETURN_TYPES = ('STRING','IMAGE')

    OUTPUT_NODE = True

    FUNCTION = "run"

    CATEGORY = "Mixlab/image"

    # INPUT_IS_LIST = True， 一个batch传进来
    OUTPUT_IS_LIST = (True,True,)
    # OUTPUT_NODE = True

    # 运行的函数
    def run(self,images,masks,invert,save,filename_prefix,prompt=None, extra_pnginfo=None):
        print('TransparentImage',images.shape,images.size())
        # print(masks.shape,masks.size())

        ui_images=[]
        image_paths=[]
        
        count=images.shape[0]
        masks_new=[]
        nh=masks.shape[0]//count

        #INPUT_IS_LIST = False, 一个batch传进来
        if nh*count==masks.shape[0]:
            masks_new=split_mask_by_new_height(masks,nh)
        else:
            masks_new=split_mask_by_new_height(masks,masks.shape[0])


        is_save=True if save=='yes' else False
        # filename_prefix += self.prefix_append

        images_res=[]

        for i in range(len(images)):
            image=images[i]
            mask=masks_new[i]

            result=doMask(image,mask,is_save,filename_prefix,invert,not is_save,prompt, extra_pnginfo)

            for item in result["result"]:
                ui_images.append(item)

            image_paths.append(result['image_path'])

            images_res.append(result['im_tensor'])
        
        # ui.images 节点里显示图片，和 传参，image_path自定义的数据，需要写节点的自定义ui
        # result 里输出给下个节点的数据 
        print('TransparentImage',len(images_res))
        return {"ui":{"images": ui_images,"image_paths":image_paths},"result": (image_paths,images_res,)}
        


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
                    "white_bg": (["disable","enable"],),
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
    def run(self,file_path,white_bg,newest_files,index_variable,seed):
        print(file_path)
        images=get_images_filepath(file_path,white_bg=='enable')

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
                              },
                "optional":{
                    "auto_transparent": (["enable", "disable"],)
                }
                }
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "crop"

    CATEGORY = "Mixlab/image"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)


    def crop(self, images, width, height, x, y,auto_transparent):
        print('#ImageCrop:',width,auto_transparent,type(images[0]))
        width=width[0]
        height=height[0]
        x=x[0]
        y=y[0]
        auto_transparent=auto_transparent[0]

        cropped_images = []
        
        for img in images:

            im=tensor2pil(img)

            if auto_transparent=='enable':
                cropped_img=crop_image_remove_transparent(im)
            else:
                cropped_img = im.crop((x, y, x + width, y + height))
            
            cropped_images.append(pil2tensor(cropped_img))

        return (cropped_images,)

