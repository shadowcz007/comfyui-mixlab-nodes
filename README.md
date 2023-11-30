## 
In progress.
！！
![screenshare](./assets/screenshare.png)


### ScreenShareNode & FloatingVideoNode
> Now comfyui supports capturing screen pixel streams from any software and can be used for LCM-Lora integration. Let's get started with implementation and design! 💻🌐

https://github.com/shadowcz007/comfyui-mixlab-nodes/assets/12645064/e7e77f90-e43e-410a-ab3a-1952b7b4e7da


<!-- [ScreenShareNode](./workflow/2-screeshare.json) -->
[ScreenShareNode & FloatingVideoNode](./workflow/3-FloatVideo-workflow.json)

!! Please use the address with HTTPS (https://127.0.0.1).

## Installation

manually install, simply clone the repo into the custom_nodes directory with this command:

```
cd ComfyUI/custom_nodes

git clone https://github.com/shadowcz007/comfyui-mixlab-nodes.git

```

Install the requirements:

run directly:
```
cd ComfyUI_Mixlab
install.bat
```

or install the requirements using:
```
../../../python_embeded/python.exe -s -m pip install -r requirements.txt
```

If you are using a venv, make sure you have it activated before installation and use:
```
pip3 install -r requirements.txt
```



## Nodes

![main](./assets/all.png)
![main2](./assets/detect-face-all.png)

[workflow-1](./workflow/1-workflow.json)

> randomPrompt

![randomPrompt](./assets/randomPrompt.png)

> TransparentImage

![TransparentImage](./assets/TransparentImage.png)



>LoadImagesFromLocal

![watch](./assets/load-watch.png)

[workflow-4](./workflow/4-loadfromlocal-watcher-workflow.json)

> Consistency Decoder

[openai Consistency Decoder]( https://github.com/openai/consistencydecoder)

![Consistency](./assets/consistency.png)
After downloading the OpenAI VAE model, place it in the "model/vae" directory for use.
https://openaipublic.azureedge.net/diff-vae/c9cebd3132dd9c42936d803e33424145a748843c8f716c0814838bdc8a2fe7cb/decoder.pt


> FeatheredMask、SmoothMask

Add edges to an image.

![FeatheredMask](./assets/FlVou_Y6kaGWYoEj1Tn0aTd4AjMI.jpg)


### Models
[Download CLIPSeg](https://huggingface.co/CIDAS/clipseg-rd64-refined/tree/main), move to : model/clipseg

<!-- ### Workflow
[Workflow](./workflow.md) -->

#### Thanks:
[ComfyUI-CLIPSeg](https://github.com/biegert/ComfyUI-CLIPSeg/tree/main)


### TODO:
- vector https://github.com/GeorgLegato/stable-diffusion-webui-vectorstudio

