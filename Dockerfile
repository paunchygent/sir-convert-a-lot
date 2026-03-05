#
# Purpose:
#   Build a deterministic container image for Sir Convert-a-Lot HTTP service.
#
# Relationships:
#   - Used by compose.yaml for the canonical runtime lane.
#   - Executes canonical PDM script entrypoints from pyproject.toml.
#

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PDM_CHECK_UPDATE=false
ENV PDM_NO_SELF_UPDATE=1

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

RUN python -m pip install --no-cache-dir "pdm==2.26.4"
RUN getent group video >/dev/null || groupadd --system video
RUN getent group render >/dev/null || groupadd --system render

COPY pyproject.toml pdm.lock ./
RUN pdm sync --prod --no-editable --no-self
RUN pdm run python -m ensurepip --upgrade
RUN pdm run python -m pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1 || true
RUN pdm run python -m pip install --upgrade --no-cache-dir \
    --index-url "${SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL}" \
    "torch==${SIR_CONVERT_A_LOT_TORCH_VERSION}" \
    "torchvision==${SIR_CONVERT_A_LOT_TORCHVISION_VERSION}" \
    "torchaudio==${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION}"

RUN mkdir -p /opt/easyocr-models \
    && pdm run python -c 'import easyocr; easyocr.Reader(["sv", "en"], gpu=False, model_storage_directory="/opt/easyocr-models", download_enabled=True, verbose=False)'

COPY scripts ./scripts

RUN mkdir -p /var/lib/sir-convert-a-lot/prod

EXPOSE 8085

CMD ["pdm", "run", "serve:sir-convert-a-lot"]
