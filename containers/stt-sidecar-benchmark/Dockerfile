# syntax=docker/dockerfile:1
#
# Purpose:
#   Build the isolated speech-to-text benchmark runtime used to collect live
#   Hemma profile-proof observations.
#
# Relationships:
#   - Built by `benchmark:stt-sidecar-live-observation` with Docker BuildKit.
#   - Provides FFmpeg, faster-whisper, pyannote.audio, Hugging Face Hub, and
#     ROCm-backed Torch for Task 352 evidence collection without changing the
#     main Sir Convert service image.
#

ARG BASE_IMAGE=sir-convert-a-lot-deps-rocm:local

FROM ${BASE_IMAGE} AS stt-sidecar-benchmark

ENV HF_HOME=/cache/huggingface
ENV HF_HUB_CACHE=/cache/huggingface/hub
ENV TRANSFORMERS_CACHE=/cache/huggingface

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,id=sir-convert-a-lot-stt-sidecar-pip,target=/root/.cache/pip \
    python -m pip install --upgrade \
        faster-whisper \
        "huggingface-hub==0.34.4" \
        pyannote.audio
