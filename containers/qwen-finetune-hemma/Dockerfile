# syntax=docker/dockerfile:1
# Experimental Task 100 training image for Qwen3-TTS Swedish fine-tuning on Hemma.

FROM rocm/dev-ubuntu-24.04:7.1.1-complete

ARG TORCH_ROCM_INDEX_URL=https://download.pytorch.org/whl/rocm7.1
ARG TORCH_VERSION=2.10.0+rocm7.1
ARG TORCHAUDIO_VERSION=2.10.0+rocm7.1
ARG FLASH_ATTENTION_REPO=https://github.com/ROCm/flash-attention.git
ARG FLASH_ATTENTION_REF=main_perf
ARG GPU_ARCHS=gfx1201
ARG MAX_JOBS=16
ARG VIRTUAL_ENV=/opt/task100-venv

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV VIRTUAL_ENV=${VIRTUAL_ENV}
ENV PATH=${VIRTUAL_ENV}/bin:${PATH}
ENV PYTHONPATH=/app:/app/scripts/devops/qwen_finetuning_patches
ENV HF_HUB_DISABLE_XET=1
ENV GPU_ARCHS=${GPU_ARCHS}
ENV PYTORCH_ROCM_ARCH=${GPU_ARCHS}
ENV MAX_JOBS=${MAX_JOBS}
ENV FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE

LABEL org.sir_convert_a_lot.runtime_family="qwen_finetune"
LABEL org.sir_convert_a_lot.runtime_backend="qwen3_tts_12hz_1p7b"
LABEL org.sir_convert_a_lot.lifecycle="experimental_training"
LABEL org.sir_convert_a_lot.hemma_deployable="false"

WORKDIR /app

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        git \
        hipblas-dev \
        hiprand-dev \
        libdw1 \
        libsndfile1 \
        python-is-python3 \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        rocblas-dev \
        rocsolver-dev \
        hipsparse-dev \
        sox \
    && rm -rf /var/lib/apt/lists/*

COPY containers/qwen-finetune-hemma/requirements.txt /tmp/task100-requirements.txt

RUN python3 -m venv "${VIRTUAL_ENV}"
RUN python -m pip install --upgrade pip "setuptools<81" wheel
RUN python -m pip install --index-url "${TORCH_ROCM_INDEX_URL}" \
    "torch==${TORCH_VERSION}" \
    "torchaudio==${TORCHAUDIO_VERSION}"
RUN python -m pip install -r /tmp/task100-requirements.txt
RUN python -m pip uninstall -y hf-xet triton || true
RUN python -m pip install \
    "ninja>=1.13.0" \
    "packaging>=25.0" \
    "psutil>=7.1.0" \
    "triton==3.5.1"
RUN git clone --recursive --branch "${FLASH_ATTENTION_REF}" "${FLASH_ATTENTION_REPO}" /tmp/flash-attention \
    && cd /tmp/flash-attention \
    && python -m pip install . --no-build-isolation \
    && rm -rf /tmp/flash-attention

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/devops /app/scripts/sir_convert_a_lot/devops
COPY scripts/devops/qwen_finetuning_patches /app/scripts/devops/qwen_finetuning_patches

CMD ["python", "-m", "scripts.sir_convert_a_lot.devops.task100_qwen_finetune_smoke_probe", "--help"]
