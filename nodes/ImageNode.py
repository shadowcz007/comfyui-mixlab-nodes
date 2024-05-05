import numpy as np
import requests
import torch
# from PIL import Image, ImageDraw
from PIL import Image, ImageOps,ImageFilter,ImageEnhance,ImageDraw,ImageSequence, ImageFont
from PIL.PngImagePlugin import PngInfo
import base64,os,random
from io import BytesIO
import folder_paths
import json,io
import comfy.utils
from comfy.cli_args import args
import cv2
import string
import math,glob
from .Watcher import FolderWatcher
import hashlib



# 将PIL图片转换为OpenCV格式
def pil_to_opencv(image):
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return open_cv_image

# 将OpenCV格式图片转换为PIL格式
def opencv_to_pil(image):
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    return pil_image


def composite_images(foreground, background, mask,is_multiply_blend=False,position="overall"):
    width,height=foreground.size
 
    bg_image=background

    bwidth,bheight=bg_image.size

    # 按z-index排序
    if position=="overall":
        layer = {
                "x":0,
                "y":0,
                "width":bwidth,
                "height":bheight,
                "z_index":88,
                "scale_option":'overall',
                "image":foreground,
                "mask":mask
        }

    elif position=='center_bottom':
        
        scale = int(bwidth*0.5) / width
        new_height = int(height * scale)

        layer = {
                "x":int(bwidth*0.25),
                "y":bheight-new_height-24,
                "width":int(bwidth*0.5),
                "height":int(bheight*0.25),
                "z_index":88,
                "scale_option":'width',
                "image":foreground,
                "mask":mask
        }

    elif position=='right_bottom':
        
        scale = int(bwidth*0.35) / width
        new_height = int(height * scale)

        layer = {
                "x":bwidth-int(bwidth*0.35)-24,
                "y":bheight-new_height-24,
                "width":int(bwidth*0.35),
                "height":int(bheight*0.25),
                "z_index":88,
                "scale_option":'width',
                "image":foreground,
                "mask":mask
        }


    elif position=='center_top':
        
        scale = int(bwidth*0.5) / width
        new_height = int(height * scale)

        layer = {
                "x":int(bwidth*0.25),
                "y":24,
                "width":int(bwidth*0.5),
                "height":int(bheight*0.25),
                "z_index":88,
                "scale_option":'width',
                "image":foreground,
                "mask":mask
        }

    elif position=='right_top':
        
        scale = int(bwidth*0.35) / width
        new_height = int(height * scale)

        layer = {
                "x":bwidth-int(bwidth*0.35)-24,
                "y":24,
                "width":int(bwidth*0.35),
                "height":int(bheight*0.25),
                "z_index":88,
                "scale_option":'width',
                "image":foreground,
                "mask":mask
        }
    elif position=='left_top':
        
        scale = int(bwidth*0.35) / width
        new_height = int(height * scale)

        layer = {
                "x":24,
                "y":24,
                "width":int(bwidth*0.35),
                "height":int(bheight*0.25),
                "z_index":88,
                "scale_option":'width',
                "image":foreground,
                "mask":mask
        }
    elif position=='left_bottom':
        
        scale = int(bwidth*0.35) / width
        new_height = int(height * scale)

        layer = {
                "x":24,
                "y":bheight-new_height-24,
                "width":int(bwidth*0.35),
                "height":int(bheight*0.25),
                "z_index":88,
                "scale_option":'width',
                "image":foreground,
                "mask":mask
        }
                
    # width, height = bg_image.size

    layer_image=layer['image']
    layer_mask=layer['mask']
    
    bg_image=merge_images(bg_image,
                        layer_image,
                        layer_mask,
                        layer['x'],
                        layer['y'],
                        layer['width'],
                        layer['height'],
                        layer['scale_option'],
                        is_multiply_blend )
                   
    bg_image=bg_image.convert('RGB')
    
    return bg_image


def count_files_in_directory(directory):
    file_count = 0
    for _, _, files in os.walk(directory):
        file_count += len(files)
    return file_count

def save_json_to_file(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file)

def draw_rectangle(image, grid, color,width):
    x, y, w, h = grid
    draw = ImageDraw.Draw(image)
    draw.rectangle([(x, y), (x+w, y+h)], outline=color,width=width)

def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def padding_rectangle(grid, padding):
    x, y, w, h = grid
    x -= padding
    y -= padding
    w += 2 * padding
    h += 2 * padding
    return (x, y, w, h)

class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")


FONT_PATH= os.path.abspath(os.path.join(os.path.dirname(__file__),'../assets/王汉宗颜楷体繁.ttf'))

MAX_RESOLUTION=8192

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


# 颜色迁移
# Color-Transfer-between-Images https://github.com/chia56028/Color-Transfer-between-Images/blob/master/color_transfer.py

def get_mean_and_std(x):
	x_mean, x_std = cv2.meanStdDev(x)
	x_mean = np.hstack(np.around(x_mean,2))
	x_std = np.hstack(np.around(x_std,2))
	return x_mean, x_std

def color_transfer(source,target):
	# sources = ['s1','s2','s3','s4','s5','s6']
	# targets = ['t1','t2','t3','t4','t5','t6']

     # 将PIL的Image类型转换为OpenCV的numpy数组
    source = cv2.cvtColor(np.array(source), cv2.COLOR_RGB2LAB)
    target = cv2.cvtColor(np.array(target), cv2.COLOR_RGB2LAB)

    s_mean, s_std = get_mean_and_std(source)
    t_mean, t_std = get_mean_and_std(target)

    height, width, channel = source.shape
	
    for i in range(0,height):
        for j in range(0,width):
            for k in range(0,channel):
                x = source[i,j,k]
                x = ((x-s_mean[k])*(t_std[k]/s_std[k]))+t_mean[k]
				# round or +0.5
                x = round(x)
				# boundary check
                x = 0 if x<0 else x
                x = 255 if x>255 else x
                source[i,j,k] = x
    
    source = cv2.cvtColor(source,cv2.COLOR_LAB2RGB)
 
    # 创建PIL图像对象
    image_pil = Image.fromarray(source)
    
    return image_pil



# 组合
def create_big_image(image_folder, image_count):
    # 计算行数和列数
    rows = math.ceil(math.sqrt(image_count))
    cols = math.ceil(image_count / rows)

    # 获取每个小图的尺寸
    small_width = 100
    small_height = 100

    # 计算大图的尺寸
    big_width = small_width * cols
    big_height = small_height * rows

    # 创建一个新的大图
    big_image = Image.new('RGB', (big_width, big_height))

    # 获取所有图片文件的路径
    image_files = [f for f in os.listdir(image_folder) if os.path.isfile(os.path.join(image_folder, f))]

    # 遍历所有图片文件
    for i, image_file in enumerate(image_files):
        # 打开图片并调整大小
        image = Image.open(os.path.join(image_folder, image_file))
        image = image.resize((small_width, small_height))

        # 计算当前小图的位置
        row = i // cols
        col = i % cols
        x = col * small_width
        y = row * small_height

        # 将小图粘贴到大图上
        big_image.paste(image, (x, y))

    return big_image

# # 调用方法并保存大图
# image_folder = 'path/to/folder/containing/images'
# image_count = 100
# big_image = create_big_image(image_folder, image_count)
# big_image.save('path/to/save/big_image.jpg')



def naive_cutout(img, mask,invert=True):
    """
    Perform a simple cutout operation on an image using a mask.

    This function takes a PIL image `img` and a PIL image `mask` as input.
    It uses the mask to create a new image where the pixels from `img` are
    cut out based on the mask.

    The function returns a PIL image representing the cutout of the original
    image using the mask.
    """

    # img=img.convert("RGBA")
    mask=mask.convert("RGBA")

    empty = Image.new("RGBA", (mask.size), 0)

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
    
 
    return {
        "result":result,
        "image_path":image_path,
        "im_tensor":pil2tensor(im.convert('RGB')),
        "im_rgba_tensor":pil2tensor(im)
    }


# 提取不透明部分
def get_not_transparent_area(image):
    # 将PIL的Image类型转换为OpenCV的numpy数组
    image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGRA)

    # 分离图像的RGBA通道
    rgba = cv2.split(image_np)
    alpha = rgba[3]

    # 使用阈值将非透明部分转换为纯白色（255），透明部分转换为纯黑色（0）
    _, mask = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)

    # 获取非透明区域的边界框
    coords = cv2.findNonZero(mask)
    x, y, w, h = cv2.boundingRect(coords)

    return (x, y, w, h)




