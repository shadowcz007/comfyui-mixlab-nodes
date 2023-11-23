## 
In progress.
！！
> Now comfyui supports capturing screen pixel streams from any software and can be used for LCM-Lora integration. Let's get started with implementation and design! 💻🌐

https://github.com/shadowcz007/comfyui-mixlab-nodes/assets/12645064/3167aed0-cea0-41f2-9075-b05e0ed08536


## Installation

For the easiest install experience, install the [Comfyui Manager](https://github.com/ltdrdata/ComfyUI-Manager) and use that to automate the installation process.
Otherwise, to manually install, simply clone the repo into the custom_nodes directory with this command:
```
git clone https://github.com/shadowcz007/comfyui-mixlab-nodes.git
```
and install the requirements using:
```
.\python_embeded\python.exe -s -m pip install -r requirements.txt
```
If you are using a venv, make sure you have it activated before installation and use:
```
pip install -r requirements.txt
```

Run directly:
```
install.bat
```

## Nodes

> randomPrompt

![randomPrompt](./assets/randomPrompt.png)

> TransparentImage

![TransparentImage](./assets/TransparentImage.png)

> Consistency Decoder

[openai Consistency Decoder]( https://github.com/openai/consistencydecoder)

![Consistency](./assets/consistency.png)
After downloading the OpenAI VAE model, place it in the "model/vae" directory for use.
https://openaipublic.azureedge.net/diff-vae/c9cebd3132dd9c42936d803e33424145a748843c8f716c0814838bdc8a2fe7cb/decoder.pt


> FeatheredMask、SmoothMask

Add edges to an image.

![FeatheredMask](./assets/FlVou_Y6kaGWYoEj1Tn0aTd4AjMI.jpg)



<!-- ### Workflow
[Workflow](./workflow.md) -->

### TODO:
- Copy and paste the workflow from the template library into the workspace.
- ImageFromClipborad:The node implementation to read an image from the clipboard.
- vector https://github.com/GeorgLegato/stable-diffusion-webui-vectorstudio

