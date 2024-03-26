import os
import hashlib
import json
import subprocess
import shutil
import re
import time,math
import numpy as np
from typing import List
import torch
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
import cv2
from pathlib import Path

import folder_paths
from comfy.k_diffusion.utils import FolderOfImages
from comfy.utils import common_upscale


folder_paths.folder_names_and_paths["video_formats"] = (
    [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "video_formats"),
    ],
    [".json"]
)

ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path is None:
    print("ffmpeg could not be found. Using ffmpeg from imageio-ffmpeg.")
    from imageio_ffmpeg import get_ffmpeg_exe
    try:
        ffmpeg_path = get_ffmpeg_exe()
    except:
        print("ffmpeg could not be found. Outputs that require it have been disabled")

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def count_files(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count

def create_temp_file(image):
    output_dir = folder_paths.get_temp_directory()

    c=count_files(output_dir)

    (
            full_output_folder,
            filename,
            counter,
            subfolder,
            _,
        ) = folder_paths.get_save_image_path('temp_', output_dir)

    
    image=tensor2pil(image)
 
    image_file = f"{filename}_{c}_{counter:05}.png"
     
    image_path=os.path.join(full_output_folder, image_file)

    image.save(image_path,compress_level=4)

    return [{
                "filename": image_file,
                "subfolder": subfolder,
                "type": "temp"
                }]


def split_list(lst, chunk_size, transition_size):
    result = []
    for i in range(0, len(lst), chunk_size):
        start = i - transition_size
        end = i + chunk_size + transition_size
        result.append(lst[max(start, 0):end])
    return result

# images = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
# chunk_size = 3
# transition_size = 1

# result = split_list(images, chunk_size, transition_size)
# print(result)

class ImageListReplace:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "images": ("IMAGE",),
            "start_index":("INT", {"default": 0, "min": 0, "step": 1}),
            "end_index":("INT", {"default": 0, "min": 0, "step": 1}),
            "invert": ("BOOLEAN", {"default": False}),
        },
         "optional":{
                    "image_replace": ("IMAGE",),
                    "images_replace": ("IMAGE",),
                    
                    }
        }

    RETURN_TYPES = ("IMAGE","IMAGE",)
    RETURN_NAMES = ("images","select_images",)
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Video"

    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,)

    def run(self, images,start_index=[0],end_index=[0],invert=[False],image_replace=None,images_replace=None):
        start_index=start_index[0]
        end_index=end_index[0]
        invert=invert[0]

        image_rs=[]

        if image_replace!=None:
            for i in range(end_index-start_index+1):
                image_rs.append(image_replace[0])

        if images_replace!=None:
            image_rs=images_replace

        # 如果image replace 为空
        if image_replace==None and images_replace==None:
            # print('如果image replace 为空',images[0])
            # [[tensor(
            # tensor([[[[0.
            first_image=tensor2pil(images[0][0])
            width, height = first_image.size
            image_replace=Image.new("RGB", (width, height), (0, 0, 0))
            image_replace=pil2tensor(image_replace)
            for i in range(end_index-start_index+1):
                image_rs.append(image_replace)

        
        new_images=[]
        select_images=[]
        k=0
        for i in range(len(images)):
            if i>=start_index and i<=end_index:
                if invert:
                    new_images.append(images[i])
                else:
                    new_images.append(image_rs[k])
                    select_images.append(images[i])
                    k+=1
            else:
                if invert:
                    new_images.append(image_rs[k])
                    select_images.append(images[i])
                    k+=1
                else:
                    new_images.append(images[i])

        imss=[]
        # print(len(images))
        for i in range(len(images)):
            t=images[i][0]
            t=tensor2pil(t)
            t = t.convert("RGB")
            original_width, original_height = t.size
            scale = 300 / original_width
            new_height = int(original_height * scale)
            t = t.resize((300, new_height))

            ims=create_temp_file(pil2tensor(t))
            imss.append(ims[0])

        # image_replace=create_temp_file(image_replace)

        return {"ui":{"_images": imss},"result": (new_images,select_images,)}