def generate_gradient_image(width, height, start_color_hex, end_color_hex):
    image = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(image)

    if len(start_color_hex) == 7:
        start_color_hex += "FF"
    if len(end_color_hex) == 7:
        end_color_hex += "FF"

    start_color_hex = start_color_hex.lstrip("#")
    end_color_hex = end_color_hex.lstrip("#")

    # 将十六进制颜色代码转换为RGBA元组，包括透明度
    start_color = tuple(int(start_color_hex[i:i+2], 16) for i in (0, 2, 4, 6))
    end_color = tuple(int(end_color_hex[i:i+2], 16) for i in (0, 2, 4, 6))

    for y in range(height):
        # 计算当前行的颜色
        r = int(start_color[0] + (end_color[0] - start_color[0]) * y / height)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * y / height)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * y / height)
        a = int(start_color[3] + (end_color[3] - start_color[3]) * y / height)

        # 绘制当前行的渐变色
        draw.line((0, y, width, y), fill=(r, g, b, a))

    # Create a mask from the image's alpha channel
    mask = image.split()[-1]

    # Convert the mask to a black and white image
    mask = mask.convert('L')

    image=image.convert('RGB')

    return (image, mask)

# 示例用法
# width = 500
# height = 200
# start_color_hex = 'FF0000FF'  # 红色，完全不透明
# end_color_hex = '0000FFFF'  # 蓝色，完全不透明

# gradient_image = generate_gradient_image(width, height, start_color_hex, end_color_hex)
# gradient_image.save('gradient_image.png')

def rgb_to_hex(rgb):
    r, g, b = rgb
    hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
    return hex_color


# 读取不了分层
def load_psd(image):
    layers=[]
    print('load_psd',image.format)
    if image.format=='PSD':
        layers = [frame.copy() for frame in ImageSequence.Iterator(image)]
        print('#PSD',len(layers))
    else:
        image = ImageOps.exif_transpose(image) #校对方向
    layers.append(image)
    return layers


def load_image(fp,white_bg=False):
    im = Image.open(fp)

    # ims=load_psd(im)
    im = ImageOps.exif_transpose(im) #校对方向
    ims=[im]

    images=[]
 
    for i in ims:
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
        
        images.append({
            "image":image,
            "mask":mask
        })
        
    return images

def load_image_and_mask_from_url(url, timeout=10):
    # Load the image from the URL
    response = requests.get(url, timeout=timeout)

    content_type = response.headers.get('Content-Type')
    
    image = Image.open(BytesIO(response.content))

    # Create a mask from the image's alpha channel
    mask = image.convert('RGBA').split()[-1]

    # Convert the mask to a black and white image
    mask = mask.convert('L')

    image=image.convert('RGB')

    return (image, mask)


# 获取图片s
def get_images_filepath(f,white_bg=False):
    images = []
 
    if os.path.isdir(f):
        for root, dirs, files in os.walk(f):
            for file in files:
                file_path = os.path.join(root, file)
                file_name=os.path.basename(file_path)
                try:
                    imgs=load_image(file_path,white_bg)
                    for img in imgs:
                        images.append({
                            "image":img['image'],
                            "mask":img['mask'],
                            "file_path":file_path,
                            "file_name":file_name,
                            "psd":len(imgs)>1
                        })
                except:
                    print('非图片',file_path)
 
    elif os.path.isfile(f):
        try:
            file_path = os.path.join(root, f)
            file_name=os.path.basename(file_path)
            imgs=load_image(f,white_bg)
            for img in imgs:
                images.append({
                    "image":img['image'],
                    "mask":img['mask'],
                    "file_path":file_path,
                    "file_name":file_name,
                    "psd":len(imgs)>1
                })
        except:
            print('非图片',f)
    else:
        print('路径不存在或无效',f)

    return images



