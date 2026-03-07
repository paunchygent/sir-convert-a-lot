# syntax=docker/dockerfile:1
# Experimental benchmark sidecar image. Do not deploy on Hemma as a production service.

FROM python:3.12-slim

ARG TORCH_ROCM_INDEX_URL=https://download.pytorch.org/whl/rocm7.1
ARG TORCH_VERSION=2.10.0+rocm7.1
ARG F5_TTS_REF=1.1.17
ARG TRANSFORMERS_VERSION=4.57.6
ARG HUGGINGFACE_HUB_VERSION=0.34.4

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app
ENV HF_HUB_DISABLE_XET=1

LABEL org.sir_convert_a_lot.sidecar_family="tts"
LABEL org.sir_convert_a_lot.sidecar_backend="f5_tts_swedish"
LABEL org.sir_convert_a_lot.lifecycle="experimental_benchmark"
LABEL org.sir_convert_a_lot.hemma_deployable="false"

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
    "torchaudio==${TORCH_VERSION}"
RUN git clone --branch "${F5_TTS_REF}" --depth 1 https://github.com/SWivid/F5-TTS.git /opt/F5-TTS \
    && git -C /opt/F5-TTS submodule update --init --recursive
RUN python -m pip install \
    "fastapi>=0.128.8" \
    "uvicorn[standard]>=0.40.0" \
    "python-multipart>=0.0.22" \
    "httpx>=0.28.1" \
    "pydantic==2.10.6" \
    "transformers==${TRANSFORMERS_VERSION}" \
    "huggingface-hub==${HUGGINGFACE_HUB_VERSION}" \
    "soundfile>=0.13.1"
RUN python -m pip install -e /opt/F5-TTS
RUN python -m pip uninstall -y hf-xet

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/tts_sidecar /app/scripts/sir_convert_a_lot/tts_sidecar

EXPOSE 8093

CMD ["uvicorn", "scripts.sir_convert_a_lot.tts_sidecar.f5_app:app", "--host", "0.0.0.0", "--port", "8093"]
