"""FastAPI entrypoint for the normalized OpenVoice Task 81 sidecar.

Purpose:
    Bind the reusable normalized TTS sidecar HTTP contract to the OpenVoice V2
    backend adapter used by the Hemma Task 81 benchmark.

Relationships:
    - Uses `create_tts_sidecar_app` to enforce ADR-0007 endpoint behavior.
    - Instantiates `OpenVoiceSidecarBackend` from environment-driven settings.
"""

from __future__ import annotations

from fastapi import FastAPI

from scripts.sir_convert_a_lot.tts_sidecar.app_factory import create_tts_sidecar_app
from scripts.sir_convert_a_lot.tts_sidecar.openvoice_runtime import (
    OpenVoiceSidecarBackend,
    OpenVoiceSidecarSettings,
)


def create_app() -> FastAPI:
    """Create the OpenVoice Task 81 sidecar application."""
    settings = OpenVoiceSidecarSettings.from_env()
    backend = OpenVoiceSidecarBackend(settings)
    return create_tts_sidecar_app(backend, title="Sir Convert-a-Lot OpenVoice TTS Sidecar")


app = create_app()
