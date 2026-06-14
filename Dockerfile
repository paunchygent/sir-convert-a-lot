#
# Purpose:
#   Build the Sir Convert-a-Lot production HTTP service image from an explicit
#   prebuilt dependency image so app/ops-only updates stay cache-hot.
#
# Relationships:
#   - Used by compose.yaml for the canonical runtime lane.
#   - Consumes `DEPS_IMAGE`, normally built by `pdm run prod-deps-rocm-build`.
#   - Copies only the application runtime source after dependencies, ROCm
#     torch, and EasyOCR preload are already baked.
#

ARG DEPS_IMAGE=sir-convert-a-lot-deps-rocm:local

FROM ${DEPS_IMAGE} AS runtime

COPY scripts/__init__.py ./scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py ./scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/service.py ./scripts/sir_convert_a_lot/service.py
COPY scripts/sir_convert_a_lot/service_remote_proof.py ./scripts/sir_convert_a_lot/service_remote_proof.py
COPY scripts/sir_convert_a_lot/application ./scripts/sir_convert_a_lot/application
COPY scripts/sir_convert_a_lot/domain ./scripts/sir_convert_a_lot/domain
COPY scripts/sir_convert_a_lot/infrastructure ./scripts/sir_convert_a_lot/infrastructure
COPY scripts/sir_convert_a_lot/integrations ./scripts/sir_convert_a_lot/integrations
COPY scripts/sir_convert_a_lot/interfaces ./scripts/sir_convert_a_lot/interfaces
COPY scripts/sir_convert_a_lot/templates ./scripts/sir_convert_a_lot/templates

EXPOSE 8085

CMD ["uvicorn", "scripts.sir_convert_a_lot.service:app", "--host", "0.0.0.0", "--port", "8085"]
