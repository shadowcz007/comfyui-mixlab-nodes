import os
import folder_paths
import numpy as np
import torch
from PIL import Image
# import comfy.utils
from PIL import Image
# from PIL.PngImagePlugin import PngInfo

import cv2
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.detectors import AdaptiveDetector

import os
import random
import string


class AnyType(str):
  """A special class that is always equal in not equal comparisons."""

  def __ne__(self, __value: object) -> bool:
    return False

any_type = AnyType("*")

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


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



def detect_scenes(video_path, min_scene_len=15, adaptive_threshold=3.0,callback=None):
    # Create a VideoManager object to load the video file.
    video_manager = VideoManager([video_path])
    video_manager.set_downscale_factor()

    # Create a SceneManager object to manage the scene detection process.
    scene_manager = SceneManager()
    # scene_manager.add_detector(AdaptiveDetector())

    adaptive_detector = AdaptiveDetector(adaptive_threshold=adaptive_threshold,min_scene_len=min_scene_len)
    
    scene_manager.add_detector(adaptive_detector)

    # Initialize the video processing loop.
    video_manager.start()
    if callback:
        scene_manager.detect_scenes(frame_source=video_manager,callback=callback)
    else:
        scene_manager.detect_scenes(frame_source=video_manager)

    # Iterate over the detected scenes and print their start and end timecodes.
    scenes = []
    for scene in scene_manager.get_scene_list():
        # start_time = scene[0].get_timecode()
        # end_time = scene[1].get_timecode()
        # scenes.append((start_time, end_time))
        scenes.append(scene)

    # Release the video manager and scene manager resources.
    video_manager.release()
    # scene_manager.release()

    return scenes


# 采样逻辑
def calculate_sample_range(start_frame, middle_frame, end_frame, number_of_sample_frames):
    half_samples = number_of_sample_frames // 2

    # 初始化采样帧列表
    samples = [middle_frame]

    if number_of_sample_frames==1:
        return samples

    # 计算间隔
    interval_before = (middle_frame - start_frame) // half_samples
    interval_after = (end_frame - middle_frame) // half_samples

    # 添加中间帧前的采样帧
    for i in range(1, half_samples + 1):
        sample_before = middle_frame - i * interval_before
        if sample_before >= start_frame:
            samples.insert(0, sample_before)

    # 添加中间帧后的采样帧
    for i in range(1, half_samples + 1):
        sample_after = middle_frame + i * interval_after
        if sample_after <= end_frame:
            samples.append(sample_after)

    # 如果采样帧数是偶数，则需要移除最靠近边界的一个帧
    if number_of_sample_frames % 2 == 0:
        if len(samples) > number_of_sample_frames:
            if abs(samples[0] - start_frame) < abs(samples[-1] - end_frame):
                samples.pop(0)
            else:
                samples.pop()

    return samples


def split_video_by_scenes(video_path, scenes, output_path, number_of_sample_frames=1):
    # Load the video file
    video = cv2.VideoCapture(video_path)
    
    # Get the video properties
    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Create a list to hold the paths of the scene videos
    scenes_video = []
    keyframes = []
    
    # Iterate over the scenes
    for scene_num, scene in enumerate(scenes, start=1):
        start_time = scene[0]
        end_time = scene[1]
        
        # Calculate the start and end frames based on the timestamps
        start_frame = int(start_time.get_seconds() * fps)
        end_frame = int(end_time.get_seconds() * fps)
        
        # Calculate the middle frame
        middle_frame = (start_frame + end_frame) // 2
        
        sample_frames=[]

        # Calculate the range of frames to sample
        # sample_range = range(max(start_frame, middle_frame - number_of_sample_frames // 2),
        #                      min(end_frame, middle_frame + number_of_sample_frames // 2 + 1))
        sample_range=calculate_sample_range(start_frame, middle_frame, end_frame, number_of_sample_frames)
        
        # Set the video file's current frame to the start frame
        video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Create a VideoWriter object for the current scene
        output_path1 = os.path.join(output_path, f"scene{scene_num}.avi")
        scenes_video.append(output_path1)
        writer = cv2.VideoWriter(output_path1, cv2.VideoWriter_fourcc(*'XVID'), fps, (width, height))
        
        # Write the frames of the current scene to the video file
        for frame_num in range(start_frame, end_frame + 1):
            ret, frame = video.read()
            if not ret:
                break
            writer.write(frame)
            
            # If this frame is in the sample range, save it to keyframes
            if frame_num in sample_range:
                # Convert the frame to RGB (OpenCV uses BGR by default)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Convert the frame to a PIL image
                pil_image = Image.fromarray(frame_rgb)

                sample_frames.append(pil2tensor(pil_image))
        
        keyframe_info = {
                    'start_frame': start_frame,
                    'end_frame': end_frame,
                    'sample_frames': sample_frames,
                    'video_path': output_path1
                }
        
        keyframes.append(keyframe_info)

        # Release the VideoWriter object
        writer.release()
    
    # Release the video file
    video.release()
    
    return scenes_video, keyframes