class LoadVideoAndSegment:
    @classmethod
    def INPUT_TYPES(s):
        video_extensions = ['webm', 'mp4', 'mkv', 'gif']
        input_dir = folder_paths.get_input_directory()
        files = []
        for f in os.listdir(input_dir):
            if os.path.isfile(os.path.join(input_dir, f)):
                file_parts = f.split('.')
                if len(file_parts) > 1 and (file_parts[-1] in video_extensions):
                    files.append(f)
        return {"required": {
                    "video": (sorted(files), {"video_upload": True}),
                     "video_segment_frames": ("INT", {"default": 10, "min": 1, "step": 1}),
                     "transition_frames": ("INT", {"default": 0, "min": 0, "step": 1}), 
                     },}

    CATEGORY = "♾️Mixlab/Video"

    RETURN_TYPES = ("IMAGE","IMAGE", "INT",)
    RETURN_NAMES = ("segment_batch","frame_count","segment_count",)
    FUNCTION = "load_video"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,False,False,)


    def is_gif(self, filename):
        file_parts = filename.split('.')
        return len(file_parts) > 1 and file_parts[-1] == "gif"

    def load_video_cv_fallback(self, video, frame_load_cap, skip_first_frames):
        try:
            video_cap = cv2.VideoCapture(folder_paths.get_annotated_filepath(video))
            if not video_cap.isOpened():
                raise ValueError(f"{video} could not be loaded with cv fallback.")
            # set video_cap to look at start_index frame
            images = []
            total_frame_count = 0
            frames_added = 0
            base_frame_time = 1/video_cap.get(cv2.CAP_PROP_FPS)
            
            target_frame_time = base_frame_time

            time_offset=0.0
            while video_cap.isOpened():
                if time_offset < target_frame_time:
                    is_returned, frame = video_cap.read()
                    # if didn't return frame, video has ended
                    if not is_returned:
                        break
                    time_offset += base_frame_time
                if time_offset < target_frame_time:
                    continue
                time_offset -= target_frame_time
                # if not at start_index, skip doing anything with frame
                total_frame_count += 1
                if total_frame_count <= skip_first_frames:
                    continue
                # TODO: do whatever operations need to happen, like force_size, etc

                # opencv loads images in BGR format (yuck), so need to convert to RGB for ComfyUI use
                # follow up: can videos ever have an alpha channel?
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # convert frame to comfyui's expected format (taken from comfy's load image code)
                image = Image.fromarray(frame)
                image = ImageOps.exif_transpose(image)
                image = np.array(image, dtype=np.float32) / 255.0
                image = torch.from_numpy(image)[None,]
                images.append(image)
                frames_added += 1
                # if cap exists and we've reached it, stop processing frames
                if frame_load_cap > 0 and frames_added >= frame_load_cap:
                    break
        finally:
            video_cap.release()
        images = torch.cat(images, dim=0)
       
        return (images, frames_added)

    def load_video(self, video,video_segment_frames,transition_frames ):
        frame_load_cap=0
        skip_first_frames=0

        video_path = folder_paths.get_annotated_filepath(video)
        
        # check if video is a gif - will need to use cv fallback to read frames
        # use cv fallback if ffmpeg not installed or gif
        if ffmpeg_path is None:
            return self.load_video_cv_fallback(video, frame_load_cap, skip_first_frames)
        # otherwise, continue with ffmpeg
        
        args_dummy = [ffmpeg_path, "-i", video_path, "-f", "null", "-"]
        try:
            with subprocess.Popen(args_dummy, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as proc:
                for line in proc.stderr.readlines():
                    match = re.search(", ([1-9]|\\d{2,})x(\\d+)",line.decode('utf-8'))
                    if match is not None:
                        size = [int(match.group(1)), int(match.group(2))]
                        break
        except Exception as e:
            print(f"Retrying with opencv due to ffmpeg error: {e}")
            return self.load_video_cv_fallback(video, frame_load_cap, skip_first_frames)
        args_all_frames = [ffmpeg_path, "-i", video_path, "-v", "error",
                             "-pix_fmt", "rgb24"]

        vfilters = []
       
        if skip_first_frames > 0:
            vfilters.append(f"select=gt(n\\,{skip_first_frames-1})")
        if frame_load_cap > 0:
            vfilters.append(f"select=gt({frame_load_cap}\\,n)")
        #manually calculate aspect ratio to ensure reads remain aligned
        
        if len(vfilters) > 0:
            args_all_frames += ["-vf", ",".join(vfilters)]

        args_all_frames += ["-f", "rawvideo", "-"]
        images = []
        try:
            with subprocess.Popen(args_all_frames, stdout=subprocess.PIPE) as proc:
                #Manually buffer enough bytes for an image
                bpi = size[0]*size[1]*3
                current_bytes = bytearray(bpi)
                current_offset=0
                while True:
                    bytes_read = proc.stdout.read(bpi - current_offset)
                    if bytes_read is None:#sleep to wait for more data
                        time.sleep(.2)
                        continue
                    if len(bytes_read) == 0:#EOF
                        break
                    current_bytes[current_offset:len(bytes_read)] = bytes_read
                    current_offset+=len(bytes_read)
                    if current_offset == bpi:
                        images.append(np.array(current_bytes, dtype=np.float32).reshape(size[1], size[0], 3) / 255.0)
                        current_offset = 0
        except Exception as e:
            print(f"Retrying with opencv due to ffmpeg error: {e}")
            return self.load_video_cv_fallback(video, frame_load_cap, skip_first_frames)

        imgs=split_list(images,video_segment_frames,transition_frames)

        imgs=[torch.from_numpy(np.stack(im)) for im in imgs]

        # images = torch.from_numpy(np.stack(images))

        return (imgs, len(images),len(imgs),)

    @classmethod
    def IS_CHANGED(s, video, **kwargs):
        image_path = folder_paths.get_annotated_filepath(video)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, video, **kwargs):
        if not folder_paths.exists_annotated_filepath(video):
            return "Invalid image file: {}".format(video)

        return True
    




