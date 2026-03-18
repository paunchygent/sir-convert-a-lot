#
# Purpose:
#   Build a layered Sir Convert-a-Lot HTTP service image where stable system and
#   dependency layers remain cached across code-only updates.
#
# Relationships:
#   - Used by compose.yaml for the canonical runtime lane.
#   - Uses `export_service_requirements.py` to strip CUDA torch packages from
#     the service dependency layer before the ROCm wheels are installed.
#   - Keeps the final app layer focused on the `scripts/` tree so code-only
#     changes do not invalidate the heavy dependency build.
#

FROM python:3.11-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PDM_CHECK_UPDATE=false
ENV PDM_NO_SELF_UPDATE=1
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

ARG SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL="https://download.pytorch.org/whl/rocm7.1"
ARG SIR_CONVERT_A_LOT_TORCH_VERSION="2.10.0+rocm7.1"
ARG SIR_CONVERT_A_LOT_TORCHVISION_VERSION="0.25.0+rocm7.1"
ARG SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION="2.10.0+rocm7.1"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libharfbuzz-subset0 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libsm6 \
        libx11-6 \
        libxext6 \
        libxcb1 \
        libxrender1 \
        pandoc \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-swe \
    && rm -rf /var/lib/apt/lists/*

RUN getent group video >/dev/null || groupadd --system video
RUN getent group render >/dev/null || groupadd --system render
RUN mkdir -p /var/lib/sir-convert-a-lot/prod

FROM runtime-base AS dependency-builder

RUN python -m pip install --no-cache-dir "pdm==2.26.4"

COPY pyproject.toml pdm.lock ./
COPY scripts/sir_convert_a_lot/devops/export_service_requirements.py /tmp/export_service_requirements.py

RUN python -m venv "${VIRTUAL_ENV}"
RUN python -m pip install --upgrade --no-cache-dir pip
RUN python /tmp/export_service_requirements.py --project-root /app --output /tmp/service-requirements.txt
RUN python -m pip install --no-cache-dir --no-deps -r /tmp/service-requirements.txt
RUN python -m pip install --upgrade --no-cache-dir \
    --index-url "${SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL}" \
    "torch==${SIR_CONVERT_A_LOT_TORCH_VERSION}" \
    "torchvision==${SIR_CONVERT_A_LOT_TORCHVISION_VERSION}" \
    "torchaudio==${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION}"

RUN mkdir -p /opt/easyocr-models \
    && python -c 'import easyocr; easyocr.Reader(["sv", "en"], gpu=False, model_storage_directory="/opt/easyocr-models", download_enabled=True, verbose=False)'

FROM runtime-base AS runtime

COPY --from=dependency-builder /app/.venv /app/.venv
COPY --from=dependency-builder /opt/easyocr-models /opt/easyocr-models
COPY scripts ./scripts

EXPOSE 8085

CMD ["uvicorn", "scripts.sir_convert_a_lot.service:app", "--host", "0.0.0.0", "--port", "8085"]
