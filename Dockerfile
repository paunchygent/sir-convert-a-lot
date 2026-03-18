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
COPY scripts/__init__.py /tmp/service-build-support/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /tmp/service-build-support/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/devops/__init__.py /tmp/service-build-support/scripts/sir_convert_a_lot/devops/__init__.py
COPY scripts/sir_convert_a_lot/devops/export_service_requirements.py /tmp/service-build-support/scripts/sir_convert_a_lot/devops/export_service_requirements.py
COPY scripts/sir_convert_a_lot/devops/service_image_build_contract.py /tmp/service-build-support/scripts/sir_convert_a_lot/devops/service_image_build_contract.py

RUN python -m venv "${VIRTUAL_ENV}"
RUN python -m pip install --upgrade --no-cache-dir pip
RUN PYTHONPATH=/tmp/service-build-support python -m scripts.sir_convert_a_lot.devops.export_service_requirements --project-root /app --output /tmp/service-requirements.txt
RUN PYTHONPATH=/tmp/service-build-support python -c 'from pathlib import Path; from scripts.sir_convert_a_lot.devops.service_image_build_contract import load_rocm_runtime_contract; Path("/tmp/rocm-runtime.env").write_text(load_rocm_runtime_contract(Path("/app")).as_shell_exports(), encoding="utf-8")'
RUN python -m pip install --no-cache-dir --no-deps -r /tmp/service-requirements.txt
RUN . /tmp/rocm-runtime.env \
    && python -m pip install --upgrade --no-cache-dir \
        --index-url "${SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL}" \
        "torch==${SIR_CONVERT_A_LOT_TORCH_VERSION}" \
        "torchvision==${SIR_CONVERT_A_LOT_TORCHVISION_VERSION}" \
        "torchaudio==${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION}"

RUN mkdir -p /opt/easyocr-models \
    && python -c 'import easyocr; easyocr.Reader(["sv", "en"], gpu=False, model_storage_directory="/opt/easyocr-models", download_enabled=True, verbose=False)'

FROM runtime-base AS runtime

COPY --from=dependency-builder /app/.venv /app/.venv
COPY --from=dependency-builder /opt/easyocr-models /opt/easyocr-models
COPY scripts/__init__.py ./scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py ./scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/service.py ./scripts/sir_convert_a_lot/service.py
COPY scripts/sir_convert_a_lot/application ./scripts/sir_convert_a_lot/application
COPY scripts/sir_convert_a_lot/domain ./scripts/sir_convert_a_lot/domain
COPY scripts/sir_convert_a_lot/infrastructure ./scripts/sir_convert_a_lot/infrastructure
COPY scripts/sir_convert_a_lot/integrations ./scripts/sir_convert_a_lot/integrations
COPY scripts/sir_convert_a_lot/interfaces ./scripts/sir_convert_a_lot/interfaces
COPY scripts/sir_convert_a_lot/templates ./scripts/sir_convert_a_lot/templates

EXPOSE 8085

CMD ["uvicorn", "scripts.sir_convert_a_lot.service:app", "--host", "0.0.0.0", "--port", "8085"]
