from transformers import pipeline, set_seed,AutoTokenizer, AutoModelForSeq2SeqLM
import random
import re

import os,sys
import folder_paths

# from PIL import Image
# import importlib.util

import comfy.utils
# import numpy as np
import torch
import random

global _available
_available=True


text_generator_model_path=os.path.join(folder_paths.models_dir, "prompt_generator/text2image-prompt-generator")
if not os.path.exists(text_generator_model_path):
    print(f"## text_generator_model not found: {text_generator_model_path}, pls download from https://huggingface.co/succinctly/text2image-prompt-generator/tree/main")
    text_generator_model_path='succinctly/text2image-prompt-generator'

zh_en_model_path=os.path.join(folder_paths.models_dir, "prompt_generator/opus-mt-zh-en")
if not os.path.exists(zh_en_model_path):
    print(f"## zh_en_model not found: {zh_en_model_path}, pls download from https://huggingface.co/Helsinki-NLP/opus-mt-zh-en/tree/main")
    zh_en_model_path='Helsinki-NLP/opus-mt-zh-en'



def translate(zh_en_tokenizer,zh_en_model,texts):
    with torch.no_grad():
        encoded = zh_en_tokenizer(texts, return_tensors="pt")
        encoded.to(zh_en_model.device)
        sequences = zh_en_model.generate(**encoded)
        return zh_en_tokenizer.batch_decode(sequences, skip_special_tokens=True)

input = "青春不能回头，所以青春没有终点。 ——《火影忍者》"
# print(input, translate(input))


def text_generate(text_pipe,input,seed=None):
    
    if seed==None:
        seed = random.randint(100, 1000000)
    
    set_seed(seed)

    for count in range(6):    
        sequences = text_pipe(input, max_length=random.randint(60, 90), num_return_sequences=8)
        list = []
        for sequence in sequences:
            line = sequence['generated_text'].strip()
            if line != input and len(line) > (len(input) + 4) and line.endswith((":", "-", "—")) is False:
                list.append(line)

        result = "\n".join(list)
        result = re.sub('[^ ]+\.[^ ]+','', result)
        result = result.replace("<", "").replace(">", "")
        if result != "":
            return result
        if count == 5:
            return result

# input = "Youth can't turn back, so there's no end to youth."
# print(input, text_generate(input))

    
import re

def correct_prompt_syntax(prompt):

    print("input prompt",prompt)
    corrected_elements = []
    # 处理成统一的英文标点
    prompt = prompt.replace('（', '(').replace('）', ')').replace('，', ',').replace(';', ',').replace('。', '.').replace('：',':')
    # 删除多余的空格
    prompt = re.sub(r'\s+', ' ', prompt).strip()

    # 分词
    prompt_elements = prompt.split(',')

    for element in prompt_elements:
        element = element.strip()

        # 处理空元素
        if not element:
            continue

        # 检查并处理圆括号、方括号、尖括号
        if element[0] in '([':
            corrected_element = balance_brackets(element, '(', ')') if element[0] == '(' else balance_brackets(element, '[', ']')
        elif element[0] == '<':
            corrected_element = balance_brackets(element, '<', '>')
        else:
            # 删除开头的右括号或右方括号
            corrected_element = element.lstrip(')]')

        corrected_elements.append(corrected_element)

    # 重组修正后的prompt
    corrected_prompt = ', '.join(corrected_elements)
    print("output prompt",corrected_prompt)
    return corrected_prompt

def balance_brackets(element, open_bracket, close_bracket):
    open_brackets_count = element.count(open_bracket)
    close_brackets_count = element.count(close_bracket)
    return element + close_bracket * (open_brackets_count - close_brackets_count)

