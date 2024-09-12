
import torch
from .models.text2semantic.llama import BaseTransformer, NaiveTransformer, DualARTransformer
from .tools.llama.generate import decode_one_token_ar, decode_one_token_naive, generate_long
import numpy as np
import time
from typing import Union
from loguru import logger
from pathlib import Path
from typing import Optional

def load_model(checkpoint_path, device, precision, compile=False):
    model: Union[NaiveTransformer, DualARTransformer] = BaseTransformer.from_pretrained(
        checkpoint_path, load_weights=True
    )

    model = model.to(device=device, dtype=precision)
    logger.info(f"Restored model from checkpoint")

    if isinstance(model, DualARTransformer):
        decode_one_token = decode_one_token_ar
        logger.info("Using DualARTransformer")
    else:
        decode_one_token = decode_one_token_naive
        logger.info("Using NaiveTransformer")

    if compile:
        logger.info("Compiling function...")
        decode_one_token = torch.compile(
            decode_one_token, mode="reduce-overhead", fullgraph=True
        )

    return model.eval(), decode_one_token


def prompt2semantic(
    model: DualARTransformer,
    decode_one_token: callable,
    text: str,
    prompt_text: Optional[list[str]],
    prompt_tokens: Optional[list[np.ndarray]],
    max_new_tokens: int,
    top_p: float,
    repetition_penalty: float,
    temperature: float,
    device: str,
    compile: bool,
    seed: int,
    iterative_prompt: bool,
    chunk_length: int,
):

    if prompt_text is not None and len(prompt_text) != len(prompt_tokens):
        raise ValueError(
            f"Number of prompt text ({len(prompt_text)}) and prompt tokens ({len(prompt_tokens)}) should be the same"
        )
    
    if torch.cuda.is_available():
        torch.cuda.synchronize()

    if prompt_tokens is not None:
        prompt_tokens = [torch.from_numpy(pt).to(device) for pt in prompt_tokens]

    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)

    generator = generate_long(
        model=model,
        device=device,
        decode_one_token=decode_one_token,
        text=text,
        num_samples=1,
        max_new_tokens=max_new_tokens,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        temperature=temperature,
        compile=compile,
        iterative_prompt=iterative_prompt,
        chunk_length=chunk_length,
        prompt_text=prompt_text,
        prompt_tokens=prompt_tokens,
    )

    idx = 0
    all_codes = []
    codes = []

    for response in generator:
        if response.action == "sample":
            codes.append(response.codes)
            logger.info(f"Sampled text: {response.text}")
        elif response.action == "next":
            if codes:
                all_codes.append(torch.cat(codes, dim=1).cpu().numpy())
                logger.info(f"Saved codes to codes_{idx}.npy")
            logger.info(f"Next sample")
            codes = []
            idx += 1
        else:
            logger.error(f"Error: {response}")

    return all_codes