# 用于定义社交名片

import json,os
import folder_paths

def save_to_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
            print(e)

def read_from_json(file_path):
    data=None
    try:
        with open(file_path, 'w') as f:
            data = json.load(f)
    except Exception as e:
            print(e)
            return None
    return data


default_agent={
                    "username":"shadow",
                    "profile_id":"ML000",
                    "skills":"Design Hacker,Programmer,Architect,Experience Designer".split(",")
                }

def create_default_file(agent_dir):
    fp=os.path.join(agent_dir,'shadow.json')
    if not os.path.exists(fp):
        save_to_json(fp,default_agent)

def get_social_profile_dir():
    try:
        return folder_paths.get_folder_paths('agent')[0]
    except:
        agent_dir=os.path.join(folder_paths.models_dir, "agent")
        if not os.path.exists(agent_dir):
            os.makedirs(agent_dir, exist_ok=True)
            create_default_file(agent_dir)
        return agent_dir

def list_all_json_files(directory_path):
    json_files = []
    
    try:
        for filename in os.listdir(directory_path):
            if filename.endswith('.json'):
                json_files.append(filename)
                
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return json_files


def read_social_profiles():
    agent_dir=get_social_profile_dir()
    files=list_all_json_files(agent_dir)
    if len(files)==0:
        create_default_file(agent_dir)
    files=list_all_json_files(agent_dir)
    return files

def save_social_profile_config(agent_dir,file_name,data):
     save_to_json(os.path.join(agent_dir,file_name),data)



agent_dir=get_social_profile_dir()
# print('Watcher:',config_json)


class NewSocialProfileNode:

    @classmethod
    def INPUT_TYPES(s):
 
        user=default_agent

        return {
            "required": {
                "username": ("STRING", {"forceInput": False, "default": user['username']}),
                "profile_id": ("STRING", {"forceInput": False, "default": user['profile_id']}),
                "skills": ("STRING", {"forceInput": False, "multiline": True, "default": ",".join(user['skills'])}),
                "file_name": ("STRING", {"forceInput": False, "default": "agent"}),
            },
        }

    # INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("social_profile(json_string)",)
    FUNCTION = "run"
    # OUTPUT_IS_LIST = (False,)
    CATEGORY = "♾️Mixlab/Agent"

    def run(self, username, profile_id, skills,file_name):
        
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

        save_social_profile_config(agent_dir,file_name+'.json',social_profile)

        # 返回JSON字符串和一个示例值
        return (json_string,)


class LoadSocialProfileNode:

    @classmethod
    def INPUT_TYPES(s):
        files=read_social_profiles()
        return {
            "required": {
                "file_name": ( files, 
                    {"default": files[0]}),
            },
        }

    # INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("social_profile(json_string)",)
    FUNCTION = "run"
    # OUTPUT_IS_LIST = (False,)
    CATEGORY = "♾️Mixlab/Agent"

    def run(self,file_name):
        # print("#read_from_json",os.path.join(agent_dir,file_name))
        social_profile=read_from_json(os.path.join(agent_dir,file_name))

        if social_profile==None:
            social_profile=default_agent

        social_profile['file_name']=file_name

        # 将社交名片转换为JSON字符串
        json_string = json.dumps(social_profile, ensure_ascii=False)

        # 返回JSON字符串和一个示例值
        return (json_string,)
