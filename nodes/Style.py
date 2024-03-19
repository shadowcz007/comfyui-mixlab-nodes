import comfy
import torch

from dataclasses import dataclass
import torch.nn as nn
from comfy.model_patcher import ModelPatcher
import comfy.ops
from typing import Union
import comfy.sample
import latent_preview
import comfy.utils

T = torch.Tensor


from .VisualStylePrompting.attention_functions import VisualStyleProcessor

class ApplyVisualStylePrompting:

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "reference_image": ("IMAGE",),
                "reference_image_text": ("STRING", {"multiline": True}),
                "model": ("MODEL",),
                "clip": ("CLIP", ),
                "vae": ("VAE", ),
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING", ),
                "enabled": ("BOOLEAN", {"default": True}),
                "denoise": ("FLOAT", {"default": 1., "min": 0., "max": 1., "step": 1e-2}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4096,"step":2})
            }
        }

    RETURN_TYPES = ("MODEL", "CONDITIONING","CONDITIONING", "LATENT")
    RETURN_NAMES = ("model", "positive", "negative", "latents")
    
    CATEGORY = "♾️Mixlab/Style"

    FUNCTION = "run"

    def run(
        self, 
        reference_image, 
        reference_image_text,
        model: comfy.model_patcher.ModelPatcher, 
        clip,
        vae,
        positive,
        negative, 
        enabled,
        denoise,
        batch_size=1
    ):
        
        tokens = clip.tokenize(reference_image_text)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        reference_image_prompt=[[cond, {"pooled_output": pooled}]]
   
        reference_image = reference_image.repeat(((batch_size+1)//2, 1,1,1))

        self.model = model
        reference_latent = vae.encode(reference_image[:,:,:,:3])
        
        for n, m in model.model.diffusion_model.named_modules():
            if m.__class__.__name__  == "CrossAttention":
                processor = VisualStyleProcessor(m, enabled=enabled)
                setattr(m, 'forward', processor.visual_style_forward)

        conditioning_prompt = reference_image_prompt + positive
        negative_prompt = negative * 2 

        latents = torch.zeros_like(reference_latent) 
        latents = torch.cat([latents] * 2)

        if denoise < 1.0:
            latents[::1] = reference_latent[:1]
        else:
            latents[::2] = reference_latent

        denoise_mask = torch.ones_like(latents)[:, :1, ...] * denoise

        denoise_mask[0] = 0.

        return (model, conditioning_prompt, negative_prompt, {"samples": latents, "noise_mask": denoise_mask})    





def exists(val):
    return val is not None

def default(val, d):
    if exists(val):
        return val
    return d


class StyleAlignedArgs:
    def __init__(self, share_attn: str) -> None:
        self.adain_keys = "k" in share_attn
        self.adain_values = "v" in share_attn
        self.adain_queries = "q" in share_attn

    share_attention: bool = True
    adain_queries: bool = True
    adain_keys: bool = True
    adain_values: bool = True


def expand_first(
    feat: T,
    scale=1.0,
) -> T:
    """
    Expand the first element so it has the same shape as the rest of the batch.
    """
    b = feat.shape[0]
    feat_style = torch.stack((feat[0], feat[b // 2])).unsqueeze(1)
    if scale == 1:
        feat_style = feat_style.expand(2, b // 2, *feat.shape[1:])
    else:
        feat_style = feat_style.repeat(1, b // 2, 1, 1, 1)
        feat_style = torch.cat([feat_style[:, :1], scale * feat_style[:, 1:]], dim=1)
    return feat_style.reshape(*feat.shape)


def concat_first(feat: T, dim=2, scale=1.0) -> T:
    """
    concat the the feature and the style feature expanded above
    """
    feat_style = expand_first(feat, scale=scale)
    return torch.cat((feat, feat_style), dim=dim)


def calc_mean_std(feat, eps: float = 1e-5) -> "tuple[T, T]":
    feat_std = (feat.var(dim=-2, keepdims=True) + eps).sqrt()
    feat_mean = feat.mean(dim=-2, keepdims=True)
    return feat_mean, feat_std

def adain(feat: T) -> T:
    feat_mean, feat_std = calc_mean_std(feat)
    feat_style_mean = expand_first(feat_mean)
    feat_style_std = expand_first(feat_std)
    feat = (feat - feat_mean) / feat_std
    feat = feat * feat_style_std + feat_style_mean
    return feat

class SharedAttentionProcessor:
    def __init__(self, args: StyleAlignedArgs, scale: float):
        self.args = args
        self.scale = scale

    def __call__(self, q, k, v, extra_options):
        if self.args.adain_queries:
            q = adain(q)
        if self.args.adain_keys:
            k = adain(k)
        if self.args.adain_values:
            v = adain(v)
        if self.args.share_attention:
            k = concat_first(k, -2, scale=self.scale)
            v = concat_first(v, -2)

        return q, k, v


def get_norm_layers(
    layer: nn.Module,
    norm_layers_: "dict[str, list[Union[nn.GroupNorm, nn.LayerNorm]]]",
    share_layer_norm: bool,
    share_group_norm: bool,
):
    if isinstance(layer, nn.LayerNorm) and share_layer_norm:
        norm_layers_["layer"].append(layer)
    if isinstance(layer, nn.GroupNorm) and share_group_norm:
        norm_layers_["group"].append(layer)
    else:
        for child_layer in layer.children():
            get_norm_layers(
                child_layer, norm_layers_, share_layer_norm, share_group_norm
            )


def register_norm_forward(
    norm_layer: Union[nn.GroupNorm, nn.LayerNorm],
) -> Union[nn.GroupNorm, nn.LayerNorm]:
    if not hasattr(norm_layer, "orig_forward"):
        setattr(norm_layer, "orig_forward", norm_layer.forward)
    orig_forward = norm_layer.orig_forward

    def forward_(hidden_states: T) -> T:
        n = hidden_states.shape[-2]
        hidden_states = concat_first(hidden_states, dim=-2)
        hidden_states = orig_forward(hidden_states)  # type: ignore
        return hidden_states[..., :n, :]

    norm_layer.forward = forward_  # type: ignore
    return norm_layer


def register_shared_norm(
    model: ModelPatcher,
    share_group_norm: bool = True,
    share_layer_norm: bool = True,
):
    norm_layers = {"group": [], "layer": []}
    get_norm_layers(model.model, norm_layers, share_layer_norm, share_group_norm)
    print(
        f"Patching {len(norm_layers['group'])} group norms, {len(norm_layers['layer'])} layer norms."
    )
    return [register_norm_forward(layer) for layer in norm_layers["group"]] + [
        register_norm_forward(layer) for layer in norm_layers["layer"]
    ]


SHARE_NORM_OPTIONS = ["both", "group", "layer", "disabled"]
SHARE_ATTN_OPTIONS = ["q+k", "q+k+v", "disabled"]

class StyleAlignedSampleReferenceLatents:
    @classmethod
    def INPUT_TYPES(s):
        return {"required":
                    { 
                    "reference_image": ("IMAGE",),
                    "positive": ("CONDITIONING",),
                    "negative": ("CONDITIONING", ),
                    "model": ("MODEL",),
                    "vae": ("VAE", ),
                    "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                    "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                    "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step":0.1, "round": 0.01}),

                    "scheduler": (comfy.samplers.KSampler.SCHEDULERS.reverse(), ), 
                    "denoise": ("FLOAT", {"default": 1, "min": 0.0, "max": 1.0, "step": 0.01}),
                    
                     }
                }

    RETURN_TYPES = ("STEP_LATENTS","LATENT")
    RETURN_NAMES = ("ref_latents", "noised_output")

    FUNCTION = "run"

    # CATEGORY = "style_aligned"
    CATEGORY = "♾️Mixlab/Style"

    def run(self, reference_image, positive, negative, model, vae, seed, steps, cfg,scheduler,denoise):

        # TODO noise_mask?
        def vae_encode_crop_pixels(pixels):
            x = (pixels.shape[1] // 8) * 8
            y = (pixels.shape[2] // 8) * 8
            if pixels.shape[1] != x or pixels.shape[2] != y:
                x_offset = (pixels.shape[1] % 8) // 2
                y_offset = (pixels.shape[2] % 8) // 2
                pixels = pixels[:, x_offset:x + x_offset, y_offset:y + y_offset, :]
            return pixels

        pixels=vae_encode_crop_pixels(reference_image)
        t = vae.encode(pixels[:,:,:,:3])
        latent_image =  {"samples":t}

        noise_seed=seed

        sampler_name="ddim"
        
        sampler = comfy.samplers.sampler_object(sampler_name)

        total_steps = steps
        if denoise < 1.0:
            total_steps = int(steps/denoise)

        comfy.model_management.load_models_gpu([model])
        sigmas = comfy.samplers.calculate_sigmas_scheduler(model.model, scheduler, total_steps).cpu()
        sigmas = sigmas[-(steps + 1):]

        sigmas = sigmas.flip(0)
        if sigmas[0] == 0:
            sigmas[0] = 0.0001

        latent = latent_image
        latent_image = latent["samples"]
        noise = torch.zeros(latent_image.size(), dtype=latent_image.dtype, layout=latent_image.layout, device="cpu")

    
        noise_mask = None
        if "noise_mask" in latent:
            noise_mask = latent["noise_mask"]

        ref_latents = []
        def callback(step: int, x0: T, x: T, steps: int):
            ref_latents.insert(0, x[0])
        
        disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
        samples = comfy.sample.sample_custom(model, noise, cfg, sampler, sigmas, positive, negative, latent_image, noise_mask=noise_mask, callback=callback, disable_pbar=disable_pbar, seed=noise_seed)

        out = latent.copy()
        out["samples"] = samples
        out_noised = out

        ref_latents = torch.stack(ref_latents)

        return (ref_latents, out_noised)

class StyleAlignedReferenceSampler:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {

                "ref_latents": ("STEP_LATENTS",),
                "reference_image_text": ("STRING", {"multiline": True}),
                "model": ("MODEL",),
                "clip": ("CLIP", ),

                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),

                "share_norm": (SHARE_NORM_OPTIONS,),
                "share_attn": (SHARE_ATTN_OPTIONS,),
                "scale": ("FLOAT", {"default": 1, "min": 0, "max": 2.0, "step": 0.01}),
                "batch_size": ("INT", {"default": 2, "min": 1, "max": 8, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0, "step":0.1, "round": 0.01}),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, ), 
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("output", "denoised_output")
    FUNCTION = "patch"
    # CATEGORY = "style_aligned"
    CATEGORY = "♾️Mixlab/Style"
    def patch(
        self,
        ref_latents,
        reference_image_text,
        model,
        clip,
        positive,
        negative,
        share_norm,
        share_attn,
        scale,
        batch_size,
        seed,steps,cfg,scheduler,denoise

    ) -> "tuple[dict, dict]":
        
        m = model.clone()

        # ref_latents = vae.encode(reference_image[:,:,:,:3])

        tokens = clip.tokenize(reference_image_text)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        ref_positive=[[cond, {"pooled_output": pooled}]]

        noise_seed=seed


        total_steps = steps
        if denoise < 1.0:
            total_steps = int(steps/denoise)

        # comfy.model_management.load_models_gpu([model])
        sigmas = comfy.samplers.calculate_sigmas_scheduler(model.model, scheduler, total_steps).cpu()
        sigmas = sigmas[-(steps + 1):]

        sampler_name="ddim"
        
        sampler = comfy.samplers.sampler_object(sampler_name)

        args = StyleAlignedArgs(share_attn)

        # Concat batch with style latent
        style_latent_tensor = ref_latents[0].unsqueeze(0)
        height, width = style_latent_tensor.shape[-2:]
        latent_t = torch.zeros(
            [batch_size, 4, height, width], device=ref_latents.device
        )
        latent = {"samples": latent_t}
        noise = comfy.sample.prepare_noise(latent_t, noise_seed)

        latent_t = torch.cat((style_latent_tensor, latent_t), dim=0)
        ref_noise = torch.zeros_like(noise[0]).unsqueeze(0)
        noise = torch.cat((ref_noise, noise), dim=0)

        x0_output = {}
        preview_callback = latent_preview.prepare_callback(m, sigmas.shape[-1] - 1, x0_output)

        # Replace first latent with the corresponding reference latent after each step
        def callback(step: int, x0: T, x: T, steps: int):
            preview_callback(step, x0, x, steps)
            if (step + 1 < steps):
                # 当ref_latents的step不够时
                if step+1>len(ref_latents)-1:
                    step=len(ref_latents)-2
                
                x[0] = ref_latents[step+1]
                x0[0] = ref_latents[step+1]

        # Register shared norms
        share_group_norm = share_norm in ["group", "both"]
        share_layer_norm = share_norm in ["layer", "both"]
        register_shared_norm(m, share_group_norm, share_layer_norm)

        # Patch cross attn
        m.set_model_attn1_patch(SharedAttentionProcessor(args, scale))

        # Add reference conditioning to batch 
        batched_condition = []
        for i,condition in enumerate(positive):
            additional = condition[1].copy()
            batch_with_reference = torch.cat([ref_positive[i][0], condition[0].repeat([batch_size] + [1] * len(condition[0].shape[1:]))], dim=0)
            if 'pooled_output' in additional and 'pooled_output' in ref_positive[i][1]:
                # combine pooled output
                pooled_output = torch.cat([ref_positive[i][1]['pooled_output'], additional['pooled_output'].repeat([batch_size] 
                    + [1] * len(additional['pooled_output'].shape[1:]))], dim=0)
                additional['pooled_output'] = pooled_output
            if 'control' in additional:
                if 'control' in ref_positive[i][1]:
                    # combine control conditioning
                    control_hint = torch.cat([ref_positive[i][1]['control'].cond_hint_original, additional['control'].cond_hint_original.repeat([batch_size] 
                        + [1] * len(additional['control'].cond_hint_original.shape[1:]))], dim=0)
                    cloned_controlnet = additional['control'].copy()
                    cloned_controlnet.set_cond_hint(control_hint, strength=additional['control'].strength, timestep_percent_range=additional['control'].timestep_percent_range)
                    additional['control'] = cloned_controlnet
                else:
                    # add zeros for first in batch
                    control_hint = torch.cat([torch.zeros_like(additional['control'].cond_hint_original), additional['control'].cond_hint_original.repeat([batch_size] 
                        + [1] * len(additional['control'].cond_hint_original.shape[1:]))], dim=0)
                    cloned_controlnet = additional['control'].copy()
                    cloned_controlnet.set_cond_hint(control_hint, strength=additional['control'].strength, timestep_percent_range=additional['control'].timestep_percent_range)
                    additional['control'] = cloned_controlnet
            batched_condition.append([batch_with_reference, additional])

        disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
        samples = comfy.sample.sample_custom(
            m,
            noise,
            cfg,
            sampler,
            sigmas,
            batched_condition,
            negative,
            latent_t,
            callback=callback,
            disable_pbar=disable_pbar,
            seed=noise_seed,
        )

        # remove reference image
        samples = samples[1:]

        out = latent.copy()
        out["samples"] = samples
        if "x0" in x0_output:
            out_denoised = latent.copy()
            x0 = x0_output["x0"][1:]
            out_denoised["samples"] = m.model.process_latent_out(x0.cpu())
        else:
            out_denoised = out
        return (out, out_denoised)


class StyleAlignedBatchAlign:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "share_norm": (SHARE_NORM_OPTIONS,),
                "share_attn": (SHARE_ATTN_OPTIONS,),
                "scale": ("FLOAT", {"default": 1, "min": 0, "max": 1.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch"
    # CATEGORY = "style_aligned"
    CATEGORY = "♾️Mixlab/Style"
    def patch(
        self,
        model: ModelPatcher,
        share_norm: str,
        share_attn: str,
        scale: float,
    ):
        m = model.clone()
        share_group_norm = share_norm in ["group", "both"]
        share_layer_norm = share_norm in ["layer", "both"]
        register_shared_norm(model, share_group_norm, share_layer_norm)
        args = StyleAlignedArgs(share_attn)
        m.set_model_attn1_patch(SharedAttentionProcessor(args, scale))
        return (m,)


