# 用于定义社交名片

import json,os



def save_to_json(file_path, data):
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f)
    except Exception as e:
            print(e)

def read_from_json(file_path):
    data={}
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
            print(e)
    return data


# read_from_json()
current_path = os.path.abspath(os.path.dirname(__file__))
social_profile_json=os.path.join(current_path,'social_profile.json')
# print('Watcher:',config_json)

def read_social_profile_config():
    config={
         "username":"shadow",
         "profile_id":"ML000",
         "skills":"Design Hacker,Programmer,Architect,Experience Designer".split(",")
    }
    try:
        if os.path.exists(social_profile_json):
            config=read_from_json(social_profile_json)
    except Exception as e:
            print(e)  
    return config

def save_social_profile_config(data):
     save_to_json(social_profile_json,data)


class SocialProfileNode:

    @classmethod
    def INPUT_TYPES(s):
 
        user=read_social_profile_config()

        return {
            "required": {
                "username": ("STRING", {"forceInput": False, "default": user['username']}),
                "profile_id": ("STRING", {"forceInput": False, "default": user['profile_id']}),
                "skills": ("STRING", {"forceInput": False, "multiline": True, "default": ",".join(user['skills'])}),
            },
        }

    # INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("social_profile(json_string)",)
    FUNCTION = "run"
    # OUTPUT_IS_LIST = (False,)
    CATEGORY = "♾️Mixlab/Agent"

    def run(self, username, profile_id, skills):
        
        # 将skills字符串分割为列表
        skills_list = [skill.strip() for skill in skills.split(",")]

        # 创建社交名片的JSON对象
        social_profile = {
            "username": username,
            "profile_id": profile_id,
            "skills": skills_list,
        }

        # 将社交名片转换为JSON字符串
        json_string = json.dumps(social_profile, ensure_ascii=False)

        save_social_profile_config(social_profile)

        # 返回JSON字符串和一个示例值
        return (json_string,)
