import sys
from os import path
sys.path.insert(0, path.dirname(__file__))
from PIL import Image
import numpy as np
import torch

from folder_paths import get_folder_paths, get_full_path, get_save_image_path, get_output_directory,models_dir
from comfy.model_management import get_torch_device
from .tsr.system import TSR

import comfy.utils


def get_triposr_model_path():
    try:
        return path.join(get_folder_paths('triposr')[0],'model.ckpt')
    except:
        return path.join(path.join(models_dir, "triposr"),'model.ckpt')
    
triposr_model_path=get_triposr_model_path()


# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def fill_background(image):
    im = np.array(image).astype(np.float32) / 255.0
    im = im[:, :, :3] * im[:, :, 3:4] + (1 - im[:, :, 3:4]) * 0.5
    im = Image.fromarray((im * 255.0).astype(np.uint8))
    return im


class LoadTripoSRModel:
    def __init__(self):
        self.initialized_model = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # "model": (get_filename_list("checkpoints"),),
                "chunk_size": ("INT", {"default": 8192, "min": 0, "max": 10000})
            }
        }

    RETURN_TYPES = ("TRIPOSR_MODEL",)
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/3D/TripoSR"

    def run(self, chunk_size):
        device = get_torch_device()

        if not torch.cuda.is_available():
            device = "cpu"

        if not self.initialized_model:
            # triposr_model_path
            print("#Loading TripoSR model",triposr_model_path)
            self.initialized_model = TSR.from_pretrained_custom(
                weight_path=triposr_model_path,
                config_path=path.join(path.dirname(__file__), "tsr/config.yaml")
            )
            self.initialized_model.renderer.set_chunk_size(chunk_size)
            self.initialized_model.to(device)

        return (self.initialized_model,)


class TripoSRSampler:
    def __init__(self):
        self.initialized_model = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("TRIPOSR_MODEL",),
                "image": ("IMAGE",),
                "resolution": ("INT", {"default": 256, "min": 128, "max": 12288}),
                "threshold": ("FLOAT", {"default": 25.0, "min": 0.0, "step": 0.01}),
                "device":(["auto","cpu"],), 
            },
            "optional": {
                "mask": ("MASK",)
            }
        }

    RETURN_TYPES = ("MESH",)
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/3D/TripoSR"

    def run(self, model, image, resolution, threshold,device='auto', mask=None):

        reference_image=image
        reference_mask=mask

        device = get_torch_device()

        if not torch.cuda.is_available():
            device = "cpu"

        if device=='cpu':
            device = "cpu"

        print('#TripoSRSampler device',device)

        to_images=[]

        for i in range(len(reference_image)):

            image = reference_image[i]
            
            if reference_mask is not None:
                mask = reference_mask[i].unsqueeze(2)
                image = torch.cat((image, mask), dim=2).detach().cpu().numpy()
                image = Image.fromarray(np.clip(255. * image, 0, 255).astype(np.uint8))
                image = fill_background(image)
            else:
                image = tensor2pil(image)

            image = image.convert('RGB')

            to_images.append(image)

        # 进度条
        pbar = comfy.utils.ProgressBar(len(to_images))
        def callback(c):
            pbar.update(1)    

        scene_codes = model(to_images, device)
        meshes = model.extract_mesh(scene_codes, resolution=resolution, threshold=threshold,callback=callback)

        del model
        return (meshes,)


class SaveTripoSRMesh:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "mesh": ("MESH",),
                # "format":(["glb","obj"],), 
                "filename_prefix":("STRING", {"multiline": False,"default": "TripoSR_"})
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "run"
    CATEGORY = "♾️Mixlab/3D/TripoSR"

    def run(self, mesh,filename_prefix):
        format='glb'
        saved = list()
        full_output_folder, filename, counter, subfolder, filename_prefix = get_save_image_path(filename_prefix,
                                                                                                get_output_directory())

        for (index, single_mesh) in enumerate(mesh):
            filename_with_batch_num = filename.replace("%batch_num%", str(index))
            file = f"{filename_with_batch_num}_{counter:05}_.{format}"
            single_mesh.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]]))
            single_mesh.export(path.join(full_output_folder, file))
            saved.append({
                "filename": file,
                "type": "output",
                "subfolder": subfolder
            })

        return {"ui": {"mesh": saved}}



