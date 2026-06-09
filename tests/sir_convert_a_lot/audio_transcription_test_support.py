"""Shared fixtures for audio transcription policy tests.

Purpose:
    Provide typed builders for audio route-admission and STT sidecar readiness
    tests without coupling behavioral assertions to construction boilerplate.

Relationships:
    - Supports route-policy and sidecar-readiness test modules.
    - Mirrors the governed audio converter contract's day-one media and
      normalized-audio capability truth.
"""

from __future__ import annotations

from collections.abc import Mapping

from scripts.sir_convert_a_lot.domain.audio_transcription_policy import (
    AudioDiarizationMode,
    AudioDiarizationOptions,
    AudioInputProtocol,
    AudioProbeEvidence,
    AudioTranscriptionPublicOptions,
    AudioTranscriptionRouteRequest,
)
from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy

ACCEPTED_MEDIA_CONTAINERS = (
    "aac",
    "aiff",
    "flac",
    "m4a",
    "mkv",
    "mov",
    "mp3",
    "mp4",
    "ogg",
    "opus",
    "wav",
    "webm",
)


def route_request(**patch: object) -> AudioTranscriptionRouteRequest:
    """Build a default GPU-required local-upload route request."""

    route_enabled = True
    input_protocol = AudioInputProtocol.LOCAL_UPLOAD
    acceleration_policy = AccelerationPolicy.GPU_REQUIRED
    retention_pin = False
    public_options = public_options_with()
    for key, value in patch.items():
        if key == "route_enabled" and isinstance(value, bool):
            route_enabled = value
        elif key == "input_protocol" and isinstance(value, AudioInputProtocol):
            input_protocol = value
        elif key == "acceleration_policy" and isinstance(value, AccelerationPolicy):
            acceleration_policy = value
        elif key == "retention_pin" and isinstance(value, bool):
            retention_pin = value
        elif key == "public_options" and isinstance(value, AudioTranscriptionPublicOptions):
            public_options = value
        else:
            raise AssertionError(f"unsupported route request patch: {key}")
    return AudioTranscriptionRouteRequest(
        route_enabled=route_enabled,
        input_protocol=input_protocol,
        acceleration_policy=acceleration_policy,
        retention_pin=retention_pin,
        public_options=public_options,
    )


def public_options_with(
    *,
    language: str = "auto",
    diarization: AudioDiarizationOptions | None = None,
    max_duration_seconds: int = 7200,
    output_artifacts: tuple[str, ...] = ("json",),
    raw_option_keys: frozenset[str] | None = None,
) -> AudioTranscriptionPublicOptions:
    """Build public options using only the governed day-one option surface."""

    if diarization is None:
        diarization = AudioDiarizationOptions(mode=AudioDiarizationMode.AUTO)
    if raw_option_keys is None:
        raw_option_keys = frozenset({"language", "diarization", "output_artifacts"})
    return AudioTranscriptionPublicOptions(
        language=language,
        diarization=diarization,
        max_duration_seconds=max_duration_seconds,
        output_artifacts=output_artifacts,
        raw_option_keys=raw_option_keys,
    )


def probe(**patch: object) -> AudioProbeEvidence:
    """Build default media-probe evidence for an accepted local audio upload."""

    container = "wav"
    codec = "pcm_s16le"
    has_audio_stream = True
    duration_seconds = 120.0
    upload_size_bytes = 1024
    for key, value in patch.items():
        if key == "container" and isinstance(value, str):
            container = value
        elif key == "codec" and isinstance(value, str):
            codec = value
        elif key == "has_audio_stream" and isinstance(value, bool):
            has_audio_stream = value
        elif key == "duration_seconds" and isinstance(value, float):
            duration_seconds = value
        elif key == "upload_size_bytes" and isinstance(value, int):
            upload_size_bytes = value
        else:
            raise AssertionError(f"unsupported probe patch: {key}")
    return AudioProbeEvidence(
        container=container,
        codec=codec,
        has_audio_stream=has_audio_stream,
        duration_seconds=duration_seconds,
        upload_size_bytes=upload_size_bytes,
    )


def health(**patch: object) -> dict[str, object]:
    """Build a default healthy sidecar `/health` payload."""

    payload: dict[str, object] = {
        "status": "ok",
        "ready": True,
        "backend_profile_id": "stt_sv_en_primary",
        "backend_version": "2026-06-09",
        "gpu_ready": True,
        "capability_version": "stt-sidecar-v1",
    }
    payload.update(patch)
    return payload


def capabilities(**patch: object) -> dict[str, object]:
    """Build a default provider-neutral sidecar `/capabilities` payload."""

    payload: dict[str, object] = {
        "adapter_contract_version": "stt-sidecar-v1",
        "runtime": {
            "network_scope": "internal_only",
            "published_port_allowed": False,
            "gpu_required": True,
            "acceleration_family": "rocm",
            "acceleration_ready": True,
        },
        "media": media_capability(),
        "transcription": {
            "profile_label": "stt_sv_en_primary",
            "languages": ["auto", "sv", "en"],
            "word_timestamps_supported": True,
        },
        "diarization": {
            "profile_label": "diarization_sv_en_primary",
            "required_for_success": True,
            "modes": ["auto", "known_speaker_count", "speaker_range"],
            "exclusive_speaker_segments_supported": True,
        },
        "cache": {
            "cache_family": "huggingface",
            "host_root": "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            "container_root": "/cache/huggingface",
            "cache_roots_ready": True,
            "model_artifacts_present": True,
        },
        "secrets": {
            "required_secret_names": ["HUGGINGFACE_TOKEN"],
            "required_secrets_present": True,
            "values_exposed": False,
        },
    }
    for key, value in patch.items():
        existing = payload.get(key)
        if key == "media":
            payload[key] = value
        elif isinstance(existing, dict) and isinstance(value, dict):
            merged = dict(existing)
            merged.update(value)
            payload[key] = merged
        else:
            payload[key] = value
    return payload


def media_capability(
    *,
    normalized_audio: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build a sidecar media capability payload with normalized-audio truth."""

    media = media_capability_without_normalized_audio()
    if normalized_audio is None:
        media["normalized_audio"] = {
            "container": "wav",
            "sample_rate_hz": 16000,
            "channels": 1,
            "sample_format": "s16",
        }
    else:
        media["normalized_audio"] = normalized_audio
    return media


def media_capability_without_normalized_audio() -> dict[str, object]:
    """Build route-satisfying media caps while omitting normalized-audio truth."""

    return {
        "max_upload_bytes": 524288000,
        "max_duration_seconds": 7200,
        "accepted_containers": list(ACCEPTED_MEDIA_CONTAINERS),
        "input_protocols": ["local_upload"],
    }