def get_average_color_image(image):
    # 打开图片
    # image = Image.open(image_path)

    # 将图片转换为RGB模式
    image = image.convert("RGB")

    # 获取图片的像素值
    pixel_data = image.load()

    # 初始化颜色总和和像素数量
    total_red = 0
    total_green = 0
    total_blue = 0
    pixel_count = 0

    # 遍历图片的每个像素
    for i in range(image.width):
        for j in range(image.height):
            # 获取像素的RGB值
            r, g, b = pixel_data[i, j]

            # 累加颜色值
            total_red += r
            total_green += g
            total_blue += b

            # 像素数量加1
            pixel_count += 1

    # 计算平均颜色值
    average_red = int(total_red // pixel_count)
    average_green = int(total_green // pixel_count)
    average_blue = int(total_blue // pixel_count)

    # 返回平均颜色值

    im = Image.new("RGB", (image.width, image.height), (average_red, average_green, average_blue))

    hex=rgb_to_hex((average_red, average_green, average_blue))
    return (im,hex)



# 创建噪声图像
def create_noisy_image(width, height, mode="RGB", noise_level=128, background_color="#FFFFFF"):
    
    background_rgb = tuple(int(background_color[i:i+2], 16) for i in (1, 3, 5))
    image = Image.new(mode, (width, height), background_rgb)

    # 创建空白图像
    # image = Image.new(mode, (width, height))

    # 遍历每个像素，并随机设置像素值
    pixels = image.load()
    for i in range(width):
        for j in range(height):
            # 随机生成噪声值
            noise_r = random.randint(-noise_level, noise_level)
            noise_g = random.randint(-noise_level, noise_level)
            noise_b = random.randint(-noise_level, noise_level)

            # 像素值加上噪声值，并限制在0-255的范围内
            r = max(0, min(pixels[i, j][0] + noise_r, 255))
            g = max(0, min(pixels[i, j][1] + noise_g, 255))
            b = max(0, min(pixels[i, j][2] + noise_b, 255))

            # 设置像素值
            pixels[i, j] = (r, g, b)

    image=image.convert(mode)
    return image


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

 
def enhance_depth_map(depth_map, contrast):
    # 打开深度图像
    # depth_map = Image.open(im)
    
    # 创建对比度增强对象
    enhancer = ImageEnhance.Contrast(depth_map)
    
    # 对深度图像进行对比度增强
    enhanced_depth_map = enhancer.enhance(contrast)
    
    return enhanced_depth_map


def detect_faces(image):
    # Read the image
    # image = cv2.imread('people1.jpg')
    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGRA)

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Load the pre-trained face detector
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Detect faces in the image
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=5, minSize=(50, 50))

    # Create a black and white mask image
    mask = np.zeros_like(gray)

    # Loop over all detected faces
    for (x, y, w, h) in faces:
        # Draw rectangles around the detected faces
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Set the corresponding region in the mask image to white
        mask[y:y+h, x:x+w] = 255

    # Display the number of faces detected
    print('Faces Detected:', len(faces))

    mask = Image.fromarray(cv2.cvtColor(mask, cv2.COLOR_BGRA2RGBA))

    return mask


def areaToMask(x,y,w,h,image):
    # 创建一个与原图片大小相同的空白图片
    mask = Image.new('L', image.size)

    # 创建一个可用于绘制的对象
    draw = ImageDraw.Draw(mask)

    # 在空白图片上绘制一个矩形，表示要处理的区域
    draw.rectangle((x, y, x+w, y+h), fill=255)

    # 将处理区域之外的部分填充为黑色
    draw.rectangle((0, 0, image.width, y), fill=0)
    draw.rectangle((0, y+h, image.width, image.height), fill=0)
    draw.rectangle((0, y, x, y+h), fill=0)
    draw.rectangle((x+w, y, image.width, y+h), fill=0)
    return mask


# def merge_images(bg_image, layer_image,mask, x, y, width, height):
#     # 打开底图
#     # bg_image = Image.open(background)
#     bg_image=bg_image.convert("RGBA")

#     # 打开图层
#     layer_image=layer_image.convert("RGBA")
#     layer_image = layer_image.resize((width, height))
#     # mask = Image.new("L", layer_image.size, 255)
#     mask = mask.resize((width, height))
#     # 在底图上粘贴图层
#     bg_image.paste(layer_image, (x, y), mask=mask)

#     # 输出合成后的图片
#     # bg_image.save("output.jpg")
#     return bg_image


import cv2
import numpy as np

# ps的正片叠底
# 可以基于https://www.cnblogs.com/jsxyhelu/p/16947810.html ，用gpt写python代码
def multiply_blend(image1, image2):
    image1=pil_to_opencv(image1)
    image2=pil_to_opencv(image2)
    # 将图像转换为浮点型
    image1 = image1.astype(float)
    image2 = image2.astype(float)
    if image1.shape != image2.shape:
        image1 = cv2.resize(image1, (image2.shape[1], image2.shape[0]))
        
    # 归一化图像
    image1 /= 255.0
    image2 /= 255.0

    # 正片叠底混合
    blended = image1 * image2

    # 将图像还原为8位无符号整数
    blended = (blended * 255).astype(np.uint8)

    blended=opencv_to_pil(blended)
    return blended

# # 读取图像
# image1 = cv2.imread('1.png')
# image2 = cv2.imread('3.png')

# # 进行正片叠底混合
# result = multiply_blend(image1, image2)

# cv2.imwrite('result.jpg', result)


def merge_images(bg_image, layer_image, mask, x, y, width, height, scale_option,is_multiply_blend=False):
    # 打开底图
    bg_image = bg_image.convert("RGBA")

    # 打开图层
    layer_image = layer_image.convert("RGBA")
    # layer_image = layer_image.resize((width, height))

    # 根据缩放选项调整图像大小
    if scale_option == "height":
        # 按照高度比例缩放
        original_width, original_height = layer_image.size
        scale = height / original_height
        new_width = int(original_width * scale)
        layer_image = layer_image.resize((new_width, height))
    elif scale_option == "width":
        # 按照宽度比例缩放
        original_width, original_height = layer_image.size
        scale = width / original_width
        new_height = int(original_height * scale)
        layer_image = layer_image.resize((width, new_height))
    elif scale_option == "overall":
        # 整体缩放
        layer_image = layer_image.resize((width, height))

    elif scale_option == "longest":
        original_width, original_height = layer_image.size
        if original_width > original_height:
            new_width=width
            scale = width / original_width
            new_height = int(original_height * scale)
            x=0
            y=int((height-new_height)*0.5)
        else:
            new_height=height
            scale = height / original_height
            new_width = int(original_height * scale)
            x=int((width-new_width)*0.5)
            y=0
    # elif side == "shortest":
    #         if width < height:
    #              
    #         else:
    #              
    

    # 调整mask的大小
    nw, nh = layer_image.size
    mask = mask.resize((nw, nh))

    # # 分离出a通道
    # r, g, b, alpha = layer_image.split()
    # alpha = ImageOps.invert(alpha)
    # # 创建一个新的RGB图像
    # new_rgb_image = Image.new("RGB", layer_image.size)
    # # 将透明通道粘贴到新的RGB图像上
    # new_rgb_image.paste(layer_image, (0, 0), mask=alpha)
   
    # new_rgb_image.paste(layer_image, (x, y), mask=mask)
    # mask=new_rgb_image.convert('L')
    # mask = ImageOps.invert(mask)

    if is_multiply_blend:
        bg_image_white=Image.new("RGB", bg_image.size,(255, 255, 255))

        bg_image_white.paste(layer_image, (x, y), mask=mask)
        bg_image=multiply_blend(bg_image_white,bg_image)
        bg_image=bg_image.convert("RGBA")
    else:
        transparent_img = Image.new("RGBA",layer_image.size, (0, 0, 0, 0))
        transparent_img.paste(layer_image,(0, 0), mask)
        bg_image.paste(transparent_img, (x, y), transparent_img)


    # 输出合成后的图片
    return bg_image


def resize_2(img):
    # 检查图像的高度是否是2的倍数，如果不是，则调整高度
    if img.height % 2 != 0:
        img = img.resize((img.width, img.height + 1))

    # 检查图像的宽度是否是2的倍数，如果不是，则调整宽度
    if img.width % 2 != 0:
        img = img.resize((img.width + 1, img.height))

    return img

# TODO 几个像素点的底
def resize_image(layer_image, scale_option, width, height,color="white"):
    layer_image = layer_image.convert("RGB")
    original_width, original_height = layer_image.size
    
    if scale_option == "height":
        # Scale image based on height
        scale = height / original_height
        new_width = int(original_width * scale)
        layer_image = layer_image.resize((new_width, height))
        
    elif scale_option == "width":
        # Scale image based on width
        scale = width / original_width
        new_height = int(original_height * scale)
        layer_image = layer_image.resize((width, new_height))
        
    elif scale_option == "overall":
        # Scale image overall
        layer_image = layer_image.resize((width, height))
        
    elif scale_option == "center":
        # Scale image to minimum of width and height, center it, and fill extra area with black
        scale = min(width / original_width, height / original_height)
        new_width = math.ceil(original_width * scale)
        new_height = math.ceil(original_height * scale)
        resized_image = Image.new("RGB", (width, height), color=color)
        resized_image.paste(layer_image.resize((new_width, new_height)), ((width - new_width) // 2, (height - new_height) // 2))
        resized_image = resized_image.convert("RGB")
        resized_image=resize_2(resized_image)
        return resized_image
    elif scale_option == "longest":
    #暂时不用，  
        if original_width > original_height:
            new_width=width
            scale = width / original_width
            new_height = int(original_height * scale)
            x=0
            y=int((new_height-height)*0.5)
            resized_image = Image.new("RGB", (new_width, new_height), color=color)
            resized_image.paste(layer_image.resize((new_width, new_height)), (x,y))
            resized_image = resized_image.convert("RGB")
            resized_image=resize_2(resized_image)
            return resized_image
        else:
            new_height=height
            scale = height / original_height
            new_width = int(original_height * scale)
            x=int((new_width-width)*0.5)
            y=0
            resized_image = Image.new("RGB", (new_width, new_height), color=color)
            resized_image.paste(layer_image.resize((new_width, new_height)), (x,y))
            resized_image = resized_image.convert("RGB")
            resized_image=resize_2(resized_image)
            return resized_image

    
    layer_image=resize_2(layer_image)
    return layer_image






# def generate_text_image(text_list, font_path, font_size, text_color, vertical=True, spacing=0):
#     # Load Chinese font
#     font = ImageFont.truetype(font_path, font_size)

#     # Calculate image size based on the number of characters and orientation
#     if vertical:
#         width = font_size + 100
#         height = font_size * len(text_list) + (len(text_list) - 1) * spacing + 100
#     else:
#         width = font_size * len(text_list) + (len(text_list) - 1) * spacing + 100
#         height = font_size + 100

#     # Create a blank image
#     image = Image.new('RGBA', (width, height), (255, 255, 255,0))
#     draw = ImageDraw.Draw(image)

#     # Draw text
#     if vertical:
#         for i, char in enumerate(text_list):
#             char_position = (50, 50 + i * font_size)
#             draw.text(char_position, char, font=font, fill=text_color)
#     else:
#         for i, char in enumerate(text_list):
#             char_position = (50 + i * (font_size + spacing), 50)
#             draw.text(char_position, char, font=font, fill=text_color)

#     # Save the image
#     # image.save(output_image_path)

#     # 分离alpha通道
#     alpha_channel = image.split()[3]

#     # 创建一个只有alpha通道的新图像
#     alpha_image = Image.new('L', image.size)
#     alpha_image.putdata(alpha_channel.getdata())

#     image=image.convert('RGB')

#     return (image,alpha_image)
def generate_text_image(text, font_path, font_size, text_color, vertical=True, stroke=False, stroke_color=(0, 0, 0), stroke_width=1, spacing=0):
    # Split text into lines based on line breaks
    lines = text.split("\n")

    # 1. Determine layout direction
    if vertical:
        layout = "vertical"
    else:
        layout = "horizontal"

    # 2. Calculate absolute coordinates for each character
    char_coordinates = []
    if layout == "vertical":
        x = 0
        y = 0
        for i in range(len(lines)):
            line = lines[i]
            for char in line:
                char_coordinates.append((x, y))
                y += font_size + spacing
            x += font_size + spacing
            y = 0
    else:
        x = 0
        y = 0
        for line in lines:
            for char in line:
                char_coordinates.append((x, y))
                x += font_size + spacing
            y += font_size + spacing
            x = 0

    # 3. Calculate image width and height
    if layout == "vertical":
        width = (len(lines) * (font_size + spacing)) - spacing
        height = ((len(max(lines, key=len)) + 1) * (font_size + spacing)) + spacing
    else:
        width = (len(max(lines, key=len)) * (font_size + spacing)) - spacing
        height = ((len(lines) - 1) * (font_size + spacing)) + font_size

    # 4. Draw each character on the image
    image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, font_size)

    index = 0
    for i, line in enumerate(lines):
        for j, char in enumerate(line):
            x, y = char_coordinates[index]
            
            if stroke:
                draw.text((x-stroke_width, y), char, font=font, fill=stroke_color)
                draw.text((x+stroke_width, y), char, font=font, fill=stroke_color)
                draw.text((x, y-stroke_width), char, font=font, fill=stroke_color)
                draw.text((x, y+stroke_width), char, font=font, fill=stroke_color)
            
            draw.text((x, y), char, font=font, fill=text_color)
            index += 1

    # Separate alpha channel
    alpha_channel = image.split()[3]

    # Create a new image with only the alpha channel
    alpha_image = Image.new('L', image.size)
    alpha_image.putdata(alpha_channel.getdata())

    image = image.convert('RGB')

    return (image, alpha_image)



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

    return [{
                "filename": image_file,
                "subfolder": subfolder,
                "type": "temp"
                }]


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

    CATEGORY = "♾️Mixlab/Mask"

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

    CATEGORY = "♾️Mixlab/Mask"

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
    
    RETURN_TYPES = ('STRING','IMAGE','RGBA')
    RETURN_NAMES = ("file_path","IMAGE","RGBA",)

    OUTPUT_NODE = True

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    # INPUT_IS_LIST = True， 一个batch传进来
    OUTPUT_IS_LIST = (True,True,True,)
    # OUTPUT_NODE = True

    # 运行的函数
    def run(self,images,masks,invert,save,filename_prefix,prompt=None, extra_pnginfo=None):
        # print('TransparentImage',images.shape,images.size(),masks.shape,masks.size())
        # print(masks.shape,masks.size())

        ui_images=[]
        image_paths=[]
        
        count=images.shape[0]
        masks_new=[]
        nh=masks.shape[0]//count

        masks_new=masks

        if images.shape[0]==masks.shape[0] and  images.shape[1]==masks.shape[1] and  images.shape[2]==masks.shape[2]:
            print('TransparentImage',images.shape,images.size(),masks.shape,masks.size())
        else:
            #INPUT_IS_LIST = False, 一个batch传进来
            if nh*count==masks.shape[0]:
                masks_new=split_mask_by_new_height(masks,nh)
            else:
                masks_new=split_mask_by_new_height(masks,masks.shape[0])


        is_save=True if save=='yes' else False
        # filename_prefix += self.prefix_append

        images_rgb=[]
        images_rgba=[]

        for i in range(len(images)):
            image=images[i]
            mask=masks_new[i]

            result=doMask(image,mask,is_save,filename_prefix,invert,not is_save,prompt, extra_pnginfo)

            for item in result["result"]:
                ui_images.append(item)

            image_paths.append(result['image_path'])

            images_rgb.append(result['im_tensor'])
            images_rgba.append(result['im_rgba_tensor'])
        
        # ui.images 节点里显示图片，和 传参，image_path自定义的数据，需要写节点的自定义ui
        # result 里输出给下个节点的数据 
        # print('TransparentImage',len(images_rgb))
        
        return {"ui":{"images": ui_images,"image_paths":image_paths},"result": (image_paths,images_rgb,images_rgba)}



class ImagesPrompt:
    @classmethod
    def INPUT_TYPES(s):
        # input_dir = folder_paths.get_input_directory()
        # files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": { 
               "image_base64": ("STRING",{"multiline": False,"default": "","dynamicPrompts": False}),
               "text": ("STRING",{"multiline": True,"default": "","dynamicPrompts": True}),
            }
            }
    
    RETURN_TYPES = ("IMAGE","STRING",)
    RETURN_NAMES = ("image","text",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Input"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,)
    OUTPUT_NODE = False

    # 运行的函数
    def run(self,image_base64,text):
        image = base64_to_image(image_base64)
        image=image.convert('RGB')
        image=pil2tensor(image)
        return (image,text,)


class EnhanceImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "image": ("IMAGE",),
                                "contrast":("FLOAT", {"default": 0.5, 
                                                        "min":0, 
                                                        "max": 10, 
                                                        "step": 0.01,
                                                        "display": "slider"})
                            }
            }
    
    RETURN_TYPES = ('IMAGE',)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = True

    OUTPUT_IS_LIST = (True,)
  
    # 运行的函数
    def run(self,image,contrast):
        # print('EnhanceImage',len(image),image[0].shape)
        contrast=contrast[0]
        res=[]
        for ims in image:
            for im in ims:

                image=tensor2pil(im)
            
                image=enhance_depth_map(image,contrast)

                image=pil2tensor(image)

                res.append(image)
           
        return (res,)