# # 示例使用
# test_prompt = "((middle-century castles)), [forsaken: 0.8], (mystery dragons: 1.3, mist forests, sunsets, quiet; (((dummy)), [fisting city: 0.5] background, radiant, soft and flavoured,] promising mountains, ((starry: 1.6), [[crowds], [middle-century castle: urban landscapes of the future: 0.5], [yellow: bright sun: 0.7], overlooking"
# corrected_prompt = correct_prompt_syntax(test_prompt)
# print(corrected_prompt)

        
        
class ChinesePrompt:

    global _available
    available=_available
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
               "text": ("STRING",{"multiline": True,"default": "", "dynamicPrompts": False}),
               "generation": (["on","off"],{"default": "off"}), 
                             },
               
                "optional":{
                    "seed":("INT", {"default": 100, "min": 100, "max": 1000000}), 
                    
                },

                }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Prompt"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    global text_pipe,zh_en_model,zh_en_tokenizer

    text_pipe= None
    zh_en_model=None
    zh_en_tokenizer=None 

    def run(self,text,seed,generation):
        global text_pipe,zh_en_model,zh_en_tokenizer

        seed=seed[0]
        generation=generation[0]

        # 进度条
        pbar = comfy.utils.ProgressBar(len(text)+1)

        text = correct_prompt_syntax(text[0])

        if zh_en_model==None:
            zh_en_model = AutoModelForSeq2SeqLM.from_pretrained(zh_en_model_path).eval()
            zh_en_tokenizer = AutoTokenizer.from_pretrained(zh_en_model_path)
        
        zh_en_model.to("cuda" if torch.cuda.is_available() else "cpu")
            # zh_en_tokenizer.to("cuda" if torch.cuda.is_available() else "cpu")
        
        text_pipe=pipeline('text-generation', model=text_generator_model_path,device="cuda" if torch.cuda.is_available() else "cpu")
        
        # text_pipe.model.to("cuda" if torch.cuda.is_available() else "cpu")

        prompt_result=[]

        # print('zh_en_model device',zh_en_model.device,text_pipe.model.device,torch.cuda.current_device() )
        en_text=translate(zh_en_tokenizer,zh_en_model,text)
        
        zh_en_model.to('cpu')
        print("test en_text",en_text)
        # en_text.to("cuda" if torch.cuda.is_available() else "cpu")

        pbar.update(1)
        for t in en_text:
            if generation=='on':
                prompt =text_generate(text_pipe,t,seed)
                # 多条，还是单条
                lines = prompt.split("\n")
                longest_line = max(lines, key=len)
                # print(longest_line)
                prompt_result.append(longest_line)
            else:
                prompt_result.append(t)
            pbar.update(1)

        text_pipe.model.to('cpu')
        prompt_result = [correct_prompt_syntax(prompt_result[0])]
        
        return {
            "ui":{
                    "prompt": prompt_result
                },
            "result": (prompt_result,)}


class PromptGenerate:

    global _available
    available=_available
    
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "text": ("STRING",{"multiline": True,"default": "", "dynamicPrompts": False}),
                             },

                "optional":{
                    "multiple": (["off","on"],), 
                    "seed":("INT", {"default": 100, "min": 100, "max": 1000000}), 
                },

                }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Prompt"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    global text_pipe

    text_pipe= None
    # 

    def run(self,text,multiple,seed):
        global text_pipe

        seed=seed[0]

        multiple=multiple[0]

        # 进度条
        pbar = comfy.utils.ProgressBar(len(text))
        
        text_pipe=pipeline('text-generation', model=text_generator_model_path,device="cuda" if torch.cuda.is_available() else "cpu")
        
        prompt_result=[]

        for t in text:
            prompt =text_generate(text_pipe,t,seed)
            prompt = prompt.split("\n")
            if multiple=='off':
                prompt = [max(prompt, key=len)]
            
            for p in prompt:
                prompt_result.append(p)
            pbar.update(1)

        text_pipe.model.to('cpu')

        return {
            "ui":{
                    "prompt": prompt_result
                },
            "result": (prompt_result,)}
