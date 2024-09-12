
import hydra
from hydra import compose, initialize
from hydra.utils import instantiate
import torch
from loguru import logger
import torchaudio


def load_model(config_name, checkpoint_path, device="cuda"):
    hydra.core.global_hydra.GlobalHydra.instance().clear()
    with initialize(version_base="1.3", config_path="./configs"):
        cfg = compose(config_name=config_name)

    model = instantiate(cfg)
    state_dict = torch.load(
        checkpoint_path,
        map_location=device,
    )
    if "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]

    if any("generator" in k for k in state_dict):
        state_dict = {
            k.replace("generator.", ""): v
            for k, v in state_dict.items()
            if "generator." in k
        }

    result = model.load_state_dict(state_dict, strict=False)
    model.eval()
    model.to(device)

    logger.info(f"Loaded model: {result}")
    return model


def codes2audio(model, indices, device):
    # Restore
    feature_lengths = torch.tensor([indices.shape[1]], device=device)

    fake_audios, _ = model.decode(
        indices=indices[None], feature_lengths=feature_lengths
    )
  
    audio_time = fake_audios.shape[-1] / model.spec_transform.sample_rate

    logger.info(
        f"Generated audio of shape {fake_audios.shape}, equivalent to {audio_time:.2f} seconds from {indices.shape[1]} features, features/second: {indices.shape[1] / audio_time:.2f}"
    )

    # Save audio
    fake_audio = fake_audios[0, 0]

    # to tensor
    waveform = fake_audio.unsqueeze(0)

    sample_rate = model.spec_transform.sample_rate

    audio_content = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}

    return audio_content


def audio2prompt(model, audio_content, device):
    logger.info(f"Processing in-place reconstruction of {audio_content}")

    audio = audio_content['waveform'].squeeze(0)
    sr = audio_content['sample_rate']

    if audio.shape[0] > 1:
        audio = audio.mean(0, keepdim=True)

    audio = torchaudio.functional.resample(
        audio, sr, model.spec_transform.sample_rate
    )

    audios = audio[None].to(device)
    logger.info(
        f"Loaded audio with {audios.shape[2] / model.spec_transform.sample_rate:.2f} seconds"
    )

    # VQ Encoder
    audio_lengths = torch.tensor([audios.shape[2]], device=device, dtype=torch.long)
    indices = model.encode(audios, audio_lengths)[0][0]

    logger.info(f"Generated indices of shape {indices.shape}")

    audio_content = codes2audio(model, indices, device)

    return (audio_content, indices.cpu().numpy(), )


def semantic2audio(model, codes, device):
    logger.info(f"Processing precomputed indices from {codes.shape}")
    indices = torch.from_numpy(codes).to(device).long()
    audio_content = codes2audio(model, indices, device)
    return (audio_content, )