# syntax=docker/dockerfile:1

FROM python:3.11-slim-bullseye

ARG TORCH_ROCM_INDEX_URL=https://download.pytorch.org/whl/rocm6.2.4
ARG TORCH_VERSION=2.6.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG CHATTERBOX_TTS_VERSION=0.1.6

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app
ENV HF_HUB_DISABLE_XET=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip "setuptools<81" wheel
RUN python -m pip install --index-url "${TORCH_ROCM_INDEX_URL}" \
    "torch==${TORCH_VERSION}" \
    "torchaudio==${TORCHAUDIO_VERSION}"
RUN python -m pip install \
    "fastapi>=0.128.8" \
    "uvicorn[standard]>=0.40.0" \
    "python-multipart>=0.0.22" \
    "httpx>=0.28.1" \
    "pydantic==2.10.6" \
    "chatterbox-tts==${CHATTERBOX_TTS_VERSION}"
RUN python -m pip uninstall -y hf-xet

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/tts_sidecar /app/scripts/sir_convert_a_lot/tts_sidecar

EXPOSE 8094

CMD ["uvicorn", "scripts.sir_convert_a_lot.tts_sidecar.chatterbox_app:app", "--host", "0.0.0.0", "--port", "8094"]
