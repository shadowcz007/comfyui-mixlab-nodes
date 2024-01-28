import os,sys
import folder_paths

from PIL import Image
import importlib.util

import comfy.utils
import numpy as np
import json
import torch
import random


# from clip_interrogator import Config, Interrogator


global _available
_available=False

def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None


try:
    if is_installed('clip_interrogator')==False:
        import subprocess

        # 安装
        print('#pip install clip-interrogator==0.6.0')

        result = subprocess.run([sys.executable, '-s', '-m', 'pip', 'install', 'clip-interrogator==0.6.0'], capture_output=True, text=True)

        #检查命令执行结果
        if result.returncode == 0:
            print("#install success")
            from clip_interrogator import Config, Interrogator
            _available=True
        else:
            print("#install error")
        
    else:
        from clip_interrogator import Config, Interrogator
        _available=True

except:
    _available=False

try:
    from transformers import AutoProcessor, BlipForConditionalGeneration
except:
    _available=False
    print('pls check  transformers.__version__>=4.36.0:: AutoProcessor, BlipForConditionalGeneration')



def load_caption_model(model_path,config,t='blip-base'):
    dtype=torch.float16 if config.device == 'cuda' else torch.float32
    caption_model = BlipForConditionalGeneration.from_pretrained(model_path, torch_dtype=dtype)
    
    caption_processor = AutoProcessor.from_pretrained(model_path)

    caption_model.eval()
    if not config.caption_offload:
        caption_model = caption_model.to(config.device)
    
    return (caption_model,caption_processor)
    


caption_model_path=os.path.join(folder_paths.models_dir, "clip_interrogator/Salesforce/blip-image-captioning-base")
if not os.path.exists(caption_model_path):
    print(f"## clip_interrogator_model not found: {caption_model_path}, pls download from https://huggingface.co/Salesforce/blip-image-captioning-base")
    caption_model_path='Salesforce/blip-image-captioning-base'

cache_path=os.path.join(folder_paths.models_dir, "clip_interrogator")
if not os.path.exists(cache_path):
    os.mkdir(cache_path)

# Tensor to PIL
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

# Convert PIL to Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def image_analysis_fn(ci,image):
    image = image.convert('RGB')
    image_features = ci.image_to_features(image)

    top_mediums = ci.mediums.rank(image_features, 5)
    top_artists = ci.artists.rank(image_features, 5)
    top_movements = ci.movements.rank(image_features, 5)
    top_trendings = ci.trendings.rank(image_features, 5)
    top_flavors = ci.flavors.rank(image_features, 5)

    medium_ranks = {medium: sim for medium, sim in zip(top_mediums, ci.similarities(image_features, top_mediums))}
    artist_ranks = {artist: sim for artist, sim in zip(top_artists, ci.similarities(image_features, top_artists))}
    movement_ranks = {movement: sim for movement, sim in zip(top_movements, ci.similarities(image_features, top_movements))}
    trending_ranks = {trending: sim for trending, sim in zip(top_trendings, ci.similarities(image_features, top_trendings))}
    flavor_ranks = {flavor: sim for flavor, sim in zip(top_flavors, ci.similarities(image_features, top_flavors))}
    
    return {
        "medium_ranks":medium_ranks, 
        "artist_ranks":artist_ranks, 
        "movement_ranks":movement_ranks, 
        "trending_ranks":trending_ranks, 
        "flavor_ranks":flavor_ranks
        }


def generate_sentences(data):
    sentences = []

    # Get the length of data
    data_length = len(data)

    # Use a recursive function to handle variable-length data
    def generate_recursive(index, current_sentence, current_score):
        # Check if recursion is complete
        if index == data_length:
            sentences.append({"sentence": current_sentence, "score": current_score})
            return

        # Get the current level data
        current_data = data[index]

        # Iterate through the current level data
        for phrase in current_data:
            sentence = current_sentence + ("," if current_sentence.strip() else "") + phrase
            score = current_score + current_data[phrase]
            generate_recursive(index + 1, sentence, score)

    # Start recursive generation of sentences
    generate_recursive(0, "", 0)

    # Sort the generated sentences by score in descending order
    sentences.sort(key=lambda x: x["score"], reverse=True)

    def get_random_elements(elements, num):
        return random.sample(elements, num)

    ps = get_random_elements(sentences, 5)
    ps = [s["sentence"] for s in sorted(ps, key=lambda x: x["score"], reverse=True)]

    return ps




