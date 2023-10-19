# 一些有用的模型
# https://huggingface.co/kandinsky-community/kandinsky-2-1

from diffusers import AutoPipelineForText2Image
import torch
import os


directory = os.path.dirname(__file__)


class KandinskyModelLoad:

    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {
                                "file_path": ("STRING",{"multiline": True,"default":os.path.join(directory,'model\kandinsky-2-1')}),
                                "image": ("IMAGE",),
                            }
            }
    
    RETURN_TYPES = ('IMAGE',)

    FUNCTION = "run"

    # OUTPUT_IS_LIST = (True,)

    CATEGORY = "Mixlab/model"
  
    # 运行的函数
    def run(self,file_path,image):
        print('#file_path',file_path)
       
        return (image,)
    


class KandinskyModel:

    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {   
                                "file_path": ("STRING",{"multiline": False,"default":os.path.join(directory,'model\kandinsky-2-1')}),
                                "prompt": ("STRING",{"multiline": True,"default": "A alien cheeseburger creature eating itself, claymation, cinematic, moody lighting"}),
                                "negative_prompt ": ("STRING",{"multiline": True,"default": "low quality, bad quality"})
                            }
            }
    
    RETURN_TYPES = ('IMAGE',)

    FUNCTION = "run"

    OUTPUT_IS_LIST = (True,)

    CATEGORY = "Mixlab/model"
  
    # 运行的函数
    def run(self,file_path,prompt,negative_prompt):
        print(file_path,prompt,negative_prompt)
        pipe = AutoPipelineForText2Image.from_pretrained(file_path, 
                                                         torch_dtype=torch.float16)
        pipe.enable_model_cpu_offload()

        image = pipe(prompt=prompt, negative_prompt=negative_prompt, 
                     prior_guidance_scale =1.0, height=768, width=768).images[0]
        # image.save("cheeseburger_monster.png")
        return (image,)



