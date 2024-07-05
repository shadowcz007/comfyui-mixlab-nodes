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
import cv2,random,string
from pathlib import Path

import folder_paths
from comfy.k_diffusion.utils import FolderOfImages
from comfy.utils import common_upscale

import torchaudio
import base64

import mimetypes



def get_frames(frame_count, frames, revert=False):
    if not revert:
        if frame_count <= len(frames):
            return frames[:frame_count]
        else:
            return [frames[i % len(frames)] for i in range(frame_count)]
    else:
        extended_frames = frames + frames[-2:0:-1]  # 正向加反向中间部分
        if frame_count <= len(extended_frames):
            return extended_frames[:frame_count]
        else:
            return [extended_frames[i % len(extended_frames)] for i in range(frame_count)]

# # 示例用法
# frames = ["frame1", "frame2", "frame3"]
# frame_count = 2

# result = get_frames(frame_count, frames, revert=False)
# print(result)  # 输出: ['frame1', 'frame2', 'frame3', 'frame1', 'frame2', 'frame3', 'frame1']

# result = get_frames(frame_count, frames, revert=True)
# print(result)  # 输出: ['frame1', 'frame2', 'frame3', 'frame2', 'frame1', 'frame2', 'frame3']




def get_mime_type(file_path):
    # 获取文件的 MIME 类型
    mime_type, _ = mimetypes.guess_type(file_path)
    
    # 如果无法猜测类型，返回默认类型
    if mime_type is None:
        return 'application/octet-stream'
    
    return mime_type
# import subprocess
# from imageio_ffmpeg import get_ffmpeg_exe


def save_audio_base64s_to_file(base64_audios, output_folder, file_name):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    decoded_audios=[]
    for a in base64_audios:
    
        # If the base64 string contains a header, remove it
        if ',' in a:
            a = a.split(',')[1]
        
        # 解码 base64 数据
        a=base64.b64decode(a)
        decoded_audios.append(a)

    # 拼接音频数据
    combined_audio = b''.join(decoded_audios)
    
    # Create the full file path
    file_path = os.path.join(output_folder, file_name)
    
    # Write the decoded audio to the file
    with open(file_path, 'wb') as audio_file:
        audio_file.write(combined_audio)
    
    return file_path

# Example usage
# base64_audio = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAIlYAAESsAAACABAAZGF0YQAAAAA="
# output_folder = "audio_files"
# file_name = "output.wav"

# file_path = save_audio_base64_to_file(base64_audio, output_folder, file_name)
# print(f"Audio saved to: {file_path}")

# 写一个python文件，用来 判断文件夹内命名为 所有chat_tts开头的文件数量（chat_tts_00001），并输出新的编号
def get_new_counter(full_output_folder, filename_prefix):
    # 获取目录中的所有文件
    files = os.listdir(full_output_folder)
    
    # 过滤出以 filename_prefix 开头并且后续部分为数字的文件
    filtered_files = []
    for f in files:
        if f.startswith(filename_prefix):
            # 去掉文件名中的前缀和后缀，只保留中间的数字部分
            base_name = f[len(filename_prefix)+1:]
            number_part = base_name.split('.')[0]  # 假设文件名中只有一个点，即扩展名
            if number_part.isdigit():
                filtered_files.append(int(number_part))

    if not filtered_files:
        return 1

    # 获取最大的编号
    max_number = max(filtered_files)
    
    # 新的编号
    return max_number + 1

def crop_audio(input_file, start_time, duration):
    # Load the audio file
    audio_tensor, sample_rate = torchaudio.load(input_file)
    
    # Convert start_time and duration from seconds to sample indices
    start_sample = int(start_time * sample_rate)
    end_sample = start_sample + int(duration * sample_rate)
    
    # Perform the slicing
    cropped_audio_tensor = audio_tensor[:, start_sample:end_sample]
    
    # Save the cropped audio to a new file
    torchaudio.save(input_file, cropped_audio_tensor, sample_rate)
    
    return input_file

def generate_folder_name(directory,video_path):
    # Get the directory and filename from the video path
    _, filename = os.path.split(video_path)
    # Generate a random string of lowercase letters and digits
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    # Create the folder name by combining the random string and the filename
    folder_name = random_string + '_' + filename
    # Create the full folder path by joining the directory and the folder name
    folder_path = os.path.join(directory, folder_name)
    return folder_path

def create_folder(directory,video_path):
    folder_path = generate_folder_name(directory,video_path)
    os.makedirs(folder_path)
    return folder_path


