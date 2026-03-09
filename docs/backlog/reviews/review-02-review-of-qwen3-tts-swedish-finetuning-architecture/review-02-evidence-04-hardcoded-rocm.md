---
id: review-02-evidence-04-hardcoded-rocm
title: 'Evidence: Hardcoded ROCm Lock-in Blocks Colab H100'
type: review
status: completed
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture/README.md
labels: []
---

**Source:** `containers/qwen-finetune-hemma/Dockerfile`
**Lines:** 4-26

The base `Dockerfile` explicitly targets ROCm and specific RDNA3 AMD architecture (`gfx1201`), strictly violating the stated fallback requirement for running the container on Nvidia H100s via Colab.

```dockerfile
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
```