class LoadImages_:
    @classmethod
    def INPUT_TYPES(s):
        
        return {"required":
                    {"images": ("IMAGEBASE64",), 
                     },
                }

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "load_image"
    def load_image(self, images):

        # print(images)
        ims=[]
        for im in images['base64']:
            image = base64_to_image(im)
            image=image.convert('RGB')
            image=pil2tensor(image)
            ims.append(image)

        image1 = ims[0]
        for image2 in ims[1:]:
            if image1.shape[1:] != image2.shape[1:]:
                image2 = comfy.utils.common_upscale(image2.movedim(-1, 1), image1.shape[2], image1.shape[1], "bilinear", "center").movedim(1, -1)
            image1 = torch.cat((image1, image2), dim=0)
        return (image1,)
        
 


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
                                "file_path": ("STRING",{"multiline": False,"default": "","dynamicPrompts": False}),
                            },
                "optional":{
                    "white_bg": (["disable","enable"],),
                    "newest_files": (["enable", "disable"],),
                    "index_variable":("INT", {
                        "default": 0, 
                        "min": -1, #Minimum value
                        "max": 2048, #Maximum value
                        "step": 1, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    }),
                    "watcher":(["disable","enable"],),
                    "result": ("WATCHER",),#为了激活本节点运行
                     "prompt": ("PROMPT",),
                    # "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                }
            }
    
    RETURN_TYPES = ('IMAGE','MASK','STRING','STRING',)
    RETURN_NAMES = ("IMAGE","MASK","prompt_for_FloatingVideo","filepaths",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    # INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,False,True,)
  
    global watcher_folder
    watcher_folder=None

    # 运行的函数
    def run(self,file_path,white_bg,newest_files,index_variable,watcher,result,prompt):
        global watcher_folder
        # print('###监听:',watcher_folder,watcher,file_path,result)

        if watcher_folder==None:
            watcher_folder = FolderWatcher(file_path)

        watcher_folder.set_folder_path(file_path)
        
        if watcher=='enable': 
            # 在这里可以进行其他操作，监听会在后台持续
            watcher_folder.set_folder_path(file_path)
            watcher_folder.start()
        else:
            if watcher_folder!=None:
                watcher_folder.stop()

        #TODO 修bug： ps6477. tmp 
        images=get_images_filepath(file_path,white_bg=='enable')

        # 当开启了监听，则取最新的，第一个文件
        if watcher=='enable':
            index_variable=0
            newest_files='enable'

        # 排序
        sorted_files = sorted(images, key=lambda x: os.path.getmtime(x['file_path']), reverse=(newest_files=='enable'))

        imgs=[]
        masks=[]
        file_names=[]

        for im in sorted_files:
            imgs.append(im['image'])
            masks.append(im['mask'])
            file_names.append(im['file_name'])
        
        # print('index_variable',index_variable)
        
        try:
            if index_variable!=-1:
                imgs=[imgs[index_variable]] if index_variable < len(imgs) else None
                masks=[masks[index_variable]] if index_variable < len(masks) else None
                file_names=[file_names[index_variable]] if index_variable < len(file_names) else None
        except Exception as e:
            print("发生了一个未知的错误：", str(e))

        # print('#prompt::::',prompt)
        return  {"ui": {"seed": [1]}, "result":(imgs,masks,prompt,file_names,)}


# TODO 扩大选区的功能,重新输出mask
class ImageCropByAlpha:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "image": ("IMAGE",),
                             "RGBA": ("RGBA",),  },
                }
    
    RETURN_TYPES = ("IMAGE","MASK","MASK","INT","INT","INT","INT",)
    RETURN_NAMES = ("IMAGE","MASK","AREA_MASK","x","y","width","height",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,True,True,True,True,True,)

    def run(self,image,RGBA):
        # print(image.shape,RGBA.shape)

        image=image[0]
        RGBA=RGBA[0]

        bf_im = tensor2pil(image)

        # print(RGBA)
        im=tensor2pil(RGBA)

        # 要把im的alpha通道转为mask
        im=im.convert('RGBA')
        red, green, blue, alpha = im.split()

        im=naive_cutout(bf_im,alpha)
        x, y, w, h=get_not_transparent_area(im)
        # print('#ForImageCrop:',w, h,x, y,)

        x = min(x, image.shape[2] - 1)
        y = min(y, image.shape[1] - 1)
        to_x = w + x
        to_y = h + y

        x_1=x
        y_1=y
        width_1=w
        height_1=h

        img = image[:,y:to_y, x:to_x, :]
        # tensor2pil(img).save('test2.png')

        # 原图的mask
        ori=RGBA[:,y:to_y, x:to_x, :]
        ori=tensor2pil(ori)
        # ori.save('test.png')

        # 创建一个新的图像对象，大小和模式与原始图像相同
        new_image = Image.new("RGBA", ori.size)

        # 获取原始图像的像素数据
        pixel_data = ori.load()

        # 获取新图像的像素数据
        new_pixel_data = new_image.load()

        # 遍历图像的每个像素
        for y in range(ori.size[1]):
            for x in range(ori.size[0]):
                # 获取当前像素的RGBA值
                r, g, b, a = pixel_data[x, y]

                # 如果a通道不为0（不透明），将当前像素设置为白色
                if a != 0:
                    new_pixel_data[x, y] = (255, 255, 255, 255)
                else:
                    new_pixel_data[x, y] = (0,0,0,0)

        # 保存修改后的图像
        # new_image.save("output.png")
                    
        ori=new_image.convert('L')
        # threshold = 128
        # ori = ori.point(lambda x: 0 if x < threshold else 255, '1')
        ori=pil2tensor(ori)

        # 矩形区域，mask
        b_image =AreaToMask_run(RGBA)
        # img=None
        # b_image=None
        return ([img],[ori],[b_image],[x_1],[y_1],[width_1],[height_1],)





class TextImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
            
                    "text": ("STRING",{"multiline": True,"default": "龍馬精神迎新歲","dynamicPrompts": False}),
                    "font_path": ("STRING",{"multiline": False,"default": FONT_PATH,"dynamicPrompts": False}),
                    "font_size": ("INT",{
                                "default":100, 
                                "min": 100, #Minimum value
                                "max": 1000, #Maximum value
                                "step": 1, #Slider's step
                                "display": "number" # Cosmetic only: display as "number" or "slider"
                                }), 
                    "spacing": ("INT",{
                                "default":12, 
                                "min": -200, #Minimum value
                                "max": 200, #Maximum value
                                "step": 1, #Slider's step
                                "display": "number" # Cosmetic only: display as "number" or "slider"
                                }), 
                    "text_color":("STRING",{"multiline": False,"default": "#000000","dynamicPrompts": False}),
                    "vertical":("BOOLEAN", {"default": True},),
                    "stroke":("BOOLEAN", {"default": False},),
                             },
                }
    
    RETURN_TYPES = ("IMAGE","MASK",)
    # RETURN_NAMES = ("WIDTH","HEIGHT","X","Y",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,)

    def run(self,text,font_path,font_size,spacing,text_color,vertical,stroke):
        
        # text_list=list(text)
        # stroke=False, stroke_color=(0, 0, 0), stroke_width=1, spacing=0
        img,mask=generate_text_image(text,font_path,font_size,text_color,vertical,stroke,(0, 0, 0),1,spacing)
        
        img=pil2tensor(img)
        mask=pil2tensor(mask)

        return (img,mask,)

class LoadImagesFromURL:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "url": ("STRING",{"multiline": True,"default": "https://","dynamicPrompts": False}),
                             },
                "optional":{
                    "seed": (any_type,  {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                }
                }
    
    RETURN_TYPES = ("IMAGE","MASK",)
    RETURN_NAMES = ("images","masks",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (True,True,)


    global urls_image
    urls_image={}

    def run(self,url,seed=0):
        global urls_image
        print(urls_image)
        def filter_http_urls(urls):
            filtered_urls = []
            for url in urls.split('\n'):
                if url.startswith('http'):
                    filtered_urls.append(url)
            return filtered_urls

        filtered_urls = filter_http_urls(url)

        images=[]
        masks=[]

        for img_url in filtered_urls:
            try:
                if img_url in urls_image:
                    img,mask=urls_image[img_url]
                else:
                    img,mask=load_image_and_mask_from_url(img_url)
                    urls_image[img_url]=(img,mask)

                img1=pil2tensor(img)
                mask1=pil2tensor(mask)

                images.append(img1)
                masks.append(mask1)
            except Exception as e:
                print("发生了一个未知的错误：", str(e))
            
        return (images,masks,)




class SvgImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "upload":("SVG",),},
                }
    
    RETURN_TYPES = ("IMAGE","LAYER")
    RETURN_NAMES = ("IMAGE","layers",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,True,)

    def run(self,upload):
        layers=[]

        image = base64_to_image(upload['image'])
        image=image.convert('RGB')
        image=pil2tensor(image)

        for layer in upload['data']:
            layers.append(layer)
    
        return (image,layers,)



class Image3D:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "upload":("THREED",),}, 
                "optional":{
                    "material": ("IMAGE",),
                    }
                }
    
    RETURN_TYPES = ("IMAGE","MASK","IMAGE","IMAGE",)
    RETURN_NAMES = ("IMAGE","MASK","BG_IMAGE","MATERIAL",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/3D"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,False,False,False,)
    OUTPUT_NODE = True

    def run(self,upload,material=None):
        # print('material',material)
        # print(upload )
        image = base64_to_image(upload['image'])

        mat=None
        if 'material' in upload and upload['material']:
            mat=base64_to_image(upload['material'])
            mat=mat.convert('RGB')
            mat=pil2tensor(mat)

        mask = image.split()[3]
        image=image.convert('RGB')
        
        mask=mask.convert('L')

        bg_image=None
        if 'bg_image' in upload and upload['bg_image']:
            bg_image = base64_to_image(upload['bg_image'])
            bg_image=bg_image.convert('RGB')
            bg_image=pil2tensor(bg_image)


        mask=pil2tensor(mask)
        image=pil2tensor(image)
        
        m=[]
        if not material is None:
            m=create_temp_file(material[0])
        
        return {"ui":{"material": m},"result": (image,mask,bg_image,mat,)}



def AreaToMask_run(RGBA):
    # print(RGBA)
    im=tensor2pil(RGBA)
    im=naive_cutout(im,im)
    x, y, w, h=get_not_transparent_area(im)
        
    im=im.convert("RGBA")
        # print('#AreaToMask:',im)
    img=areaToMask(x,y,w,h,im)
    img=img.convert("RGBA")
    mask=pil2tensor(img)

    channels = ["red", "green", "blue", "alpha"]
    # print(mask,mask.shape)
    mask = mask[:, :, :, channels.index("green")]

    return mask


class AreaToMask:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "RGBA": ("RGBA",),  },
                }
    
    RETURN_TYPES = ("MASK",)
    # RETURN_NAMES = ("WIDTH","HEIGHT","X","Y",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Mask"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,RGBA):

        mask =AreaToMask_run(RGBA)

        return (mask,)


class FaceToMask:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "image": ("IMAGE",)},
                }
    
    RETURN_TYPES = ("MASK",)
    # RETURN_NAMES = ("WIDTH","HEIGHT","X","Y",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Mask"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,image):
        # print(image)
        im=tensor2pil(image)
        mask=detect_faces(im)

        mask=pil2tensor(mask)
        channels = ["red", "green", "blue", "alpha"]
        mask = mask[:, :, :, channels.index("green")]

        return (mask,)


class CompositeImages:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": { 
                    "foreground": ("IMAGE",),
                    "mask":("MASK",),
                    "background": ("IMAGE",),
                    },
             "optional":{
                           
                  "is_multiply_blend":  ("BOOLEAN", {"default": False}),
                  "position":  (['overall',"center_bottom","center_top","right_bottom","left_bottom","right_top","left_top"],),    
                    }
                }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    # OUTPUT_IS_LIST = (True,)

    def run(self, foreground,mask,background,is_multiply_blend,position):
        foreground= tensor2pil(foreground)
        mask= tensor2pil(mask)
        background= tensor2pil(background)
        res=composite_images(foreground,background,mask,is_multiply_blend,position)
        
        return (pil2tensor(res),)