def split_video(video_path, video_segment_frames, transition_frames, output_dir):
    # 读取视频文件
    video_capture = cv2.VideoCapture(video_path)
    
    # 获取视频的总帧数和帧率
    total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video_capture.get(cv2.CAP_PROP_FPS)
    
    # 计算每个视频片段的总帧数，包括过渡帧
    segment_total_frames = video_segment_frames + transition_frames
    
    # 计算可以分割的片段数量，向上取整
    num_segments = (total_frames + transition_frames - 1) // segment_total_frames
    
    vs=[]
    # 计算每个片段的起始帧和结束帧
    start_frame = 0
    for i in range(num_segments):
        # 计算当前片段的结束帧，注意最后一个片段可能没有过渡帧
        end_frame = min(start_frame + segment_total_frames, total_frames)
        
        # 打印当前片段的起始帧和结束帧
        print(f"Segment {i+1}: Start Frame {start_frame}, End Frame {end_frame}")

        if end_frame<start_frame:
            break
        
        # 保存当前片段为一个视频文件
        segment_video_path = f"{output_dir}/segment_{i+1}.avi"

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        segment_video = cv2.VideoWriter(segment_video_path, fourcc, fps, (int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                                              int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        

        for frame_num in range(start_frame, end_frame):
            ret, frame = video_capture.read()
            if ret:
                segment_video.write(frame)
            else:
                break  # 如果读取失败，则退出循环
        
        # 更新起始帧为下一个片段的起始位置
        start_frame = end_frame + transition_frames
        vs.append(segment_video_path)
    
    # 释放视频捕获对象
    video_capture.release()
    # print(vs)
    return (vs,total_frames,fps)


folder_paths.folder_names_and_paths["video_formats"] = (
    [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".", "video_formats"),
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


def combine_audio_video(audio_path, video_path, output_path):
   
    command = [
        ffmpeg_path,
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
    
    subprocess.run(command, check=True)
    return output_path




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

# The code is based on ComfyUI-VideoHelperSuite modification.
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
                     "video_segment_frames": ("INT", {"default": 10, "min": -1, "step": 1}),
                     "transition_frames": ("INT", {"default": 0, "min": 0, "step": 1}), 
                     },}

    CATEGORY = "♾️Mixlab/Video"

    RETURN_TYPES = ("SCENE_VIDEO","INT", "INT","INT",)
    RETURN_NAMES = ("scenes_video","scenes_count","frame_count","fps",)
    FUNCTION = "load_video"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,False,False,False,)


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
        
        video_path = folder_paths.get_annotated_filepath(video)
        
        # temp path 
        tp=folder_paths.get_temp_directory()
        basename = os.path.basename(video_path)  # 获取文件名
        name_without_extension = os.path.splitext(basename)[0]  # 去掉文件后缀

        folder_path = create_folder(tp,name_without_extension)
        
        if video_segment_frames==-1:
            # 不切割视频
            scenes_video=[video_path]
            # 读取视频文件
            video_capture = cv2.VideoCapture(video_path)
            
            # 获取视频的总帧数和帧率
            total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = video_capture.get(cv2.CAP_PROP_FPS)

        else:
            # 导出的数据
            scenes_video,total_frames,fps=split_video(video_path,video_segment_frames,
                                    transition_frames,folder_path)
      


        return (scenes_video,len(scenes_video), total_frames,fps,)

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



class LoadAndCombinedAudio_:
    @classmethod
    def INPUT_TYPES(s):
       
        return {"required": {
                    "audios": ("AUDIOBASE64",),
                    "start_time": ("FLOAT" , {"default": 0, "min": 0, "max": 10000000, "step": 0.01}),
                    "duration": ("FLOAT" , {"default": 10, "min": -1, "max": 10000000, "step": 0.01}),
                     },
                }

    CATEGORY = "♾️Mixlab/Audio"

    RETURN_TYPES = ("STRING","AUDIO",)
    RETURN_NAMES = ("audio_file_path","audio",)
    FUNCTION = "run"

    def run(self,audios, start_time, duration):
        output_dir = folder_paths.get_output_directory()
        counter=get_new_counter(output_dir,'audio_')

        audio_file_name = f"audio_{counter:05}.wav"

        audio_file=save_audio_base64s_to_file(audios['base64'],output_dir,audio_file_name)
        # duration == -1 则不裁切
        if duration > -1:
            crop_audio(audio_file, start_time, duration)

        return (audio_file, {
                "filename": audio_file_name,
                "subfolder": "",
                "type": "output",
                "audio_path":audio_file
                } ,)

class CombineAudioVideo:
    @classmethod
    def INPUT_TYPES(s):
       
        return {"required": {
                     "video_file_path": ("STRING",  {"forceInput": True}),
                     "audio_file_path": ("STRING",  {"forceInput": True}), 
                     },
                }

    CATEGORY = "♾️Mixlab/Video"

    OUTPUT_NODE = True
    FUNCTION = "run" 
    RETURN_TYPES = ()
    RETURN_NAMES = ()

    def run(self,video_file_path, audio_file_path):

        output_dir = folder_paths.get_output_directory()

        counter=get_new_counter(output_dir,'video_final_')
        
        # 获取文件名和扩展名
        base, ext = os.path.splitext(video_file_path)

        v_file = f"video_final_{counter:05}{ext}"
        
        v_file_path=os.path.join(output_dir, v_file)

        combine_audio_video(audio_file_path,video_file_path,v_file_path)

        previews = [
            {
                "filename": v_file,
                "subfolder": "",
                "type": "output",
                "format": get_mime_type(v_file),
            }
        ]
        return {"ui": {"gifs": previews}}

# The code is based on ComfyUI-VideoHelperSuite modification.
class VideoCombine_Adv:
    @classmethod
    def INPUT_TYPES(s):
        #Hide ffmpeg formats if ffmpeg isn't available
        if ffmpeg_path is not None:
            ffmpeg_formats = ["video/"+x[:-5] for x in folder_paths.get_filename_list("video_formats")]
        else:
            ffmpeg_formats = []
        # ffmpeg_formats =["video/"+x for x in  ['webm', 'mp4', 'mkv']]
        return {
            "required": {
                "image_batch": ("IMAGE",),
                "frame_rate": (
                    "INT",
                    {"default": 8, "min": 1, "step": 1},
                ),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "Comfyui"}),
                "format": (["image/gif", "image/webp"] + ffmpeg_formats,),
                "pingpong": ("BOOLEAN", {"default": False}),
                "save_image": ("BOOLEAN", {"default": True}),
                "metadata": ("BOOLEAN", {"default": False}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("SCENE_VIDEO",)
    RETURN_NAMES = ("scenes_video",)
    OUTPUT_NODE = True
    CATEGORY = "♾️Mixlab/Video"
    FUNCTION = "run"

    def save_with_tempfile(self, args, metadata, file_path, frames, env):
        #Ensure temp directory exists
        os.makedirs(folder_paths.get_temp_directory(), exist_ok=True)

        metadata_path = os.path.join(folder_paths.get_temp_directory(), "metadata.txt")
        #metadata from file should  escape = ; # \ and newline
        #From my testing, though, only backslashes need escapes and = in particular causes problems
        #It is likely better to prioritize future compatibility with containers that don't support
        #or shouldn't use the comment tag for embedding metadata
        metadata = metadata.replace("\\","\\\\")
        metadata = metadata.replace(";","\\;")
        metadata = metadata.replace("#","\\#")
        #metadata = metadata.replace("=","\\=")
        metadata = metadata.replace("\n","\\\n")
        with open(metadata_path, "w") as f:
            f.write(";FFMETADATA1\n")
            f.write(metadata)
        args = args[:1] + ["-i", metadata_path] + args[1:] + [file_path]
        with subprocess.Popen(args, stdin=subprocess.PIPE, env=env) as proc:
            for frame in frames:
                proc.stdin.write(frame.tobytes())

    def run(
        self,
        image_batch,
        frame_rate: int,
        loop_count: int,
        filename_prefix="AnimateDiff",
        format="image/gif",
        pingpong=False,
        save_image=True,
        metadata=False,
        prompt=None,
        extra_pnginfo=None,
    ):
        images=image_batch

        frames: List[Image.Image] = []
        for image in images:
            img = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
            # resize 保证
            # 检查图像的高度是否是2的倍数，如果不是，则调整高度
            if img.height % 2 != 0:
                img = img.resize((img.width, img.height + 1))

            # 检查图像的宽度是否是2的倍数，如果不是，则调整宽度
            if img.width % 2 != 0:
                img = img.resize((img.width + 1, img.height))
                
            frames.append(img)

        # get output information
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

        metadata = PngInfo()
        video_metadata = {}
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
            video_metadata["prompt"] = prompt
        if extra_pnginfo is not None:
            for x in extra_pnginfo:
                metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                video_metadata[x] = extra_pnginfo[x]

        # 取消保存metadata
        if metadata==False:
            metadata = PngInfo()

        # save first frame as png to keep metadata
        file = f"{filename}_{counter:05}_.png"
        file_path = os.path.join(full_output_folder, file)
        frames[0].save(
            file_path,
            pnginfo=metadata,
            compress_level=4,
        )
        if pingpong:
            frames = frames + frames[-2:0:-1]

        format_type, format_ext = format.split("/")
        file = f"{filename}_{counter:05}_.{format_ext}"
        file_path = os.path.join(full_output_folder, file)
        if format_type == "image":
            # Use pillow directly to save an animated image
            frames[0].save(
                file_path,
                format=format_ext.upper(),
                save_all=True,
                append_images=frames[1:],
                duration=round(1000 / frame_rate),
                loop=loop_count,
                compress_level=4,
            )
        else:
            # Use ffmpeg to save a video
            if ffmpeg_path is None:
                #Should never be reachable
                raise ProcessLookupError("Could not find ffmpeg")

            video_format_path = folder_paths.get_full_path("video_formats", format_ext + ".json")
            with open(video_format_path, 'r') as stream:
                video_format = json.load(stream)
            file = f"{filename}_{counter:05}_.{video_format['extension']}"
            file_path = os.path.join(full_output_folder, file)
            dimensions = f"{frames[0].width}x{frames[0].height}"
            metadata_args = ["-metadata", "comment=" + json.dumps(video_metadata)]
            args = [ffmpeg_path, "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                    "-s", dimensions, "-r", str(frame_rate), "-i", "-"] \
                    + video_format['main_pass']
            # On linux, max arg length is Pagesize * 32 -> 131072
            # On windows, this around 32767 but seems to vary wildly by > 500
            # in a manor not solely related to other arguments
            if os.name == 'posix':
                max_arg_length = 4096*32
            else:
                max_arg_length = 32767 - len(" ".join(args + [metadata_args[0]] + [file_path])) - 1
            #test max limit
            #metadata_args[1] = metadata_args[1] + "a"*(max_arg_length - len(metadata_args[1])-1)

            env=os.environ.copy()
            if  "environment" in video_format:
                env.update(video_format["environment"])
            if len(metadata_args[1]) >= max_arg_length:
                print(f"Using fallback file for extremely long metadata: {len(metadata_args[1])}/{max_arg_length}")
                self.save_with_tempfile(args, metadata_args[1], file_path, frames, env)
            else:
                try:
                    with subprocess.Popen(args + metadata_args + [file_path],
                                          stdin=subprocess.PIPE, env=env) as proc:
                        for frame in frames:
                            proc.stdin.write(frame.tobytes())
                except FileNotFoundError as e:
                    if "winerror" in dir(e) and e.winerror == 206:
                        print("Metadata was too long. Retrying with fallback file")
                        self.save_with_tempfile(args, metadata_args[1], file_path, frames, env)
                    else:
                        raise
                except OSError as e:
                    if "errno" in dir(e) and e.errno == 7:
                        print("Metadata was too long. Retrying with fallback file")
                        self.save_with_tempfile(args, metadata_args[1], file_path, frames, env)
                    else:
                        raise

        previews = [
            {
                "filename": file,
                "subfolder": subfolder,
                "type": "output" if save_image else "temp",
                "format": format,
            }
        ]
        return {"ui": {"gifs": previews},"result":(file_path,)}


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
    


class GenerateFramesByCount:
    @classmethod
    def INPUT_TYPES(cls):
        
        return {"required": {
                    "frames": ('IMAGE',),
                    "frame_count": ("INT", {"default": 72, "min": 1, "step": 1}), 
                    "revert" :("BOOLEAN", {"default": True},),
                     },}

    RETURN_TYPES = ('IMAGE',)
    RETURN_NAMES = ("frames",)

    FUNCTION = "r"
    CATEGORY = "♾️Mixlab/Video"
    # INPUT_IS_LIST = True

    def r(self, frames, frame_count, revert):
        
        image_list = [frames[i:i + 1, ...] for i in range(frames.shape[0])]

        image_list=get_frames(frame_count,image_list,revert)

        images = torch.cat(image_list, dim=0)

        return (images,)


class scenesNode_:
    @classmethod
    def INPUT_TYPES(cls):
        
        return {"required": {
                    "scenes_video": ('SCENE_VIDEO',),
                    "index": ("INT", {"default": 0, "min": 0, "step": 1}),
                     
                     },}

    RETURN_TYPES = ('IMAGE','INT',)
    RETURN_NAMES = ("frames","count",)
    # OUTPUT_IS_LIST = (False,)

    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Video"
    INPUT_IS_LIST = True

    def load_video_cv_fallback(self, video, frame_load_cap, skip_first_frames):
        # print('#video',video)
        try:
            video_cap = cv2.VideoCapture(video)
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
       
        return (images, frames_added,)

    def run(self, scenes_video,index):
        print('#scenes_video',index,scenes_video)
        index=index[0]
        if len(scenes_video) > index:
            vp=scenes_video[index]

            return self.load_video_cv_fallback(vp,0,0)
        
        return ([], 0,)