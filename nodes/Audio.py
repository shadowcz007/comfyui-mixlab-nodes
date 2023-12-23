



class SpeechRecognition:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { 
                    "upload":("AUDIOINPUTMIX",),   },
                "optional":{
                    "start_by":("INT", {
                        "default": 0, 
                        "min": 0, #Minimum value
                        "max": 2048, #Maximum value
                        "step": 1, #Slider's step
                        "display": "number" # Cosmetic only: display as "number" or "slider"
                    }),
                   
                }
                }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/audio"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = (False,)

    def run(self,upload,start_by):
        return {"ui": {"start_by": [start_by]}, "result": (upload,)}


class SpeechSynthesis:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "♾️Mixlab/audio"

    def run(self, text):
        # print(session_history)
        return {"ui": {"text": text}, "result": (text,)}
    

#
class GamePal:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input_text": ("STRING",{"multiline": True,"default": ""}),
            },
            "optional": {
                 
                "input_num": ("INT",{
                                "default":100, 
                                "min": -1, #Minimum value
                                "max": 0xffffffffffffffff, #Maximum value
                                "step": 1, #Slider's step
                                "display": "slider" # Cosmetic only: display as "number" or "slider"
                                }), 
                "python_code": ("STRING",{"multiline": True,"default": "result= 1 if 'Mixlab' in input_text else 0"}),
            }
        }

    INPUT_IS_LIST = False
    RETURN_TYPES = ("INT",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (False,)

    CATEGORY = "♾️Mixlab/audio"

    def run(self, input_text,input_num,python_code):
        exec(python_code)
        res=None
        try:
            # 可能会引发异常的代码
            res=result
        except:
            # 处理异常的代码
            print('')

        print(res)

        # print(session_history)
        return {"ui": {"text": [input_text],"num":[input_num]}, "result": (res,)}