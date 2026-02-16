#
# Purpose:
#   Build a deterministic container image for Sir Convert-a-Lot HTTP services.
#
# Relationships:
#   - Used by compose.yaml for prod/eval service lanes.
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

RUN python -m pip install --no-cache-dir "pdm==2.26.4"

COPY pyproject.toml pdm.lock ./
RUN pdm sync --prod --no-editable --no-self
RUN pdm run python -m ensurepip --upgrade
RUN pdm run python -m pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1 || true
RUN pdm run python -m pip install --upgrade --no-cache-dir \
    --index-url "${SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL}" \
    "torch==${SIR_CONVERT_A_LOT_TORCH_VERSION}" \
    "torchvision==${SIR_CONVERT_A_LOT_TORCHVISION_VERSION}" \
    "torchaudio==${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION}"

COPY scripts ./scripts

RUN mkdir -p /var/lib/sir-convert-a-lot/prod /var/lib/sir-convert-a-lot/eval

EXPOSE 8085
EXPOSE 8086

CMD ["pdm", "run", "serve:sir-convert-a-lot"]
