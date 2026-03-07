# syntax=docker/dockerfile:1

FROM python:3.11-slim-bullseye

ARG TORCH_ROCM_INDEX_URL=https://download.pytorch.org/whl/rocm7.1
ARG TORCH_VERSION=2.10.0+rocm7.1
ARG TORCHAUDIO_VERSION=2.10.0+rocm7.1
ARG CHATTERBOX_TTS_VERSION=0.1.6

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app
ENV HF_HUB_DISABLE_XET=1
ENV PKUSEG_HOME=/root/.pkuseg

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
    "numpy>=1.24.0,<1.26.0" \
    "librosa==0.11.0" \
    "s3tokenizer" \
    "transformers==4.46.3" \
    "diffusers==0.29.0" \
    "resemble-perth==1.0.1" \
    "conformer==0.3.2" \
    "safetensors==0.5.3" \
    "spacy-pkuseg" \
    "pykakasi==2.3.0" \
    "gradio==5.44.1" \
    "pyloudnorm" \
    "omegaconf"
RUN python -m pip install --no-deps "chatterbox-tts==${CHATTERBOX_TTS_VERSION}"
RUN python -m pip uninstall -y hf-xet
RUN python -c "import spacy_pkuseg.config as c; from spacy_pkuseg.download import download_model; download_model(c.model_urls['spacy_ontonotes'], c.pkuseg_home, c.model_hash['spacy_ontonotes'])"

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/tts_sidecar /app/scripts/sir_convert_a_lot/tts_sidecar

EXPOSE 8094

CMD ["uvicorn", "scripts.sir_convert_a_lot.tts_sidecar.chatterbox_app:app", "--host", "0.0.0.0", "--port", "8094"]
