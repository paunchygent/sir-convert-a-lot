# syntax=docker/dockerfile:1
#
# Purpose:
#   Build the isolated speech-to-text sidecar runtime used by Service API v2
#   audio transcript jobs and Hemma profile-proof observations.
#
# Relationships:
#   - Built with Docker BuildKit for the production sidecar and live
#     observation lanes.
#   - Provides FFmpeg, faster-whisper, pyannote.audio, Hugging Face Hub, and
#     ROCm-backed Torch for live profile evidence collection without changing the
#     main Sir Convert service image.
#

ARG BASE_IMAGE=sir-convert-a-lot-deps-rocm:local

FROM ${BASE_IMAGE} AS stt-sidecar-benchmark

ARG CTRANSLATE2_VERSION=4.8.0
ARG CTRANSLATE2_RELEASE_BASE_URL=https://github.com/OpenNMT/CTranslate2/releases/download
ARG CTRANSLATE2_ROCM_WHEELS_ARCHIVE=rocm-python-wheels-Linux.zip
ARG CTRANSLATE2_ROCM_WHEELS_SHA256=9ec6d82e5682b27af6c535f56525665c949cc63fbef14a9028c47b0164717143
ARG CTRANSLATE2_ROCM_WHEEL=ctranslate2-4.8.0-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
ARG CTRANSLATE2_PYTHON_PACKAGE_DIR=/app/.venv/lib/python3.11/site-packages/ctranslate2
ARG CTRANSLATE2_WHEEL_LIBRARY_DIR=/app/.venv/lib/python3.11/site-packages/ctranslate2.libs
ARG CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR=/opt/ctranslate2-rocm-libraries
ARG TORCH_ROCM_LIBRARY_DIR=/app/.venv/lib/python3.11/site-packages/torch/lib

ENV HF_HOME=/cache/huggingface
ENV HF_HUB_CACHE=/cache/huggingface/hub
ENV TRANSFORMERS_CACHE=/cache/huggingface
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        libc6-dev \
        librocrand-dev \
        patchelf \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,id=sir-convert-a-lot-stt-sidecar-pip,target=/root/.cache/pip \
    python -m pip install --upgrade \
        "fastapi>=0.128.8" \
        faster-whisper \
        "huggingface-hub==0.34.4" \
        "pyannote.audio==4.0.4" \
        "torchcodec==0.10.0" \
        "uvicorn[standard]>=0.40.0"

RUN --mount=type=cache,id=sir-convert-a-lot-stt-sidecar-ctranslate2-rocm,target=/tmp/ctranslate2-rocm-download \
    set -eux; \
    archive_path="/tmp/ctranslate2-rocm-download/${CTRANSLATE2_ROCM_WHEELS_ARCHIVE}"; \
    extract_dir="/tmp/ctranslate2-rocm-wheel"; \
    curl -fsSL "${CTRANSLATE2_RELEASE_BASE_URL}/v${CTRANSLATE2_VERSION}/${CTRANSLATE2_ROCM_WHEELS_ARCHIVE}" -o "${archive_path}"; \
    printf '%s  %s\n' "${CTRANSLATE2_ROCM_WHEELS_SHA256}" "${archive_path}" > "${archive_path}.sha256"; \
    sha256sum --check "${archive_path}.sha256"; \
    rm -rf "${extract_dir}"; \
    mkdir -p "${extract_dir}"; \
    unzip -q "${archive_path}" -d "${extract_dir}"; \
    test -f "${extract_dir}/temp-linux/${CTRANSLATE2_ROCM_WHEEL}"; \
    python -m pip install --force-reinstall --no-deps "${extract_dir}/temp-linux/${CTRANSLATE2_ROCM_WHEEL}"; \
    mkdir -p "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}"; \
    find "${TORCH_ROCM_LIBRARY_DIR}" -maxdepth 1 \( -type f -o -type l \) -name 'lib*.so*' ! -name 'libtinfo.so*' -exec ln -sf '{}' "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/" \;; \
    test -e "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhiprand.so"; \
    test -e "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhipblas.so"; \
    test -e "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libamdhip64.so"; \
    ln -sf "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhiprand.so" "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhiprand.so.1"; \
    ln -sf "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhipblas.so" "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhipblas.so.3"; \
    ln -sf "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libamdhip64.so" "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libamdhip64.so.7"; \
    for binary_path in "${CTRANSLATE2_PYTHON_PACKAGE_DIR}"/_ext*.so; do \
        test -f "${binary_path}"; \
        patchelf --set-rpath "\$ORIGIN/../ctranslate2.libs:${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}" "${binary_path}"; \
    done; \
    for binary_path in "${CTRANSLATE2_WHEEL_LIBRARY_DIR}"/libctranslate2*.so*; do \
        test -f "${binary_path}"; \
        patchelf --set-rpath "\$ORIGIN:${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}" "${binary_path}"; \
    done; \
    rm -rf "${extract_dir}" "${archive_path}.sha256"

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/domain /app/scripts/sir_convert_a_lot/domain
COPY scripts/sir_convert_a_lot/devops /app/scripts/sir_convert_a_lot/devops
COPY scripts/sir_convert_a_lot/stt_sidecar /app/scripts/sir_convert_a_lot/stt_sidecar

EXPOSE 8095

CMD ["uvicorn", "scripts.sir_convert_a_lot.stt_sidecar.app:app", "--host", "0.0.0.0", "--port", "8095"]
