import random
import comfy.utils
import json
from urllib import request, parse


# def queue_prompt(prompt_workflow):
#     p = {"prompt": prompt_workflow}
#     data = json.dumps(p).encode('utf-8')
#     req =  request.Request("http://127.0.0.1:8188/prompt", data=data)
#     request.urlopen(req)    


default_prompt1='''Swing
                                                Slide
                                                Climbing frame
                                                Sandbox
                                                See-saw
                                                Merry-go-round
                                                Jungle gym
                                                Trampoline
                                                Monkey bars
                                                Rocking horse
                                                Playhouse
                                                Hopscotch
                                                Balance beam
                                                Spring rider
                                                Water play area
                                                Ball pit
                                                Tunnel
                                                Zip line
                                                Basketball hoop
                                                Bicycle rack
                                                Spinner
                                                Climbing wall
                                                Rope ladder
                                                Tetherball
                                                Flying fox
                                                Swinging bridge
                                                Spiral slide
                                                Water sprinkler
                                                Pedal go-kart
                                                Miniature golf course
                                                '''
default_prompt1="\n".join([p.strip() for p in default_prompt1.split('\n') if p.strip()!=''])


def addWeight(text, weight=1):
    if weight == 1:
        return text
    else:
        return f"({text}:{round(weight,2)})"



class PromptSlide:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                
                "prompt_keyword": ("STRING", 
                         {
                            "multiline": False, 
                            "default": '',
                            "dynamicPrompts": False
                          }),

                "weight":("FLOAT", {"default": 1, "min": -3,"max": 3,
                                                                "step": 0.01,
                                                                "display": "slider"}),

                # "min_value":("FLOAT", {
                #         "default": -2, 
                #         "min": -10, 
                #         "max": 0xffffffffffffffff,
                #         "step": 0.01, 
                #         "display": "number"  
                #     }),
                # "max_value":("FLOAT", {
                #         "default": 2, 
                #         "min": -10, 
                #         "max": 0xffffffffffffffff,
                #         "step": 0.01, 
                #         "display": "number"  
                #     }),
              
                }
            }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/prompt"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)
    OUTPUT_NODE = False

    # 运行的函数
    def run(self,prompt_keyword,weight):
        # if weight < min_value:
        #     weight= min_value
        # elif weight > max_value:
        #     weight= max_value
        p=addWeight(prompt_keyword,weight)
        return (p,)




class RandomPrompt:

    '''
    @classmethod 是Python中的一个装饰器，用于将一个方法标记为类方法。
    类方法是与类相关联的方法，而不是与实例相关联的方法。
    这意味着类方法可以直接通过类进行调用，而不需要先创建一个类的实例。
    '''

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "max_count": ("INT", {"default": 9, "min": 1, "max": 1000}),
                # "image_field": ("IMAGE",),
                "mutable_prompt": ("STRING", 
                         {
                            "multiline": True, 
                            "default": default_prompt1
                          }),
                "immutable_prompt": ("STRING", 
                         {
                            "multiline": True, 
                            "default": 'sticker, Cartoon, ``'
                          }),
                "random_sample": (["enable", "disable"],),
                }
            }
    
    

    RETURN_TYPES = ("STRING",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/prompt"

    OUTPUT_IS_LIST = (True,)
    OUTPUT_NODE = True


    # 运行的函数
    def run(self,max_count,mutable_prompt,immutable_prompt,random_sample):
        # print('#运行的函数',mutable_prompt,immutable_prompt,max_count,random_sample)
        
        # Split the text into an array of words
        words1 = mutable_prompt.split("\n")

        # Split the text into an array of words
        words2 = immutable_prompt.split("\n")

        # 进度条
        pbar = comfy.utils.ProgressBar(len(words1)*len(words2))
        
        # Select a random word from the array
        # random_word = random.choice(words)

        prompts=[]
        for w1 in words1:
            w1=w1.strip()
            for w2 in words2:
                w2=w2.strip()
                if '``' not in w2:
                    w2=w2+',``'
                if w1!='' and w2!='':
                    prompts.append(w2.replace('``', w1))
                pbar.update(1)
        
        if len(prompts)==0:
            prompts.append(immutable_prompt)

        if random_sample=='enable':
            # 随机从数组中取max个元素
            prompts = random.sample(prompts, min(max_count,len(prompts)))
        else:
            prompts = prompts[:min(max_count,len(prompts))]

        # return (new_prompt)
        return {"ui": {"prompts": prompts}, "result": (prompts,)}





# class RunWorkflow:
#     @classmethod
#     def INPUT_TYPES(s):
#         return {
#             "required": {
#                 "workflow": ("STRING", {
#                             "multiline": False, 
#                             "default": ''
#                           }),
#                 "prompt": ("STRING", {
#                             "multiline": False, 
#                             "default": ''
#                           }),
#                  "image": ("IMAGE",),
#                  "input_node": ("STRING", {
#                             "multiline": False, 
#                             "default": ''
#                           }),
#                  "output_node": ("STRING", {
#                             "multiline": False, 
#                             "default": ''
#                           }),
#                 },
                
#             }
    
    

#     RETURN_TYPES = ("IMAGE","STRING",)

#     FUNCTION = "run"

#     CATEGORY = "♾️Mixlab/workflow"

#     OUTPUT_IS_LIST = (True,)
#     OUTPUT_NODE = True


#     # 运行的函数
#     def run(self,workflow,prompt,image,input_node,output_node):
#         print('#运行的函数',prompt,image,input_node,output_node)
#         workflow=json.loads(workflow)
#         input_node=input_node.split(".")
#         workflow[input_node[0]][input_node[1]][input_node[2]]=prompt

#         workflow_new={}
#         # 遍历，seed设为随机
#         for key, value in workflow.items():
#             if 'inputs' in value:
#                 if 'seed' in value['inputs']:
#                     value['inputs']['seed']= random.randint(1, 18446744073709551614)
#             workflow_new[key]=value

#         queue_prompt(workflow_new)
#         print('#运行的函数',workflow_new[input_node[0]])

#         # return (new_prompt)
#         return  {"ui":{"images": []},"result": ([image],['text'],)}

