



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

    CATEGORY = "♾️Mixlab/Audio"

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

    CATEGORY = "♾️Mixlab/Audio"

    def run(self, text):
        # print(session_history)
        return {"ui": {"text": text}, "result": (text,)}
    


class AudioPlayNode:

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "audio": ("AUDIO",),
              }, 
                }
    
    RETURN_TYPES = ()
  
    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/Audio"

    INPUT_IS_LIST = False
    OUTPUT_IS_LIST = ()

    OUTPUT_NODE = True
  
    def run(self,audio):
        # print(audio)
        return {"ui": {"audio":[audio]}}