"""FastAPI entrypoint for the production STT sidecar.

Purpose:
    Instantiate the accepted FasterWhisper plus pyannote STT runtime as a
    long-running internal HTTP sidecar for Service API v2 audio jobs.

Relationships:
    - Mounted by the STT sidecar container CMD.
    - Uses `stt_sidecar.app_factory` for the normalized endpoint contract.
"""

from __future__ import annotations

from fastapi import FastAPI

from scripts.sir_convert_a_lot.stt_sidecar.app_factory import create_stt_sidecar_app
from scripts.sir_convert_a_lot.stt_sidecar.runtime import SttSidecarRuntime
from scripts.sir_convert_a_lot.stt_sidecar.settings import SttSidecarSettings


def create_app() -> FastAPI:
    """Create the production STT sidecar application."""
    settings = SttSidecarSettings.from_env()
    runtime = SttSidecarRuntime(settings)
    return create_stt_sidecar_app(runtime, title="Sir Convert-a-Lot STT Sidecar")


app = create_app()
