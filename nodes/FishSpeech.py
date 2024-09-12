# 修改自 https://github.com/AnyaCoder/ComfyUI-fish-speech/

import torch,os
from pathlib import Path
from .fish_speech.llama_utils import load_model as load_llama_model
from .fish_speech.vqgan_utils import load_model as load_vqgan_model
from .fish_speech.vqgan_utils import audio2prompt, semantic2audio
from .fish_speech.llama_utils import prompt2semantic

import folder_paths

def get_checkpoints_path():
    try:
        return folder_paths.get_folder_paths('fish_speech')[0]
    except:
        return os.path.join(folder_paths.models_dir, "fish_speech")

current_directory = os.path.dirname(os.path.abspath(__file__))
configs_dir=os.path.join(current_directory,"fish_speech","configs")

CKPTS_FOLDER =  Path(get_checkpoints_path())

CONFIGS_FOLDER = Path(configs_dir)


class LoadVQGAN:
    def __init__(self):
        self.vqgan = None
        pass
    
    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
                "config": ([str(c.relative_to(CONFIGS_FOLDER)) for c in CONFIGS_FOLDER.glob("*vq*.yaml")], {"default": "firefly_gan_vq.yaml"}),
                "model": ([str(p.relative_to(CKPTS_FOLDER)) for p in CKPTS_FOLDER.glob("*vq*.pth")], ), 
                "device": (["cuda", "cpu"], {"default": "cuda"}),
            },
        }
    
    @classmethod
    def IS_CHANGED(s, model):
        return ""

    @classmethod
    def VALIDATE_INPUTS(s, model):
        return True

    RETURN_TYPES = ("VQGAN", )
    RETURN_NAMES = ("vqgan", )

    FUNCTION = "load_vqgan"

    #OUTPUT_NODE = False

    CATEGORY = "♾️Mixlab/Audio/FishSpeech"

    def load_vqgan(self, config, model, device):
        config = config.rsplit(".", 1)[0]
        model = str(CKPTS_FOLDER / model)
        if self.vqgan is None:
            self.vqgan = load_vqgan_model(config,model, device=device)
        return (self.vqgan, )



class AudioToPrompt:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
                "vqgan": ("VQGAN", ),
                "audio": ("AUDIO", ),
                "device": (["cuda", "cpu"], {"default": "cuda"}),
            },
        }

    
    RETURN_TYPES = ("AUDIO", "NUMPY")
    RETURN_NAMES = ("restored_audio", "prompt_tokens")

    FUNCTION = "encode"

    #OUTPUT_NODE = False

    CATEGORY = "♾️Mixlab/Audio/FishSpeech"

    def encode(self, vqgan, audio, device):
        return audio2prompt(vqgan, audio, device)
    


class Prompt2Semantic:
  
    def __init__(self):
        self.llama = None
        self.decode_func = None
        pass
    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": { 
                "text": ("STRING", {"multiline": True}),
                "prompt_text": ("STRING", {"multiline": True}),
                "prompt_tokens": ("NUMPY", ),
                "max_new_tokens": ("INT", {
                    "default": 1024, 
                    "min": 0,
                    "max": 2048,
                    "step": 8,
                    "display": "number",
                }),
                "top_p": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.6,
                    "max": 0.9,
                    "step": 0.01,
                    "display": "number",
                }),
                "repetition_penalty": ("FLOAT", {
                    "default": 1.2,
                    "min": 1.0,
                    "max": 1.5,
                    "step": 0.01,
                    "display": "number",
                }),
                "temperature": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.6,
                    "max": 0.9,
                    "step": 0.01,
                    "display": "number",
                }),
                
                "seed": ("INT", {
                    "default": 42,
                    "min": 0,
                    "max": 4294967295,
                    "step": 1,
                    "display": "number",
                }),
                "iterative_prompt": (["yes", "no"], {"default": "yes"}),
                "chunk_length": ("INT", {
                    "default": 100,
                    "min": 0,
                    "max": 500,
                    "step": 8,
                    "display": "number",
                }),
                
                "compile": (["yes", "no"], {"default": "no"}),
                "precision": (["bf16", "half"], {"default": "bf16"}),
 
                # "decode_func": ("DECODE_FUNC", ),
                "device": (["cuda", "cpu"], {"default": "cuda"}),

            },
        }
    
    RETURN_TYPES = ("NUMPY", )
    RETURN_NAMES = ("codes", )

    FUNCTION = "decode"

    #OUTPUT_NODE = False

    CATEGORY = "♾️Mixlab/Audio/FishSpeech"

    def decode(
        self,
        
        text: str,
        prompt_text: str,
        prompt_tokens,
        max_new_tokens: int,
        top_p: float,
        repetition_penalty: float,
        temperature: float,
       
        seed: int,
        iterative_prompt: str,
        chunk_length: int,

         compile: str,
         precision,
        device: str,
    ):
        
        model = get_checkpoints_path()
        precision = torch.bfloat16 if precision == "bf16" else torch.half
        compile=True if compile == "yes" else False
        if self.llama is None or self.decode_func is None:
            self.llama, self.decode_func = load_llama_model(model, device, precision, compile)
            

        return prompt2semantic(
            self.llama,
            self.decode_func,
            text,
            [prompt_text,],
            [prompt_tokens,],
            max_new_tokens,
            top_p,
            repetition_penalty,
            temperature,
            device,
            compile=True if compile == "yes" else False,
            seed=seed,
            iterative_prompt=True if iterative_prompt == "yes" else False,
            chunk_length=chunk_length,
        )



class Semantic2Audio:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vqgan": ("VQGAN", ),
                "codes": ("NUMPY", ),
                "device": (["cuda", "cpu"], {"default": "cuda"}),
            },
        }

    RETURN_TYPES = ("AUDIO", )
    RETURN_NAMES = ("generated_audio", )

    FUNCTION = "generate"

    #OUTPUT_NODE = False

    CATEGORY = "♾️Mixlab/Audio/FishSpeech"

    def generate(self, vqgan, codes, device):
        return semantic2audio(vqgan, codes, device)





