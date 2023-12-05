# https://github.com/openai/consistencydecoder/blob/main/consistencydecoder/__init__.py

import folder_paths
from comfy import model_management

import math
import torch
import numpy as np
from PIL import Image 


class ConsistencyDecoderWrapper:
    def __init__(self, decoder):
        self.decoder = decoder
    def decode(self, x):
        return self.decoder(x)

def _extract_into_tensor(arr, timesteps, broadcast_shape):
    
    # from: https://github.com/openai/guided-diffusion/blob/22e0df8183507e13a7813f8d38d51b072ca1e67c/guided_diffusion/gaussian_diffusion.py#L895    """
    res = arr[timesteps].float()
    dims_to_append = len(broadcast_shape) - len(res.shape)
    return res[(...,) + (None,) * dims_to_append]


def betas_for_alpha_bar(num_diffusion_timesteps, alpha_bar, max_beta=0.999):
    # from: https://github.com/openai/guided-diffusion/blob/22e0df8183507e13a7813f8d38d51b072ca1e67c/guided_diffusion/gaussian_diffusion.py#L45
    betas = []
    for i in range(num_diffusion_timesteps):
        t1 = i / num_diffusion_timesteps
        t2 = (i + 1) / num_diffusion_timesteps
        betas.append(min(1 - alpha_bar(t2) / alpha_bar(t1), max_beta))
    return torch.tensor(betas)

class ConsistencyDecoder:
    def __init__(self, device="cuda:0", download_target=""):
        self.n_distilled_steps = 64
        # download_target = _download("https://openaipublic.azureedge.net/diff-vae/c9cebd3132dd9c42936d803e33424145a748843c8f716c0814838bdc8a2fe7cb/decoder.pt", download_root)
        self.ckpt = torch.jit.load(download_target).to(device)
        self.device = device 
        sigma_data = 0.5
        betas = betas_for_alpha_bar(
            1024, lambda t: math.cos((t + 0.008) / 1.008 * math.pi / 2) ** 2
        ).to(device)
        alphas = 1.0 - betas
        alphas_cumprod = torch.cumprod(alphas, dim=0)
        self.sqrt_alphas_cumprod = torch.sqrt(alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = torch.sqrt(1.0 - alphas_cumprod)
        sqrt_recip_alphas_cumprod = torch.sqrt(1.0 / alphas_cumprod)
        sigmas = torch.sqrt(1.0 / alphas_cumprod - 1)
        self.c_skip = (
            sqrt_recip_alphas_cumprod
            * sigma_data**2
            / (sigmas**2 + sigma_data**2)
        )
        self.c_out = sigmas * sigma_data / (sigmas**2 + sigma_data**2) ** 0.5
        self.c_in = sqrt_recip_alphas_cumprod / (sigmas**2 + sigma_data**2) ** 0.5

    @staticmethod
    def round_timesteps(
        timesteps, total_timesteps, n_distilled_steps, truncate_start=True
    ):
        with torch.no_grad():
            space = torch.div(total_timesteps, n_distilled_steps, rounding_mode="floor")
            rounded_timesteps = (
                torch.div(timesteps, space, rounding_mode="floor") + 1
            ) * space
            if truncate_start:
                rounded_timesteps[rounded_timesteps == total_timesteps] -= space
            else:
                rounded_timesteps[rounded_timesteps == total_timesteps] -= space
                rounded_timesteps[rounded_timesteps == 0] += space
            return rounded_timesteps

    @staticmethod
    def ldm_transform_latent(z, extra_scale_factor=1):
        channel_means = [0.38862467, 0.02253063, 0.07381133, -0.0171294]
        channel_stds = [0.9654121, 1.0440036, 0.76147926, 0.77022034]

        if len(z.shape) != 4:
            raise ValueError()

        z = z * 0.18215
        channels = [z[:, i] for i in range(z.shape[1])]

        channels = [
            extra_scale_factor * (c - channel_means[i]) / channel_stds[i]
            for i, c in enumerate(channels)
        ]
        return torch.stack(channels, dim=1)

    @torch.no_grad()
    def __call__(
        self,
        features: torch.Tensor,
        schedule=[1.0, 0.5],
    ):
        features = self.ldm_transform_latent(features)
  
        ts = self.round_timesteps(
            torch.arange(0, 1024),
            1024,
            self.n_distilled_steps,
            truncate_start=False,
        )
        shape = (
            features.size(0),
            3,
            8 * features.size(2),
            8 * features.size(3),
        )
        
        x_start = torch.zeros(shape, device=features.device, dtype=features.dtype)
        schedule_timesteps = [int((1024 - 1) * s) for s in schedule]
        for i in schedule_timesteps:
            t = ts[i].item()
            t_ = torch.tensor([t] * features.shape[0]).to(self.device)
            noise = torch.randn_like(x_start)
            
            x_start = (
                _extract_into_tensor(self.sqrt_alphas_cumprod, t_, x_start.shape)
                * x_start
                + _extract_into_tensor(
                    self.sqrt_one_minus_alphas_cumprod, t_, x_start.shape
                )
                * noise
            )
            c_in = _extract_into_tensor(self.c_in, t_, x_start.shape)
            model_output = self.ckpt(c_in * x_start, t_, features=features)
            B, C = x_start.shape[:2]
            model_output, _ = torch.split(model_output, C, dim=1)
            pred_xstart = (
                _extract_into_tensor(self.c_out, t_, x_start.shape) * model_output
                + _extract_into_tensor(self.c_skip, t_, x_start.shape) * x_start
            ).clamp(-1, 1)
            x_start = pred_xstart
        return x_start



class VAELoader:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "vae_name": (folder_paths.get_filename_list("vae"), )}}
    RETURN_TYPES = ("VAE",)
    FUNCTION = "load_vae"

    CATEGORY = "♾️Mixlab/ConsistencyDecoder"

    #TODO: scale factor?
    def load_vae(self, vae_name):
        vae_path = folder_paths.get_full_path("vae", vae_name)
        device = 'cuda:0'
        # print('device',device)
        consistencyDecoder = ConsistencyDecoder(device=device,
                                 download_target=vae_path) # Model size: 2.49 GB
        vae = ConsistencyDecoderWrapper(consistencyDecoder)
        return (vae,)
    

class VAEDecode:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "samples": ("LATENT", ), "vae": ("VAE", )}}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "decode"

    CATEGORY = "♾️Mixlab/ConsistencyDecoder"

    def decode(self, vae, samples):
        image = vae.decode(samples["samples"].to("cuda:0"))
        image = image[0].cpu().numpy()
        image = (image + 1.0) * 127.5
        image = image.clip(0, 255).astype(np.uint8)
        image = Image.fromarray(image.transpose(1, 2, 0))
        image = image.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        return (image, )