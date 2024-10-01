# -*- coding:utf-8 -*-
# @FileName  :sense_voice.py.py
# @Time      :2024/7/18 15:40
# @Author    :lovemefan
# @Email     :lovemefan@outlook.com
import argparse
import logging
import os
import time

import soundfile as sf
from huggingface_hub import snapshot_download

from sensevoice.onnx.sense_voice_ort_session import SenseVoiceInferenceSession
from sensevoice.utils.frontend import WavFrontend
from sensevoice.utils.fsmn_vad import FSMNVad

languages = {"auto": 0, "zh": 3, "en": 4, "yue": 7, "ja": 11, "ko": 12, "nospeech": 13}
formatter = "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
logging.basicConfig(format=formatter, level=logging.INFO)


def main():
    arg_parser = argparse.ArgumentParser(description="Sense Voice")
    arg_parser.add_argument("-a", "--audio_file", required=True, type=str, help="Model")
    download_model_path = os.path.join(os.path.dirname(__file__), "resource")
    arg_parser.add_argument(
        "-dp",
        "--download_path",
        default=download_model_path,
        type=str,
        help="dir path of resource downloaded",
    )
    arg_parser.add_argument("-d", "--device", default=-1, type=int, help="Device")
    arg_parser.add_argument(
        "-n", "--num_threads", default=4, type=int, help="Num threads"
    )
    arg_parser.add_argument(
        "-l",
        "--language",
        choices=languages.keys(),
        default="auto",
        type=str,
        help="Language",
    )
    arg_parser.add_argument("--use_itn", action="store_true", help="Use ITN")
    arg_parser.add_argument(
        "--use_int8", action="store_true", help="Use int8 onnx model"
    )
    args = arg_parser.parse_args()

    if not os.path.exists(download_model_path):
        logging.info(
            "Downloading model from huggingface hub from https://huggingface.co/lovemefan/SenseVoice-onnx"
        )
        logging.info(
            "You can speed up with  `export HF_ENDPOINT=https://hf-mirror.com`"
        )
        snapshot_download(
            repo_id="lovemefan/SenseVoice-onnx", local_dir=download_model_path
        )

    front = WavFrontend(os.path.join(download_model_path, "am.mvn"))

    model = SenseVoiceInferenceSession(
        os.path.join(download_model_path, "embedding.npy"),
        os.path.join(
            download_model_path,
            "sense-voice-encoder-int8.onnx"
            if args.use_int8
            else "sense-voice-encoder.onnx",
        ),
        os.path.join(download_model_path, "chn_jpn_yue_eng_ko_spectok.bpe.model"),
        args.device,
        args.num_threads,
    )
    waveform, _sample_rate = sf.read(
        args.audio_file,
        dtype="float32",
        always_2d=True
    )

    logging.info(f"Audio {args.audio_file} is {len(waveform) / _sample_rate} seconds, {waveform.shape[1]} channel")
    # load vad model
    start = time.time()
    vad = FSMNVad(download_model_path)
    for channel_id, channel_data in enumerate(waveform.T):
        segments = vad.segments_offline(channel_data)
        results = ""
        for part in segments:
            audio_feats = front.get_features(channel_data[part[0] * 16 : part[1] * 16])
            asr_result = model(
                audio_feats[None, ...],
                language=languages[args.language],
                use_itn=args.use_itn,
            )
            logging.info(f"[Channel {channel_id}] [{part[0] / 1000}s - {part[1] / 1000}s] {asr_result}")
        vad.vad.all_reset_detection()
    decoding_time = time.time() - start
    logging.info(f"Decoder audio takes {decoding_time} seconds")
    logging.info(f"The RTF is {decoding_time/(waveform.shape[1] * len(waveform) / _sample_rate)}.")


if __name__ == "__main__":
    main()