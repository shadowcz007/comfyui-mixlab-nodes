## 
In progress.


## Installation

For the easiest install experience, install the [Comfyui Manager](https://github.com/ltdrdata/ComfyUI-Manager) and use that to automate the installation process.
Otherwise, to manually install, simply clone the repo into the custom_nodes directory with this command:
```
git clone https://github.com/shadowcz007/comfyui-mixlab-nodes.git
```
and install the requirements using:
```
.\python_embed\python.exe -s -m pip install -r requirements.txt
```
If you are using a venv, make sure you have it activated before installation and use:
```
pip install -r requirements.txt
```

直接运行：
```
install.bat
```

## Nodes

randomPrompt

![randomPrompt](./assets/randomPrompt.png)

TransparentImage

![TransparentImage](./assets//TransparentImage.png)

Consistency Decoder

[openai发布的新vae模型]( https://github.com/openai/consistencydecoder)

openai vae 模型下载后放model/vae里使用
https://openaipublic.azureedge.net/diff-vae/c9cebd3132dd9c42936d803e33424145a748843c8f716c0814838bdc8a2fe7cb/decoder.pt


<!-- ### Workflow
[Workflow](./workflow.md) -->

### TODO:
- 从模板库里 粘贴workflow进工作区
- ImageFromClipborad:The node implementation to read an image from the clipboard.
- vector https://github.com/GeorgLegato/stable-diffusion-webui-vectorstudio

