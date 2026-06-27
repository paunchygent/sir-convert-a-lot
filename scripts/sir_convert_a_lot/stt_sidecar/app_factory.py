"""FastAPI factory for the normalized STT sidecar.

Purpose:
    Bind the speech-to-text backend protocol to the HTTP endpoints called by
    Service API v2 audio transcript-bundle execution.

Relationships:
    - Uses `stt_sidecar.contracts.SttSidecarBackend` for backend delegation.
    - Mirrors the reusable sidecar factory pattern used by TTS adapters while
      exposing STT-specific media probe, diarization, chunk transcription, and
      cancellation routes.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse

from scripts.sir_convert_a_lot.stt_sidecar.contracts import (
    SttSidecarBackend,
    SttSidecarRequestError,
)


def create_stt_sidecar_app(backend: SttSidecarBackend, *, title: str) -> FastAPI:
    """Create the normalized STT sidecar application."""

    @asynccontextmanager
    async def _lifespan(_: FastAPI):
        backend.startup()
        try:
            yield
        finally:
            backend.shutdown()

    app = FastAPI(title=title, lifespan=_lifespan)

    @app.get("/health")
    def health() -> Mapping[str, object]:
        return backend.health()

    @app.get("/capabilities")
    def capabilities() -> Mapping[str, object]:
        return backend.capabilities()

    @app.post("/probe-media", response_model=None)
    def probe_media(
        request: dict[str, object] = Body(...),
    ) -> Mapping[str, object] | JSONResponse:
        try:
            return backend.probe_media(request)
        except SttSidecarRequestError as exc:
            return _error_response(exc)

    @app.post("/diarize", response_model=None)
    def diarize(request: dict[str, object] = Body(...)) -> Mapping[str, object] | JSONResponse:
        try:
            return backend.diarize(request)
        except SttSidecarRequestError as exc:
            return _error_response(exc)

    @app.post("/transcribe-chunk", response_model=None)
    def transcribe_chunk(
        request: dict[str, object] = Body(...),
    ) -> Mapping[str, object] | JSONResponse:
        try:
            return backend.transcribe_chunk(request)
        except SttSidecarRequestError as exc:
            return _error_response(exc)

    @app.post("/cancel", response_model=None)
    def cancel(request: dict[str, object] = Body(...)) -> Mapping[str, object] | JSONResponse:
        try:
            request_handle = _request_handle(request)
            return backend.cancel(request_handle)
        except SttSidecarRequestError as exc:
            return _error_response(exc)

    @app.post("/finalize", response_model=None)
    def finalize(request: dict[str, object] = Body(...)) -> Mapping[str, object] | JSONResponse:
        try:
            request_handle = _request_handle(request)
            return backend.finalize(request_handle)
        except SttSidecarRequestError as exc:
            return _error_response(exc)

    return app


def _error_response(exc: SttSidecarRequestError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
    )


def _request_handle(payload: Mapping[str, object]) -> str:
    value = payload.get("request_handle")
    if isinstance(value, str) and value.strip() != "":
        return value
    raise SttSidecarRequestError(
        code="invalid_request",
        message="request_handle is required.",
        status_code=422,
    )
