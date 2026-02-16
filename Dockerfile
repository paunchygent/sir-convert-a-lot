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

WORKDIR /app

RUN python -m pip install --no-cache-dir "pdm==2.26.4"

COPY pyproject.toml pdm.lock ./
RUN pdm sync --prod --no-editable --no-self

COPY scripts ./scripts

RUN mkdir -p /var/lib/sir-convert-a-lot/prod /var/lib/sir-convert-a-lot/eval

EXPOSE 8085
EXPOSE 8086

CMD ["pdm", "run", "serve:sir-convert-a-lot"]
