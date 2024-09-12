# Referenced some code：https://github.com/IuvenisSapiens/ComfyUI_MiniCPM-V-2_6-int4

import os
import torch
import folder_paths
from transformers import AutoTokenizer, AutoModel
from torchvision.transforms.v2 import ToPILImage
# from decord import VideoReader, cpu  # pip install decord
# from PIL import Image

def get_model_path(n=""):
    try:
        return folder_paths.get_folder_paths(n)[0]
    except:
        return os.path.join(folder_paths.models_dir, n)
 

class MiniCPM_VQA_Simple:
    def __init__(self):
        self.model_checkpoint = None
        self.tokenizer = None
        self.model = None
        self.device = (
            torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        )
        self.bf16_support = (
            torch.cuda.is_available()
            and torch.cuda.get_device_capability(self.device)[0] >= 8
        )

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "text": ("STRING", {"default": "", "multiline": True}),   
                "seed": ("INT", {"default": -1}),  # add seed parameter, default is -1
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.7,
                    },
                ),
                "keep_model_loaded": ("BOOLEAN", {"default": False}),
            },
            
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "inference"
    CATEGORY = "♾️Mixlab/Image"

    def inference(
        self,
        images,
        text, 
        seed,  # add seed parameter, default is -1
        temperature,
        keep_model_loaded,
    ):
        if seed != -1:
            torch.manual_seed(seed)
        model_id = "openbmb/MiniCPM-V-2_6-int4"

        self.model_checkpoint = os.path.join( get_model_path("prompt_generator"), os.path.basename(model_id))

        if not os.path.exists(self.model_checkpoint):
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=model_id,
                local_dir=self.model_checkpoint,
                local_dir_use_symlinks=False,
                endpoint='https://hf-mirror.com'
            )

        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_checkpoint,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

        if self.model is None:
            self.model = AutoModel.from_pretrained(
                self.model_checkpoint,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                attn_implementation="sdpa",
                torch_dtype=torch.bfloat16 if self.bf16_support else torch.float16,
            )

        with torch.no_grad():
            images = images.permute([0, 3, 1, 2])
            images = [ToPILImage()(img).convert("RGB") for img in images]
            msgs = [{"role": "user", "content": images + [text]}]

            params = {"use_image_id": False, }

            # offload model to CPU
            # self.model = self.model.to(torch.device("cpu"))
            # self.model.eval()

            result = self.model.chat(
                image=None,
                msgs=msgs,
                tokenizer=self.tokenizer,
                sampling=True,
                # top_k=top_k,
                # top_p=top_p,
                temperature=temperature,
                # repetition_penalty=repetition_penalty,
                # max_new_tokens=max_new_tokens,
                **params,
            )
            # offload model to GPU
            # self.model = self.model.to(torch.device("cpu"))
            # self.model.eval()
            if not keep_model_loaded:
                del self.tokenizer  # release tokenizer memory
                del self.model  # release model memory
                self.tokenizer = None  # set tokenizer to None
                self.model = None  # set model to None
                torch.cuda.empty_cache()  # release GPU memory
                torch.cuda.ipc_collect()
            # print(result)
            return (result,)
