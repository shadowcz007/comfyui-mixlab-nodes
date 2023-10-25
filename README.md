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


### Workflow
[Workflow](./workflow.md)

### TODO:
- ImageFromClipborad:The node implementation to read an image from the clipboard.
- vector https://github.com/GeorgLegato/stable-diffusion-webui-vectorstudio

