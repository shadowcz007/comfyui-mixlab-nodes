from transformers import pipeline, set_seed,AutoTokenizer, AutoModelForSeq2SeqLM
import random
import re

import os,sys
import folder_paths

# from PIL import Image
import importlib.util

import comfy.utils
# import numpy as np
import torch
import random
from lark import Lark, Transformer, v_args


global _available
_available=True

def get_text_generator_path():
    try:
        return folder_paths.get_folder_paths('prompt_generator')[0]
    except:
        return os.path.join(folder_paths.models_dir, "prompt_generator")

prompt_generator=get_text_generator_path()

text_generator_model_path=os.path.join(prompt_generator, "text2image-prompt-generator")
if not os.path.exists(text_generator_model_path):
    print(f"## text_generator_model not found: {text_generator_model_path}, pls download from https://huggingface.co/succinctly/text2image-prompt-generator/tree/main")
    text_generator_model_path='succinctly/text2image-prompt-generator'

zh_en_model_path=os.path.join(prompt_generator, "opus-mt-zh-en")
if not os.path.exists(zh_en_model_path):
    print(f"## zh_en_model not found: {zh_en_model_path}, pls download from https://huggingface.co/Helsinki-NLP/opus-mt-zh-en/tree/main")
    zh_en_model_path='Helsinki-NLP/opus-mt-zh-en'


def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None


try:
    if is_installed('sentencepiece')==False:
        import subprocess

        # 安装
        print('#pip install sentencepiece')

        result = subprocess.run([sys.executable, '-s', '-m', 'pip', 'install', 'sentencepiece'], capture_output=True, text=True)

        #检查命令执行结果
        if result.returncode == 0 and is_installed('sentencepiece'):
            print("#install success")
            _available=True
        else:
            print("#install error")
            _available=False
        
    else:
        _available=True

except:
    _available=False



def translate(text):
    global text_pipe,zh_en_model,zh_en_tokenizer
    
    if zh_en_model==None:
        zh_en_model = AutoModelForSeq2SeqLM.from_pretrained(zh_en_model_path).eval()
        zh_en_tokenizer = AutoTokenizer.from_pretrained(zh_en_model_path,padding=True, truncation=True)
    
    zh_en_model.to("cuda" if torch.cuda.is_available() else "cpu")
    with torch.no_grad():
        encoded = zh_en_tokenizer([text], return_tensors="pt")
        encoded.to(zh_en_model.device)
        sequences = zh_en_model.generate(**encoded)
        return zh_en_tokenizer.batch_decode(sequences, skip_special_tokens=True)[0]

# input = "青春不能回头，所以青春没有终点。 ——《火影忍者》"
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

def correct_prompt_syntax(prompt=""):

    # print("input prompt",prompt)
    corrected_elements = []
    # 处理成统一的英文标点
    prompt = prompt.replace('（', '(').replace('）', ')').replace('，', ',').replace(';', ',').replace('。', '.').replace('：',':')
    # 删除多余的空格
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    prompt = prompt.replace("< ","<").replace(" >",">").replace("( ","(").replace(" )",")").replace("[ ","[").replace(' ]',']')

    # 分词
    prompt_elements = prompt.split(',')

    def balance_brackets(element, open_bracket, close_bracket):
        open_brackets_count = element.count(open_bracket)
        close_brackets_count = element.count(close_bracket)
        return element + close_bracket * (open_brackets_count - close_brackets_count)

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
    return  ','.join(corrected_elements)


# # 示例使用
# test_prompt = "((middle-century castles)), [forsaken: 0.8], (mystery dragons: 1.3, mist forests, sunsets, quiet; (((dummy)), [fisting city: 0.5] background, radiant, soft and flavoured,] promising mountains, ((starry: 1.6), [[crowds], [middle-century castle: urban landscapes of the future: 0.5], [yellow: bright sun: 0.7], overlooking"
# corrected_prompt = correct_prompt_syntax(test_prompt)
# print(corrected_prompt)

def detect_language(input_str):
    # 统计中文和英文字符的数量
    count_cn = count_en = 0
    for char in input_str:
        if '\u4e00' <= char <= '\u9fff':
            count_cn += 1
        elif char.isalpha():
            count_en += 1

    # 根据统计的字符数量判断主要语言
    if count_cn > count_en:
        return "cn"
    elif count_en > count_cn:
        return "en"
    else:
        return "unknow"




