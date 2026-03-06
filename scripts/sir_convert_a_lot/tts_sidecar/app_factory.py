"""Generic FastAPI factory for normalized internal TTS sidecars.

Purpose:
    Provide one reusable HTTP surface that backend-specific runtimes can plug
    into while preserving ADR-0007 endpoint names and error semantics.

Relationships:
    - Uses typed contract models from `scripts.sir_convert_a_lot.tts_sidecar.contracts`.
    - Hosts backend implementations such as the OpenVoice adapter.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response

from scripts.sir_convert_a_lot.tts_sidecar.contracts import (
    CapabilityResponse,
    ErrorResponse,
    HealthResponse,
    NormalizationProfile,
    NormalizedTtsBackend,
    OutputFormat,
    ReferenceAudio,
    SidecarRequestError,
    SynthesizeRequest,
    VoiceMode,
    VoicesResponse,
)


def _normalize_form_value(value: str | None) -> str | None:
    """Convert empty form values into `None` for cleaner downstream handling."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped != "" else None


async def _read_reference_audio(upload: UploadFile | None) -> ReferenceAudio | None:
    """Read one optional uploaded reference-audio file into memory."""
    if upload is None:
        return None
    data = await upload.read()
    return ReferenceAudio(
        filename=upload.filename or "reference-audio", content_type=upload.content_type, data=data
    )


def create_tts_sidecar_app(backend: NormalizedTtsBackend, *, title: str) -> FastAPI:
    """Create one FastAPI app bound to the normalized sidecar backend contract."""

    @asynccontextmanager
    async def _lifespan(_: FastAPI):
        backend.startup()
        yield

    app = FastAPI(title=title, lifespan=_lifespan)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return backend.health()

    @app.get("/capabilities", response_model=CapabilityResponse)
    def capabilities() -> CapabilityResponse:
        return backend.capabilities()

    @app.get("/voices", response_model=VoicesResponse)
    def voices() -> VoicesResponse:
        return backend.voices()

    @app.post(
        "/synthesize",
        response_model=None,
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            415: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    async def synthesize(
        text: str = Form(...),
        language: str = Form(...),
        voice_mode: VoiceMode = Form(...),
        output_format: OutputFormat = Form(OutputFormat.WAV),
        style_instructions: str | None = Form(default=None),
        normalization_profile: NormalizationProfile = Form(NormalizationProfile.AUTO),
        preset_voice_id: str | None = Form(default=None),
        reference_transcript: str | None = Form(default=None),
        reference_audio: UploadFile | None = File(default=None),
    ) -> Response:
        try:
            request = SynthesizeRequest(
                text=text,
                language=language,
                voice_mode=voice_mode,
                output_format=output_format,
                style_instructions=_normalize_form_value(style_instructions),
                normalization_profile=normalization_profile,
                preset_voice_id=_normalize_form_value(preset_voice_id),
                reference_transcript=_normalize_form_value(reference_transcript),
            )
            result = backend.synthesize(
                request,
                reference_audio=await _read_reference_audio(reference_audio),
            )
        except SidecarRequestError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(error=exc.message, code=exc.code).model_dump(),
            )
        return Response(
            content=result.audio_bytes,
            media_type=result.content_type,
            headers={"Content-Disposition": f'inline; filename="{result.filename}"'},
        )

    return app
