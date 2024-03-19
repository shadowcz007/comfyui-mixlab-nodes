import comfy
import torch

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

