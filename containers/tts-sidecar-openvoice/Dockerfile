# syntax=docker/dockerfile:1
# Experimental benchmark sidecar image. Do not deploy on Hemma as a production service.

FROM python:3.12-slim

ARG OPENVOICE_GIT_REF=74a1d147b17a8c3092dd5430504bd83ef6c7eb23
ARG TORCH_ROCM_INDEX_URL=https://download.pytorch.org/whl/rocm7.1
ARG TORCH_VERSION=2.10.0+rocm7.1

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app

LABEL org.sir_convert_a_lot.sidecar_family="tts"
LABEL org.sir_convert_a_lot.sidecar_backend="openvoice_v2"
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
# Keep the reference-speaker preprocessing stack aligned to OpenVoice's current
# published requirements for Task 81 compatibility benchmarking; this is not a
# repo-wide dependency policy.
RUN python -m pip install \
    "setuptools<81" \
    "fastapi>=0.128.8" \
    "uvicorn[standard]>=0.40.0" \
    "python-multipart>=0.0.22" \
    "httpx>=0.28.1" \
    "pydantic>=2.11.7" \
    "huggingface_hub>=0.34.4" \
    "transformers==4.57.6" \
    "numpy<2" \
    "onnxruntime>=1.22.1" \
    "scipy>=1.11.0" \
    "librosa==0.9.1" \
    "pydub==0.25.1" \
    "soxr>=0.5.0" \
    "soundfile>=0.13.1" \
    "inflect==7.0.0" \
    "unidecode==1.3.7" \
    "eng_to_ipa==0.0.2" \
    "pypinyin==0.50.0" \
    "cn2an==0.5.22" \
    "jieba==0.42.1"
RUN python -m pip install --no-deps "git+https://github.com/myshell-ai/OpenVoice.git@${OPENVOICE_GIT_REF}"
RUN python -c "import pkg_resources; from transformers import VitsModel"

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/tts_sidecar /app/scripts/sir_convert_a_lot/tts_sidecar

EXPOSE 8092

CMD ["uvicorn", "scripts.sir_convert_a_lot.tts_sidecar.openvoice_app:app", "--host", "0.0.0.0", "--port", "8092"]