#定义Prompt文法
grammar = """
start: sentence
sentence: phrase ("," phrase)*
phrase: emphasis | weight | word | lora | embedding | schedule
emphasis: "(" sentence ")" -> emphasis
        | "[" sentence "]" -> weak_emphasis
weight: "(" word ":" NUMBER ")"
schedule: "[" word ":" word ":" NUMBER "]"
lora: "<" WORD ":" WORD (":" NUMBER)? (":" NUMBER)? ">"
embedding: "embedding" ":" WORD (":" NUMBER)? (":" NUMBER)?
word: WORD

NUMBER: /\s*-?\d+(\.\d+)?\s*/
WORD: /[^,:\(\)\[\]<>]+/
"""



@v_args(inline=True)  # Decorator to flatten the tree directly into the function arguments
class ChinesePromptTranslate(Transformer):
 
    def sentence(self, *args):
        return ", ".join(args)

    def phrase(self, *args):
        return "".join(args)

    def emphasis(self, *args):
        # Reconstruct the emphasis with translated content
        return "(" + "".join(args) + ")"

    def weak_emphasis(self, *args):
        print('weak_emphasis:',args)
        return "[" + "".join(args) + "]"
    
    def embedding(self,*args):
        print('prompt embedding',args[0])
        if len(args) == 1:
            # print('prompt embedding',str(args[0]))
            # 只传递了一个参数，意味着只有embedding名称没有数字
            embedding_name = str(args[0])
            return f"embedding:{embedding_name}"
        elif len(args) > 1:
            embedding_name,*numbers = args
           
            if len(numbers)==2:
                return f"embedding:{embedding_name}:{numbers[0]}:{numbers[1]}"
            elif len(numbers)==1:
                return f"embedding:{embedding_name}:{numbers[0]}"
            else:
                return f"embedding:{embedding_name}"

    def lora(self,*args):
        print('lora prompt',*args)
        if len(args) == 1:
            return f"<lora:{loar_name}>"
        elif len(args) > 1: 
            # print('lora', args)
            _,loar_name,*numbers = args
            loar_name = str(loar_name).strip()
            if len(numbers)==2:
                return f"<lora:{loar_name}:{numbers[0]}:{numbers[1]}>"
            elif len(numbers)==1:
                return f"<lora:{loar_name}:{numbers[0]}>"
            else:
                return f"<lora:{loar_name}>"
    
    def weight(self, word,number):
        translated_word = translate(str(word)).rstrip('.')
        return f"({translated_word}:{str(number).strip()})"
    
    def schedule(self,*args):
        print('prompt schedule',args)
        data = [str(arg).strip() for arg in args] 
        
        return f"[{':'.join(data)}]"

    def word(self, word):
        # Translate each word using the dictionary
        if detect_language(str(word)) == "cn":
            return  translate(str(word)).rstrip('.')
        else:
            return str(word).rstrip('.')
        
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
                    "seed":("INT", {"default": 100, "min": 100, "max":  0xffffffffffffffff}), 
                    
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
        

        seed=seed[0]
        generation=generation[0]

        # 进度条
        pbar = comfy.utils.ProgressBar(len(text)+1)
        texts = [correct_prompt_syntax(t) for t in text]

        global text_pipe,zh_en_model,zh_en_tokenizer
        if zh_en_model==None:
            zh_en_model = AutoModelForSeq2SeqLM.from_pretrained(zh_en_model_path).eval()
            zh_en_tokenizer = AutoTokenizer.from_pretrained(zh_en_model_path,padding=True, truncation=True)
        
        zh_en_model.to("cuda" if torch.cuda.is_available() else "cpu")
            # zh_en_tokenizer.to("cuda" if torch.cuda.is_available() else "cpu")
        
        text_pipe=pipeline('text-generation', model=text_generator_model_path,device="cuda" if torch.cuda.is_available() else "cpu")
        
        # text_pipe.model.to("cuda" if torch.cuda.is_available() else "cpu")

        prompt_result=[]

        # print('zh_en_model device',zh_en_model.device,text_pipe.model.device,torch.cuda.current_device() )
        en_texts=[]

        for t in texts:
            if t:
                parser = Lark(grammar, start="start", parser="lalr", transformer=ChinesePromptTranslate())
                try:
                    result = parser.parse(t).children
                    en_texts.append(result[0])
                except:
                    print(f"Error parsing '{t}'")
                    t = translate(str(t))
                    en_texts.append(t)
                

        zh_en_model.to('cpu')
        print("test en_text",en_texts)
        # en_text.to("cuda" if torch.cuda.is_available() else "cpu")

        pbar.update(1)
        for t in en_texts:
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

        print('prompt_result',prompt_result,)
        # prompt_result = [','.join(correct_prompt_syntax(p)) for p in prompt_result]
        if len(prompt_result)==0:
            prompt_result=[""]
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
                    "seed":("INT", {"default": 100, "min": 100, "max":  0xffffffffffffffff}), 
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
