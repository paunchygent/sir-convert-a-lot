"""FastAPI entrypoint for the normalized Chatterbox Task 86 sidecar.

Purpose:
    Bind the reusable normalized TTS sidecar HTTP contract to the Chatterbox
    backend adapter used by the Hemma Task 86 benchmark.

Relationships:
    - Uses `create_tts_sidecar_app` to enforce ADR-0007 endpoint behavior.
    - Instantiates `ChatterboxSidecarBackend` from environment-driven settings.
"""

from __future__ import annotations

from fastapi import FastAPI

from scripts.sir_convert_a_lot.tts_sidecar.app_factory import create_tts_sidecar_app
from scripts.sir_convert_a_lot.tts_sidecar.chatterbox_runtime import (
    ChatterboxSidecarBackend,
    ChatterboxSidecarSettings,
)


def create_app() -> FastAPI:
    """Create the Chatterbox Task 86 sidecar application."""
    settings = ChatterboxSidecarSettings.from_env()
    backend = ChatterboxSidecarBackend(settings)
    return create_tts_sidecar_app(backend, title="Sir Convert-a-Lot Chatterbox Sidecar")


app = create_app()
