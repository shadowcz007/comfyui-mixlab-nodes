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
from comfy.cli_args import args
import cv2 
import math
from .Watcher import FolderWatcher


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
                try:
                    imgs=load_image(file_path,white_bg)
                    for img in imgs:
                        images.append({
                            "image":img['image'],
                            "mask":img['mask'],
                            "file_path":file_path,
                            "psd":len(imgs)>1
                        })
                except:
                    print('非图片',file_path)
 
    elif os.path.isfile(f):
        try:
            imgs=load_image(f,white_bg)
            for img in imgs:
                images.append({
                    "image":img['image'],
                    "mask":img['mask'],
                    "file_path":file_path,
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
    mask = Image.new('1', image.size)

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

def merge_images(bg_image, layer_image, mask, x, y, width, height, scale_option):
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

    # 调整mask的大小
    nw, nh = layer_image.size
    mask = mask.resize((nw, nh))

    # 在底图上粘贴图层
    bg_image.paste(layer_image, (x, y), mask=mask)

    # 输出合成后的图片
    return bg_image


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
        return resized_image
    
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
    
    RETURN_TYPES = ('IMAGE','MASK','STRING',)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    # INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,False,)
  
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

        for im in sorted_files:
            imgs.append(im['image'])
            masks.append(im['mask'])
        
        # print('index_variable',index_variable)
        
        try:
            if index_variable!=-1:
                imgs=[imgs[index_variable]] if index_variable < len(imgs) else None
                masks=[masks[index_variable]] if index_variable < len(masks) else None
        except Exception as e:
            print("发生了一个未知的错误：", str(e))

        # print('#prompt::::',prompt)
        return  {"ui": {"seed": [1]}, "result":(imgs,masks,prompt,)}


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
        im=naive_cutout(im,im)
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


        # 原图的mask
        ori=RGBA[:,y:to_y, x:to_x, :]
        ori=tensor2pil(ori)

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
                    new_pixel_data[x, y] = (r, g, b, a)

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
                }
    
    RETURN_TYPES = ("IMAGE","MASK",)
    RETURN_NAMES = ("images","masks",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (True,True,)


    global urls_image
    urls_image={}

    def run(self,url):
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

    CATEGORY = "♾️Mixlab/Image"

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
                "image": ("IMAGE",),
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

                }
    
    RETURN_TYPES = ("IMAGE","MASK",)
    RETURN_NAMES = ("IMAGE","MASK",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Layer"

    INPUT_IS_LIST = True
    # OUTPUT_IS_LIST = (False,)

    def run(self,layers,images):

        bg_images=[]
        masks=[]
 
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
                    bg_image=merge_images(bg_image,
                                        layer_image,
                                        layer_mask,
                                        layer['x'],
                                        layer['y'],
                                        layer['width'],
                                        layer['height'],
                                        layer['scale_option']
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
                "scale_option": (["width","height",'overall','center'],),

                             },

            "optional":{
                    "image": ("IMAGE",),
                    "average_color": (["on",'off'],),
                    "fill_color":("STRING",{"multiline": False,"default": "#FFFFFF","dynamicPrompts": False}),
            }
                }
    
    RETURN_TYPES = ("IMAGE","IMAGE","STRING",)
    RETURN_NAMES = ("image","average_image","average_hex",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Image"

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,True,)

    def run(self,width,height,scale_option,image=None,average_color=['on'],fill_color=["#FFFFFF"]):
        
        w=width[0]
        h=height[0]
        scale_option=scale_option[0]
        average_color=average_color[0]
        fill_color=fill_color[0]

        imgs=[]
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
                    im=resize_image(im,scale_option,w,h,fill_color)
                    im=im.convert('RGB')

                    a_im,hex=get_average_color_image(im)

                    im=pil2tensor(im)
                    imgs.append(im)

                    a_im=pil2tensor(a_im)
                    average_images.append(a_im)
                    hexs.append(hex)
        
        return (imgs,average_images,hexs,)


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
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")

    FUNCTION = "get_size"

    CATEGORY = "♾️Mixlab/Image"

    def get_size(self, image):
        _, height, width, _ = image.shape
        return (width, height)



class ImageColorTransfer:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                "source": ("IMAGE",),
                "target": ("IMAGE",),
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

    def run(self,source,target):

        res=[]

        target=target[0][0]
        print(target.shape)
        target=tensor2pil(target)

        for ims in source:
            for im in ims:
                image=tensor2pil(im)
                image=color_transfer(image,target)
                image=pil2tensor(image)
                res.append(image)

        return (res,)