def image_to_prompt(ci,image, mode):
    ci.config.chunk_size = 2048 if ci.config.clip_model_name == "ViT-L-14/openai" else 1024
    ci.config.flavor_intermediate_count = 2048 if ci.config.clip_model_name == "ViT-L-14/openai" else 1024
    image = image.convert('RGB')
    if mode == 'best':
        return ci.interrogate(image)
    elif mode == 'classic':
        return ci.interrogate_classic(image)
    elif mode == 'fast':
        return ci.interrogate_fast(image)
    elif mode == 'negative':
        return ci.interrogate_negative(image)

# image = Image.open(image_path).convert('RGB')
# ci = Interrogator(Config(clip_model_name="ViT-L-14/openai"))
# print(ci.interrogate(image))


class ClipInterrogator:

    global _available
    available=_available
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "prompt_mode": (['fast','classic','best','negative'],),
            "image_analysis": (["off","on"],), 
                             },

                # "optional":{
                #     "output":("CLIPINTERROGATOR", {"multiline": True,"default": "", "dynamicPrompts": False})
                # },

                }
    
    RETURN_TYPES = ("STRING","STRING",)
    RETURN_NAMES = ("prompt","random_samples",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Prompt"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,True,)
    global ci
    ci = None
    def run(self,image,prompt_mode,image_analysis):
        global ci

        prompt_mode=prompt_mode[0]
        analysis=image_analysis[0]

        prompt_result=[]
        analysis_result=[]

        # 进度条
        pbar = comfy.utils.ProgressBar(len(image)*(2 if analysis=='on' else 1))
        
        if ci==None:
            config=Config(
                clip_model_name="ViT-L-14/openai",
                device="cuda" if torch.cuda.is_available() else "cpu",
                download_cache=True,
                clip_model_path=cache_path,
                cache_path=cache_path
                )
            config.apply_low_vram_defaults()

            caption_model,caption_processor=load_caption_model(caption_model_path,config)

            config.caption_model= caption_model
            config.caption_processor= caption_processor

            ci = Interrogator(config)
        # else:
        #     simple_lama.model.to("cuda" if torch.cuda.is_available() else "cpu")

        for i in range(len(image)):
            im=image[i]

            im=tensor2pil(im)
            im=im.convert('RGB')

            if analysis=='on':
                analysis_res=image_analysis_fn(ci,im)
                analysis_result.append( analysis_res )
                pbar.update(1)

            prompt=image_to_prompt(ci,im,prompt_mode)
            pbar.update(1)
            prompt_result.append(prompt)


        # result.save("inpainted.png")
        if ci.config.clip_offload and not ci.clip_offloaded:
            ci.clip_model = ci.clip_model.to('cpu')
            ci.clip_offloaded = True

        if ci.config.caption_offload and not ci.caption_offloaded:
            ci.caption_model = ci.caption_model.to('cpu')
            ci.caption_offloaded = True

        # analysis_result=[]
        # items = app.graph.getNodeById(31).widgets[2].value["items"]
        
        random_samples=[]

        for r in analysis_result:
            random_sample = generate_sentences([r['medium_ranks'], r['artist_ranks'],r['movement_ranks'],r['trending_ranks'],r['flavor_ranks']])
            for s in random_sample:
                random_samples.append(s)
        # print(len(random_samples))
        # print('-----')
        # print( random_samples)
        return {
            "ui":{
                    "prompt": prompt_result,
                    "analysis":analysis_result,
                    "random_samples":random_samples
                },
            "result": (prompt_result,random_samples,)}