class EmptyLayer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": { 
                "width": ("INT",{
                    "default":512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
               "height": ("INT",{
                    "default": 512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
            },
        
                }
    
    RETURN_TYPES = ("LAYER",)
    RETURN_NAMES = ("layers",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    OUTPUT_IS_LIST = (True,)

    def run(self, width,height):
        blank_image = Image.new("RGB", (width, height))
        
        mask=blank_image.convert('L')

        blank_image=pil2tensor(blank_image)
        mask=pil2tensor(mask)

        layer_n=[{
            "x":0,
            "y":0,
            "width":width,
            "height":height,
            "z_index":0,
            "scale_option":'width',
            "image":blank_image,
            "mask":mask
        }]
        return (layer_n,)


class NewLayer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            
            "required": { 
                "x": ("INT",{
                    "default": 0, 
                    "min": -1024, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "y": ("INT",{
                    "default": 0, 
                    "min": -1024, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "width": ("INT",{
                    "default": 512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "height": ("INT",{
                    "default": 512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "z_index": ("INT",{
                    "default": 0, 
                    "min":0, #Minimum value
                    "max": 100, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "scale_option": (["width","height",'overall'],),
                "image": (any_type,),
            },
             "optional":{
                    "mask": ("MASK",{"default": None}),
                    "layers": ("LAYER",{"default": None}), 
                    "canvas": ("IMAGE",{"default": None}), 
                }
                }
    
    RETURN_TYPES = ("LAYER",)
    RETURN_NAMES = ("layers",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    def run(self,x,y,width,height,z_index,scale_option,image,mask=None,layers=None,canvas=None):
        # print(x,y,width,height,z_index,image,mask)
        
        if mask==None:
            im=tensor2pil(image[0])
            mask=im.convert('L')
            mask=pil2tensor(mask)
        else:
            mask=mask[0]
        
        layer_n=[{
            "x":x[0],
            "y":y[0],
            "width":width[0],
            "height":height[0],
            "z_index":z_index[0],
            "scale_option":scale_option[0],
            "image":image[0],
            "mask":mask
        }]

        if layers!=None:
            layer_n=layer_n+layers

        return (layer_n,)



def createMask(image,x,y,w,h):
    mask = Image.new("L", image.size)
    pixels = mask.load()
    # 遍历指定区域的像素，将其设置为黑色（0 表示黑色）
    for i in range(int(x), int(x + w)):
        for j in range(int(y), int(y + h)):
            pixels[i, j] = 255
    # mask.save("mask.png")
    return mask

def splitImage(image, num):
    width, height = image.size

    num_rows = int(num ** 0.5)
    num_cols = int(num / num_rows)
    
    grid_width = int(width // num_cols)
    grid_height = int(height // num_rows)

    grid_coordinates = []
    for i in range(num_rows):
        for j in range(num_cols):
            x = int(j * grid_width)
            y = int(i * grid_height)
            grid_coordinates.append((x, y, grid_width, grid_height))

    return grid_coordinates


def centerImage(margin,canvas):
    w,h=canvas.size

    l,t,r,b=margin

    x=l
    y=t
    width=w-r-l
    height=h-t-b

    return (x,y,width,height)

# # 读取图片
# image = Image.open("path_to_your_image.jpg")

# # 定义要切割的区域数量
# num = 9

# # 切割图片
# grid_coordinates = splitImage(image, num)

# # 输出切割区域坐标
# for i, coordinates in enumerate(grid_coordinates):
#     print(f"Region {i + 1}: x={coordinates[0]}, y={coordinates[1]}, width={coordinates[2]}, height={coordinates[3]}")


class SplitImage:
    @classmethod
    def INPUT_TYPES(s):
        return { 
            "required": { 
                "image": ("IMAGE",), 
                "num": ("INT",{
                    "default": 4, 
                    "min": 1, #Minimum value
                    "max": 500, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "seed": ("INT",{
                    "default": 4, 
                    "min": 1, #Minimum value
                    "max": 500, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
            }
                }
    
    RETURN_TYPES = ("_GRID","_GRID","MASK",)
    RETURN_NAMES = ("grids","grid","mask",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = False
    # OUTPUT_IS_LIST = (True,)

    def run(self,image,num,seed):
        
        if type(seed) == list and len(seed)==1:
            seed=seed[0]

        image=tensor2pil(image)
        
        grids=splitImage(image,num)

        if seed>num:
            num=seed % (num + 1)
        else:
            num=seed-1
        
        print('#SplitImage',seed)

        num=max(0,num) 
        num=min(num,len(grids)-1)
        
        g=grids[num]

        x,y,w,h=g
        mask=createMask(image, x,y,w,h)
        mask=pil2tensor(mask)

        return (grids,g,mask,)



class CenterImage:
    @classmethod
    def INPUT_TYPES(s):
        return { 
            "required": { 
                "canvas": ("IMAGE",), 
                "left": ("INT",{
                    "default":24, 
                    "min": 0, #Minimum value
                    "max": 5000, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
               "top": ("INT",{
                    "default":24, 
                    "min": 0, #Minimum value
                    "max": 5000, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "right": ("INT",{
                    "default": 24, 
                    "min": 0, #Minimum value
                    "max": 5000, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                 "bottom": ("INT",{
                    "default": 24, 
                    "min": 0, #Minimum value
                    "max": 5000, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
            }
                }
    
    RETURN_TYPES = ("_GRID","MASK",)
    RETURN_NAMES = ("grid","mask",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = False
    # OUTPUT_IS_LIST = (True,)

    def run(self,canvas,left,top,right,bottom):
        canvas=tensor2pil(canvas)

        grid=centerImage((left,top,right,bottom),canvas)

        mask=createMask(canvas,left,top,canvas.width-left-right,canvas.height-top-bottom)

        return (grid,pil2tensor(mask),)

class GridDisplayAndSave:
    @classmethod
    def INPUT_TYPES(s):
        return { 
            "required": {
                "labels": ("STRING", 
                                        {
                                            "multiline": True, 
                                            "default": "",
                                            "forceInput": True,
                                            "dynamicPrompts": False
                                        }),
                "grids": ("_GRID",),
                
                "image": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "mixlab/grids"})
            }
                }
    
    RETURN_TYPES = ( )
    RETURN_NAMES = ( )

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = True
    OUTPUT_NODE = True
    # OUTPUT_IS_LIST = (True,)

    def run(self,labels,grids,image,filename_prefix):

        # print(image.shape)

        img= tensor2pil(image[0])

        for grid in grids:
            draw_rectangle(img, grid, 'red',8)

        #获取临时目录：temp
        output_dir = folder_paths.get_temp_directory()

        (
            full_output_folder,
            filename,
            counter,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path('tmp_', output_dir)
        
        image_file = f"{filename}_{counter:05}.png"

        image_path=os.path.join(full_output_folder, image_file)
        # 保存图片
        img.save(image_path,compress_level=6)
        width, height = img.size

        (
            full_output_folder,
            filename,
            counter,
            _,
            _,
        ) = folder_paths.get_save_image_path(filename_prefix[0], output_dir)


        data_converted = [{
            "label":labels[i],
            "grid":[float(grids[i][0]),
                           float(grids[i][1]),
                           float(grids[i][2]),
                           float(grids[i][3])
                           ]
        } for i in range(len(grids))]

        data={
            "width":int(width),
            "height":int(height),
            "grids":data_converted
        }

        save_json_to_file(data,os.path.join(full_output_folder,f"${filename}_{counter:05}.json"))

        return {"ui":{"image": [{
                "filename": image_file,
                "subfolder": subfolder,
                "type":"temp"
            }],
            "json":[data["width"],data['height'],data["grids"]]
            },"result": ()}
        # return {"ui":{"image": [ ],
             
        #     },"result": ()}

class GridInput:
    @classmethod
    def INPUT_TYPES(s):
        return { 
            "required": {
                "grids": ("STRING", 
                                        {
                                            "multiline": True, 
                                            "default": "",
                                            "dynamicPrompts": False
                                        }),
                "padding":("INT",{
                    "default": 24, 
                    "min": -500, #Minimum value
                    "max": 5000, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                
            },
            "optional":{
                    "width":("INT",{
                        "forceInput": True,
                    }),
                     "height":("INT",{
                        "forceInput": True,
                    }),
                }

                }
    
    RETURN_TYPES = ("_GRID","STRING","IMAGE",)
    RETURN_NAMES = ("grids","labels","image",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Input"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,False,)
    OUTPUT_NODE = True

    def run(self,grids,padding,width=[-1],height=[-1]):
        # print(padding[0],grids[0])
        width=width[0]
        height=height[0]

        grids=grids[0]
        data=json.loads(grids)
        grids=data['grids']

        if width>-1:
            data['width']=width
        if height>-1:
            data['height']=height
    
        new_grids=[]
        labels=[]
        
        for g in grids:
            labels.append(g['label'])
            new_grids.append(padding_rectangle(g['grid'],padding[0]))

        image = Image.new("RGB", (int(data['width']),int(data["height"])), "white")
        im=pil2tensor(image)
        # image=create_temp_file(im)

        data_converted = [{
            "label":labels[i],
            "grid":[float(new_grids[i][0]),
                           float(new_grids[i][1]),
                           float(new_grids[i][2]),
                           float(new_grids[i][3])
                           ]
        } for i in range(len(new_grids))]

        # 传递到前端节点的数据 报错,需要处理成 key:[x,x,x,x]
        return {"ui":{
            "json":[data["width"],data["height"],data_converted]
            },"result": (new_grids,labels,im,)}
    
        # return (new_grids,labels,pil2tensor(image),)

class GridOutput:
    @classmethod
    def INPUT_TYPES(s):
        return { 
            "required": {
                "grid": ("_GRID",),
                
            },
            "optional":{
                  "bg_image":("IMAGE",)
                }
                }
    
    RETURN_TYPES = ("INT","INT","INT","INT","MASK",)
    RETURN_NAMES = ("x","y","width","height","mask",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = False
    # OUTPUT_IS_LIST = (True,)

    def run(self,grid,bg_image=None):
        x,y,w,h=grid
        x=int(x)
        y=int(y)
        w=int(w)
        h=int(h)

        masks=[]
        if bg_image!=None:
            for i in range(len(bg_image)):
                im=bg_image[i]
                #增加输出mask
                im=tensor2pil(im)
                mask=areaToMask(x,y,w,h,im)
                mask=pil2tensor(mask)
                masks.append(mask)
        out=None
        if len(masks)>0:
            out = torch.cat(masks, dim=0)
        return (x,y,w,h,out,)




class ShowLayer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            
            "required": { 
                "edit": ("EDIT",),
               
                "x": ("INT",{
                    "default": 0, 
                    "min": -100, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "y": ("INT",{
                    "default": 0, 
                    "min": 0, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "width": ("INT",{
                    "default": 512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "height": ("INT",{
                    "default": 512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "z_index": ("INT",{
                    "default": 0, 
                    "min":0, #Minimum value
                    "max": 100, #Maximum value
                    "step": 1, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "scale_option": (["width","height",'overall'],),
                # "image": ("IMAGE",),
            },
             "optional":{
                    # "mask": ("MASK",{"default": None}),
                    "layers": ("LAYER",{"default": None}), 
                }
                }
    
    RETURN_TYPES = ( )
    RETURN_NAMES = ( )

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = True
    # OUTPUT_IS_LIST = (True,)

    def run(self,edit,x,y,width,height,z_index,scale_option,layers):
        # print(x,y,width,height,z_index,image,mask)
        
        # if mask==None:
        #     im=tensor2pil(image)
        #     mask=im.convert('L')
        #     mask=pil2tensor(mask)
        # else:
        #     mask=mask[0]

        # layers[edit[0]]={
        #     "x":x[0],
        #     "y":y[0],
        #     "width":width[0],
        #     "height":height[0],
        #     "z_index":z_index[0],
        #     "scale_option":scale_option[0],
        #     "image":image[0],
        #     "mask":mask
        # }

        return ( )


class MergeLayers:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                            "layers": ("LAYER",),
                            "images": ("IMAGE",),
                                            },
            "optional":{
                           
                            "is_multiply_blend":  ("BOOLEAN", {"default": False}),
                            
                    }
                }
    
    RETURN_TYPES = ("IMAGE","MASK",)
    RETURN_NAMES = ("IMAGE","MASK",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = True
    # OUTPUT_IS_LIST = (False,)

    def run(self,layers,images,is_multiply_blend):

        bg_images=[]
        masks=[]
        
        is_multiply_blend=is_multiply_blend[0]
        # print(len(images),images[0].shape)
        # 1  torch.Size([2, 512, 512, 3])
        # 4  torch.Size([1, 1024, 768, 3])

        for img in images:

            for bg_image in img:
                # bg_image=image[0]
                bg_image=tensor2pil(bg_image)
                # 按z-index排序
                layers_new = sorted(layers, key=lambda x: x["z_index"])
                
                width, height = bg_image.size
                final_mask= Image.new('L', (width, height), 0)

                for layer in layers_new:
                    image=layer['image']
                    mask=layer['mask']
                    if 'type' in layer and layer['type']=='base64' and type(image) == str:
                        im=base64_to_image(image)
                        im=im.convert('RGB')
                        image=pil2tensor(im)

                        mask=base64_to_image(mask)
                        mask=mask.convert('L')
                        mask=pil2tensor(mask)
                    
                    
                    layer_image=tensor2pil(image)
                    layer_mask=tensor2pil(mask)
                    # t=layer_image.convert("RGBA")
                    # t.save('test.png') 如果layerimage传入的是rgba，则是透明的
                    bg_image=merge_images(bg_image,
                                        layer_image,
                                        layer_mask,
                                        layer['x'],
                                        layer['y'],
                                        layer['width'],
                                        layer['height'],
                                        layer['scale_option'],
                                        is_multiply_blend
                                        )
                    
                    final_mask=merge_images(final_mask,
                                        layer_mask.convert('RGB'),
                                        layer_mask,
                                        layer['x'],
                                        layer['y'],
                                        layer['width'],
                                        layer['height'],
                                        layer['scale_option']
                                        )
                    
                    final_mask=final_mask.convert('L')
                    
                # mask=bg_image.convert('RGBA')
                final_mask=pil2tensor(final_mask)
                
                bg_image=bg_image.convert('RGB')
                bg_image=pil2tensor(bg_image)

                bg_images.append(bg_image)
                masks.append(final_mask)
        
        bg_images=torch.cat(bg_images, dim=0)
        masks=torch.cat(masks, dim=0)
        return (bg_images,masks,)
    

class GradientImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                "width": ("INT",{
                    "default": 512, 
                    "min": 1, # 最小值
                    "max": 8192, # 最大值
                    "step": 1, # 间隔
                    "display": "number" # 控件类型： 输入框 number、滑块 slider
                }),
                "height": ("INT",{
                    "default": 512, 
                    "min": 1,
                    "max": 8192,
                    "step": 1,
                    "display": "number"
                }),
                "start_color_hex": ("STRING",{"multiline": False,"default": "#FFFFFF","dynamicPrompts": False}),
                "end_color_hex": ("STRING",{"multiline": False,"default": "#000000","dynamicPrompts": False}),
                },
                }
    
    # 输出的数据类型
    RETURN_TYPES = ("IMAGE","MASK",)

    # 运行时方法名称
    FUNCTION = "run"

    # 右键菜单目录
    CATEGORY = "♾️Mixlab/Image"

    # 输入是否为列表
    INPUT_IS_LIST = False

    # 输出是否为列表
    OUTPUT_IS_LIST = (False,False,)

    def run(self,width,height,start_color_hex, end_color_hex):

        im,mask=generate_gradient_image(width, height, start_color_hex, end_color_hex)

        #获取临时目录：temp
        output_dir = folder_paths.get_temp_directory()

        (
            full_output_folder,
            filename,
            counter,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path('tmp_', output_dir)
        
        image_file = f"{filename}_{counter:05}.png"

        image_path=os.path.join(full_output_folder, image_file)
        # 保存图片
        im.save(image_path,compress_level=6)

        # 把PIL数据类型转为tensor
        im=pil2tensor(im)

        mask=pil2tensor(mask)

        # 定义ui字段，数据将回传到web前端的 nodeType.prototype.onExecuted
        # result是节点的输出
        return {"ui":{"images": [{
                "filename": image_file,
                "subfolder": subfolder,
                "type":"temp"
            }]},"result": (im,mask,)}



class NoiseImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                "width": ("INT",{
                    "default": 512, 
                    "min": 1, # 最小值
                    "max": 8192, # 最大值
                    "step": 1, # 间隔
                    "display": "number" # 控件类型： 输入框 number、滑块 slider
                }),
                "height": ("INT",{
                    "default": 512, 
                    "min": 1,
                    "max": 8192,
                    "step": 1,
                    "display": "number"
                }),
                "noise_level": ("INT",{
                    "default": 128, 
                    "min": 0,
                    "max": 8192,
                    "step": 1,
                    "display": "slider"
                }),
                "color_hex": ("STRING",{"multiline": False,"default": "#FFFFFF","dynamicPrompts": False}),
                },
                }
    
    # 输出的数据类型
    RETURN_TYPES = ("IMAGE",)

    # 运行时方法名称
    FUNCTION = "run"

    # 右键菜单目录
    CATEGORY = "♾️Mixlab/Image"

    # 输入是否为列表
    INPUT_IS_LIST = False

    # 输出是否为列表
    OUTPUT_IS_LIST = (False,)

    def run(self,width,height,noise_level,color_hex):
        # 创建噪声图像
        im=create_noisy_image(width,height,"RGB",noise_level,color_hex)
        
        #获取临时目录：temp
        output_dir = folder_paths.get_temp_directory()

        (
            full_output_folder,
            filename,
            counter,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path('tmp_', output_dir)
        
        image_file = f"{filename}_{counter:05}.png"

        image_path=os.path.join(full_output_folder, image_file)
        # 保存图片
        im.save(image_path,compress_level=6)

        # 把PIL数据类型转为tensor
        im=pil2tensor(im)

        # 定义ui字段，数据将回传到web前端的 nodeType.prototype.onExecuted
        # result是节点的输出
        return {"ui":{"images": [{
                "filename": image_file,
                "subfolder": subfolder,
                "type":"temp"
            }]},"result": (im,)}


class ResizeImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "width": ("INT",{
                    "default": 512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 8, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "height": ("INT",{
                    "default": 512, 
                    "min": 1, #Minimum value
                    "max": 8192, #Maximum value
                    "step": 8, #Slider's step
                    "display": "number" # Cosmetic only: display as "number" or "slider"
                }),
                "scale_option": (["width","height",'overall','center'],),

                             },

            "optional":{
                    "image": ("IMAGE",),
                    "average_color": (["on",'off'],),
                    "fill_color":("STRING",{"multiline": False,"default": "#FFFFFF","dynamicPrompts": False}),
                    "mask": ("MASK",),
            }
                }
    
    RETURN_TYPES = ("IMAGE","IMAGE","STRING","MASK",)
    RETURN_NAMES = ("image","average_image","average_hex","mask",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,True,True,)

    def run(self,width,height,scale_option,image=None,average_color=['on'],fill_color=["#FFFFFF"],mask=None):
        
        w=width[0]
        h=height[0]
        scale_option=scale_option[0]
        average_color=average_color[0]
        fill_color=fill_color[0]

        imgs=[]
        masks=[]
        average_images=[]
        hexs=[]

        if image==None:
            im=create_noisy_image(w,h,"RGB")
            a_im,hex=get_average_color_image(im)
            
            im=pil2tensor(im)
            imgs.append(im)

            a_im=pil2tensor(a_im)
            average_images.append(a_im)
            hexs.append(hex)
        else:
            for ims in image:
                for im in ims:
                    im=tensor2pil(im)

                    im=im.convert('RGB')
                    a_im,hex=get_average_color_image(im)

                    if average_color=='on':
                        fill_color=hex
                        
                    im=resize_image(im,scale_option,w,h,fill_color)

                    im=pil2tensor(im)
                    imgs.append(im)

                    a_im=pil2tensor(a_im)
                    average_images.append(a_im)
                    hexs.append(hex)

            try:
                for mas in mask:
                    for ma in mas:
                        ma=tensor2pil(ma)
                        ma=ma.convert('RGB')
                        ma=resize_image(ma,scale_option,w,h,fill_color)
                        ma=ma.convert('L')
                        ma=pil2tensor(ma)
                        masks.append(ma)
            except:
                print('')
        
        return (imgs,average_images,hexs,masks,)


class MirroredImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                "image": ("IMAGE",),
                },
                }
    
    # 输出的数据类型
    RETURN_TYPES = ("IMAGE",)

    # 运行时方法名称
    FUNCTION = "run"

    # 右键菜单目录
    CATEGORY = "♾️Mixlab/Image"

    # 输入是否为列表
    INPUT_IS_LIST = True

    # 输出是否为列表
    OUTPUT_IS_LIST = (True,)

    def run(self,image):
        res=[]
        for ims in image:
            for im in ims:
                img=tensor2pil(im)
                mirrored_image = img.transpose(Image.FLIP_LEFT_RIGHT)
                img=pil2tensor(mirrored_image)
                res.append(img)
        return (res,)



class GetImageSize_:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
             "optional":{
                    "min_width":("INT", {
                        "default": 512, 
                        "min":1, #Minimum value
                        "max": 2048, #Maximum value
                        "step": 8, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    })
                },
        }

    RETURN_TYPES = ("INT", "INT","INT", "INT",)
    RETURN_NAMES = ("width", "height","min_width", "min_height",)

    FUNCTION = "get_size"

    CATEGORY = "♾️Mixlab/Image"

    def get_size(self, image,min_width):
        _, height, width, _ = image.shape
        
        # 如果比min_widht,还小，则输出 min width
        if min_width>width:
            im=tensor2pil(image)
            im=resize_image(im,'width',min_width,min_width,"white")
            im=im.convert('RGB')

            min_width,min_height=im.size

        else:
            min_width=width
            min_height=height

        return (width, height,min_width,min_height,)

class SaveImageAndMetadata:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {"required": 
                    {"images": ("IMAGE", ),
                     "filename_prefix": ("STRING", {"default": "Mixlab"}),
                     "metadata": (["disable","enable"],),
                     },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                }

    RETURN_TYPES = ()
    FUNCTION = "save_images"

    OUTPUT_NODE = True

    CATEGORY = "♾️Mixlab/Output"

    def save_images(self, images, filename_prefix="Mixlab",metadata="disable", prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if (not args.disable_metadata) and (metadata=="enable"):
                print('##enable_metadata')
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            file = f"{filename}_{counter:05}_.png"
            img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return { "ui": { "images": results } }

class ImageColorTransfer:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                "source": ("IMAGE",),
                "target": ("IMAGE",),
                "weight": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                },
                }
    
    # 输出的数据类型
    RETURN_TYPES = ("IMAGE",)

    # 运行时方法名称
    FUNCTION = "run"

    # 右键菜单目录
    CATEGORY = "♾️Mixlab/Color"

    # 输入是否为列表
    # INPUT_IS_LIST = True

    # 输出是否为列表
    # OUTPUT_IS_LIST = (True,)

    def run(self,source,target,weight):

        res=[]

        #batch-list
        source_list = [source[i:i + 1, ...] for i in range(source.shape[0])]
        target_list = [target[i:i + 1, ...] for i in range(target.shape[0])]

        # 长度纠正为相等
        if len(target_list) != len(source_list):
            target_list = target_list * (len(source_list) // len(target_list)) + target_list[:len(source_list) % len(target_list)]
        
        for i in range(len(source_list)):
            target=target_list[i]
            source=source_list[i]
            target=tensor2pil(target)

            image=tensor2pil(source)

            image_res=color_transfer(image,target)

            # weight Blend image # contributors:@ning
            blend_mask = Image.new(mode="L", size=image.size,
                                    color=(round(weight * 255)))
            blend_mask = ImageOps.invert(blend_mask)
            img_result = Image.composite(image, image_res, blend_mask)
            del image, image_res, blend_mask
            
            img_result=pil2tensor(img_result)

            res.append(img_result)

        # list - batch
        res=torch.cat(res, dim=0)

        return (res,)



class SaveImageToLocal:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {"required": 
                    {"images": ("IMAGE", ),
                     "file_path": ("STRING",{"multiline": True,"default": "","dynamicPrompts": False}),
                     },
                "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
                
                }

    RETURN_TYPES = ()
    FUNCTION = "save_images"

    OUTPUT_NODE = True

    CATEGORY = "♾️Mixlab/Output"

    def save_images(self, images,file_path , prompt=None, extra_pnginfo=None):
        filename_prefix = os.path.basename(file_path)
        if file_path=='':
            filename_prefix="ComfyUI"
        
        filename_prefix, _ = os.path.splitext(filename_prefix)

        _, extension = os.path.splitext(file_path)

        if extension:
            # 是文件名，需要处理
            file_path=os.path.dirname(file_path)
            # filename_prefix=

            
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        
    
        if not os.path.exists(file_path):
            # 使用os.makedirs函数创建新目录
            os.makedirs(file_path)
            print("目录已创建")
        else:
            print("目录已存在")

        # 使用glob模块获取当前目录下的所有文件
        if file_path=="":
            files = glob.glob(full_output_folder + '/*')
        else:
            files = glob.glob(file_path + '/*')
        # 统计文件数量
        file_count = len(files)
        counter+=file_count
        print('统计文件数量',file_count,counter)

        results = list()
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            file = f"{filename}_{counter:05}_.png"
            
            if file_path=="":
                fp=os.path.join(full_output_folder, file)
                if os.path.exists(fp):
                    file = f"{filename}_{counter:05}_{generate_random_string(8)}.png"
                    fp=os.path.join(full_output_folder, file)
                img.save(fp, pnginfo=metadata, compress_level=self.compress_level)
                results.append({
                    "filename": file,
                    "subfolder": subfolder,
                    "type": self.type
                })
            
            else:

                fp=os.path.join(file_path, file)
                if os.path.exists(fp):
                    file = f"{filename}_{counter:05}_{generate_random_string(8)}.png"
                    fp=os.path.join(file_path, file)

                img.save(os.path.join(file_path, file), pnginfo=metadata, compress_level=self.compress_level)
                results.append({
                    "filename": file,
                    "subfolder": file_path,
                    "type": self.type
                })
            counter += 1

        return ()
