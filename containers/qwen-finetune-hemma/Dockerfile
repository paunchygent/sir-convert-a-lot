# syntax=docker/dockerfile:1
# Experimental Task 100 training image for Qwen3-TTS Swedish fine-tuning on Hemma.

FROM python:3.11-slim-bullseye

ARG TORCH_ROCM_INDEX_URL=https://download.pytorch.org/whl/rocm7.1
ARG TORCH_VERSION=2.10.0+rocm7.1
ARG TORCHAUDIO_VERSION=2.10.0+rocm7.1

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app:/app/scripts/devops/qwen_finetuning_patches
ENV HF_HUB_DISABLE_XET=1

LABEL org.sir_convert_a_lot.runtime_family="qwen_finetune"
LABEL org.sir_convert_a_lot.runtime_backend="qwen3_tts_12hz_1p7b"
LABEL org.sir_convert_a_lot.lifecycle="experimental_training"
LABEL org.sir_convert_a_lot.hemma_deployable="false"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        libsndfile1 \
        sox \
    && rm -rf /var/lib/apt/lists/*

COPY containers/qwen-finetune-hemma/requirements.txt /tmp/task100-requirements.txt

RUN python -m pip install --upgrade pip "setuptools<81" wheel
RUN python -m pip install --index-url "${TORCH_ROCM_INDEX_URL}" \
    "torch==${TORCH_VERSION}" \
    "torchaudio==${TORCHAUDIO_VERSION}"
RUN python -m pip install -r /tmp/task100-requirements.txt
RUN python -m pip uninstall -y hf-xet || true

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/devops /app/scripts/sir_convert_a_lot/devops
COPY scripts/devops/qwen_finetuning_patches /app/scripts/devops/qwen_finetuning_patches

CMD ["python", "-m", "scripts.sir_convert_a_lot.devops.task100_qwen_finetune_smoke_probe", "--help"]
