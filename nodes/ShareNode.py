
import urllib.parse


# 分享到微博
class ShareToWeibo:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "title":("STRING",{"multiline": True,"default": "","dynamicPrompts": False}),
                "pic_url":("STRING",{"multiline": False,"default": "","dynamicPrompts": False}),
                "url":("STRING",{"multiline": False,"default": "","dynamicPrompts": False}),
            }
        }

    RETURN_TYPES = ()
    # RETURN_NAMES = ("number",)

    FUNCTION = "run"

    CATEGORY = "♾️Mixlab/share"

    INPUT_IS_LIST = False
    OUTPUT_NODE = True
    # OUTPUT_IS_LIST = ()

    def run(self, title, pic_url, url):
        encoded_title = urllib.parse.quote(title)
        encoded_pic_url = urllib.parse.quote(pic_url)
        encoded_url = urllib.parse.quote(url)
        url = "https://service.weibo.com/share/share.php?title={}&pic={}&url={}".format(encoded_title,encoded_pic_url,encoded_url)
        print(url)
        return {"ui": {"url": [url]}, "result": ()}
    