def get_files_with_extension(directory, extension):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                file = os.path.splitext(file)[0]
                file_path = os.path.join(root, file)
                file_name = os.path.relpath(file_path, directory)
                file_list.append(file_name)
    return file_list



class SceneInfoNode:
    @classmethod
    def INPUT_TYPES(cls):
        
        return {"required": {
                    "scenes": ('SCENE_',),
                    "index": ("INT", {"default": 0, "min": -1, "step": 1}),
                     },}

    RETURN_TYPES = ('IMAGE','INT','INT','SCENE_VIDEO',)
    RETURN_NAMES = ("sample_frames","start_frame","end_frame","scene_video",)
    # OUTPUT_IS_LIST = (False,)

    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Video"
    INPUT_IS_LIST = False
    def run(self,scenes,index):
        
        if index==-1:
            images=[]
            start_frames=[]
            end_frames=[]
            video_paths=[]
            for i in range(len(scenes)):
                s=scenes[i]
                for sf in s['sample_frames']:
                    images.append(sf)
                start_frames.append(s['start_frame'])
                end_frames.append(s['end_frame'])
                video_paths.append(s['video_path'])
            images = torch.cat(images, dim=0)
            return (images,start_frames,end_frames,video_paths,)
        else:
            s=scenes[index]
            images=s['sample_frames']
            images = torch.cat(images, dim=0)
            return (images,s['start_frame'],s['end_frame'],s['video_path'],)
 

# 分割视频
class ScenedetectNode_:
    @classmethod
    def INPUT_TYPES(cls):
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
                     "min_scene_len": ("INT", {"default": 10, "min": 1, "step": 1}),
                     "adaptive_threshold": ("FLOAT", {"default": 2.5, "min": 0, "step": 0.1}), 
                     "number_of_sample_frames": ("INT", {"default": 1, "min": 1, "step": 1}), # 抽取的帧数，默认是1帧，中间帧
                     },}

    RETURN_TYPES = ("SCENE_VIDEO","SCENE_", "INT",)
    RETURN_NAMES = ("scenes_video","scenes","scene_len",)
    OUTPUT_IS_LIST = (False,False,False,)

    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/Video"

    def run(self, video, min_scene_len,adaptive_threshold,number_of_sample_frames):
        video_path = folder_paths.get_annotated_filepath(video)
        # Example usage:
        scenes = detect_scenes(video_path, min_scene_len=min_scene_len, adaptive_threshold=adaptive_threshold)
        # print("##scenes", scenes)
        # for start_time, end_time in scenes:
        #     print(f"Scene detected from {start_time} to {end_time}")

        
        tp=folder_paths.get_temp_directory()
        basename = os.path.basename(video_path)  # 获取文件名
        name_without_extension = os.path.splitext(basename)[0]  # 去掉文件后缀

        folder_path = create_folder(tp,name_without_extension)
        # print("New folder created:", folder_path)

        vs_files,keyframes=split_video_by_scenes(video_path,scenes,folder_path,number_of_sample_frames)
        # print("New folder created:", vs_files)

        return (vs_files,keyframes,len(scenes),)
    

