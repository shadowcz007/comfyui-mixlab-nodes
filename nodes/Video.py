import os
import hashlib
import json
import subprocess
import shutil
import re
import time
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

    RETURN_TYPES = ("IMAGE", "INT",)
    RETURN_NAMES = ("IMAGE", "frame_count",)
    FUNCTION = "load_video"

    OUTPUT_IS_LIST = (True,False,)


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
        # check if video is a gif - will need to use cv fallback to read frames
        # use cv fallback if ffmpeg not installed or gif
        if ffmpeg_path is None:
            return self.load_video_cv_fallback(video, frame_load_cap, skip_first_frames)
        # otherwise, continue with ffmpeg
        video_path = folder_paths.get_annotated_filepath(video)
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

        return (imgs, len(imgs))

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