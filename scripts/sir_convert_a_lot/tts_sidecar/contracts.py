"""Typed internal contract models for reusable TTS sidecars.

Purpose:
    Define the normalized request, response, and capability schemas used by
    backend-specific TTS sidecar adapters and the Hemma benchmark harnesses.

Relationships:
    - Implements the internal sidecar contract accepted in ADR-0007.
    - Used by backend adapter apps under `scripts.sir_convert_a_lot.tts_sidecar`.
    - Consumed by benchmark runners in `scripts.sir_convert_a_lot.devops`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class SidecarStatus(StrEnum):
    """Health states surfaced by one normalized sidecar adapter."""

    OK = "ok"
    DEGRADED = "degraded"


class NetworkScope(StrEnum):
    """Allowed network exposure for one sidecar adapter."""

    INTERNAL_ONLY = "internal_only"


class LanguageSupportLevel(StrEnum):
    """Support-strength levels required by ADR-0007."""

    OFFICIAL = "official"
    CROSS_LINGUAL_CLAIMED = "cross_lingual_claimed"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class VoiceMode(StrEnum):
    """Normalized voice modes understood by the internal sidecar contract."""

    PRESET = "preset"
    REFERENCE_CLONE = "reference_clone"


class OutputFormat(StrEnum):
    """Normalized audio formats allowed by the sidecar contract."""

    WAV = "wav"


class NormalizationProfile(StrEnum):
    """Text normalization profiles accepted by the internal sidecar contract."""

    AUTO = "auto"
    NONE = "none"


class HealthResponse(BaseModel):
    """Normalized readiness payload for `GET /health`."""

    model_config = ConfigDict(extra="forbid")

    status: SidecarStatus
    backend_id: str
    backend_version: str
    backend_profile: str | None = None
    ready: bool


class RuntimeCapability(BaseModel):
    """Runtime truth surfaced by `GET /capabilities`."""

    model_config = ConfigDict(extra="forbid")

    python_version: str
    gpu_required: bool
    supports_rocm: bool
    network_scope: NetworkScope


class CacheCapability(BaseModel):
    """One cache mount family used by the sidecar runtime."""

    model_config = ConfigDict(extra="forbid")

    cache_family: str
    host_root: str
    container_root: str
    reuse_strategy: str


class SynthesisCapability(BaseModel):
    """Audio-format and delivery capabilities for one sidecar backend."""

    model_config = ConfigDict(extra="forbid")

    output_formats: list[OutputFormat]
    sample_rates_hz: list[int]
    supports_streaming: bool


class VoiceCapability(BaseModel):
    """Voice-input expectations for one sidecar backend."""

    model_config = ConfigDict(extra="forbid")

    modes: list[VoiceMode]
    reference_transcript_required: bool
    reference_audio_required: bool


class LanguageCapability(BaseModel):
    """Normalized language support claim for one code."""

    model_config = ConfigDict(extra="forbid")

    code: str
    support_level: LanguageSupportLevel
    notes: str | None = None


class CapabilityResponse(BaseModel):
    """Top-level capability document for `GET /capabilities`."""

    model_config = ConfigDict(extra="forbid")

    backend_id: str
    backend_version: str
    backend_profile: str | None = None
    runtime: RuntimeCapability
    cache: CacheCapability
    auxiliary_caches: list[CacheCapability] = Field(default_factory=list)
    synthesis: SynthesisCapability
    voice: VoiceCapability
    languages: list[LanguageCapability]


class VoiceDescriptor(BaseModel):
    """One preset voice returned by `GET /voices`."""

    model_config = ConfigDict(extra="forbid")

    voice_id: str
    display_name: str
    mode: VoiceMode = VoiceMode.PRESET
    language_codes: list[str] = Field(default_factory=list)


class VoicesResponse(BaseModel):
    """Stable preset-voice listing for one sidecar backend."""

    model_config = ConfigDict(extra="forbid")

    voices: list[VoiceDescriptor] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Structured error envelope for normalized sidecar failures."""

    model_config = ConfigDict(extra="forbid")

    error: str
    code: str


@dataclass(frozen=True)
class SynthesizeRequest:
    """Normalized synthesis request consumed by backend runtime adapters."""

    text: str
    language: str
    voice_mode: VoiceMode
    output_format: OutputFormat
    style_instructions: str | None
    normalization_profile: NormalizationProfile
    preset_voice_id: str | None
    reference_transcript: str | None


@dataclass(frozen=True)
class ReferenceAudio:
    """Reference-audio payload uploaded to one cloning-capable backend."""

    filename: str
    content_type: str | None
    data: bytes


@dataclass(frozen=True)
class SynthesizeResult:
    """Successful normalized synthesis result returned by one backend adapter."""

    audio_bytes: bytes
    content_type: str
    filename: str
    sample_rate_hz: int | None


class SidecarRequestError(RuntimeError):
    """Error raised when one normalized sidecar request is invalid or unsupported."""

    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NormalizedTtsBackend(Protocol):
    """Backend interface implemented by all normalized sidecar adapters."""

    def startup(self) -> None:
        """Load runtime dependencies and become ready to answer requests."""

    def health(self) -> HealthResponse:
        """Return readiness information for the backend."""

    def capabilities(self) -> CapabilityResponse:
        """Return the normalized capability document for the backend."""

    def voices(self) -> VoicesResponse:
        """Return one bounded preset-voice listing for the backend."""

    def synthesize(
        self,
        request: SynthesizeRequest,
        *,
        reference_audio: ReferenceAudio | None,
    ) -> SynthesizeResult:
        """Synthesize one request and return binary audio on success."""
