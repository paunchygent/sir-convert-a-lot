"""FastAPI entrypoint for the normalized F5-TTS Task 85 sidecar.

Purpose:
    Bind the reusable normalized TTS sidecar HTTP contract to the F5-TTS
    backend adapter used by the Hemma Task 85 smoke benchmark.

Relationships:
    - Uses `create_tts_sidecar_app` to enforce ADR-0007 endpoint behavior.
    - Instantiates `F5TtsSidecarBackend` from environment-driven settings.
"""

from __future__ import annotations

from fastapi import FastAPI

from scripts.sir_convert_a_lot.tts_sidecar.app_factory import create_tts_sidecar_app
from scripts.sir_convert_a_lot.tts_sidecar.f5_runtime import (
    F5TtsSidecarBackend,
    F5TtsSidecarSettings,
)


def create_app() -> FastAPI:
    """Create the F5-TTS Task 85 sidecar application."""
    settings = F5TtsSidecarSettings.from_env()
    backend = F5TtsSidecarBackend(settings)
    return create_tts_sidecar_app(backend, title="Sir Convert-a-Lot F5-TTS Sidecar")


app = create_app()
