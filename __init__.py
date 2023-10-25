#
import os
import subprocess
import importlib.util
import sys

python = sys.executable


def is_installed(package, package_overwrite=None):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        pass

    package = package_overwrite or package

    if spec is None:
        print(f"Installing {package}...")
        # 清华源 -i https://pypi.tuna.tsinghua.edu.cn/simple
        command = f'"{python}" -m pip install {package}'
  
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ)

        if result.returncode != 0:
            print(f"Couldn't install\nCommand: {command}\nError code: {result.returncode}")

# 导入节点
from .PromptNode import RandomPrompt,RunWorkflow
from .ImageNode import TransparentImage,LoadImagesFromPath,SplitLongMask,ImagesCrop
# from .ModelNode import KandinskyModel,KandinskyModelLoad

# 要导出的所有节点及其名称的字典
# 注意：名称应全局唯一
NODE_CLASS_MAPPINGS = {
    "RandomPrompt":RandomPrompt,
    "TransparentImage":TransparentImage,
    "LoadImagesFromPath":LoadImagesFromPath,
    "SplitLongMask":SplitLongMask,
    "ImagesCrop":ImagesCrop,
    "RunWorkflow":RunWorkflow
    # "KandinskyModelLoad":KandinskyModelLoad,
    # "KandinskyModel":KandinskyModel
}

# 一个包含节点友好/可读的标题的字典
NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomPrompt": "Random Prompt #Example Node",
    "SplitLongMask":"Splitting a long image into sections"
}

# web ui的节点功能
WEB_DIRECTORY = "./web"

print('--------------')
print('\033[34mMixlab Custom Nodes: \033[92mLoaded\033[0m')
print('--------------')