class VAEEncodeForInpaint_Frames:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
            "vae": ("VAE", ), 
            "images": ("IMAGE", ), 
            "masks": ("MASK", ), 
            "grow_mask_by": ("INT", {"default": 6, "min": 0, "max": 64, "step": 1}),
            }}
    
    FUNCTION = "encode"


    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("LATENT",)
 
    CATEGORY = "♾️Mixlab/Video"

    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)


    def encode(self, vae, images, masks, grow_mask_by=[6]):
        vae=vae[0]
        grow_mask_by=grow_mask_by[0]

        result=[]

        for i in range(len(images)):
            pixels=images[i]
            mask=masks[i]


            x = (pixels.shape[1] // 8) * 8
            y = (pixels.shape[2] // 8) * 8
            mask = torch.nn.functional.interpolate(mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1])), size=(pixels.shape[1], pixels.shape[2]), mode="bilinear")

            pixels = pixels.clone()
            if pixels.shape[1] != x or pixels.shape[2] != y:
                x_offset = (pixels.shape[1] % 8) // 2
                y_offset = (pixels.shape[2] % 8) // 2
                pixels = pixels[:,x_offset:x + x_offset, y_offset:y + y_offset,:]
                mask = mask[:,:,x_offset:x + x_offset, y_offset:y + y_offset]

            #grow mask by a few pixels to keep things seamless in latent space
            if grow_mask_by == 0:
                mask_erosion = mask
            else:
                kernel_tensor = torch.ones((1, 1, grow_mask_by, grow_mask_by))
                padding = math.ceil((grow_mask_by - 1) / 2)

                mask_erosion = torch.clamp(torch.nn.functional.conv2d(mask.round(), kernel_tensor, padding=padding), 0, 1)

            m = (1.0 - mask.round()).squeeze(1)
            for i in range(3):
                pixels[:,:,:,i] -= 0.5
                pixels[:,:,:,i] *= m
                pixels[:,:,:,i] += 0.5
            t = vae.encode(pixels)

            result.append({"samples":t, "noise_mask": (mask_erosion[:,:,:x,:y].round())})


        return (result, )