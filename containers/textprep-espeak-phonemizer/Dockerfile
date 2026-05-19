# syntax=docker/dockerfile:1
# Experimental helper image. Do not deploy on Hemma as a production service.

FROM python:3.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app

LABEL org.sir_convert_a_lot.sidecar_family="textprep"
LABEL org.sir_convert_a_lot.sidecar_backend="espeak_phonemizer"
LABEL org.sir_convert_a_lot.lifecycle="experimental_helper"
LABEL org.sir_convert_a_lot.hemma_deployable="false"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        espeak-ng \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip "setuptools<81" wheel
RUN python -m pip install "phonemizer==3.3.0"

COPY scripts/__init__.py /app/scripts/__init__.py
COPY scripts/sir_convert_a_lot/__init__.py /app/scripts/sir_convert_a_lot/__init__.py
COPY scripts/sir_convert_a_lot/textprep /app/scripts/sir_convert_a_lot/textprep

ENTRYPOINT ["python", "-m", "scripts.sir_convert_a_lot.textprep.espeak_phonemizer_cli"]
