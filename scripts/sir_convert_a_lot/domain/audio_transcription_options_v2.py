"""Audio transcription option validation helpers for Service API v2.

Purpose:
    Keep audio-specific public option key validation and transcript formatter
    artifact alias normalization out of the broader v2 job specification model.

Relationships:
    - Imported by `domain.specs_v2` so the v2 spec model can stay focused on
      cross-route request shape.
    - Shares governed audio error codes and formatter artifact constants with
      the audio transcription contract and transcript formatter domain modules.
"""

from __future__ import annotations

from collections.abc import Mapping

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    FORBIDDEN_PUBLIC_BACKEND_OPTION_KEYS,
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.domain.transcript_formatter_artifacts import (
    CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT,
    TRANSCRIPT_OUTPUT_ARTIFACT_ORDER,
)

AUDIO_TRANSCRIPTION_OPTION_KEYS_V2 = frozenset(
    {"diarization", "language", "max_duration_seconds", "output_artifacts"}
)


def audio_public_options_error(detail: str) -> ValueError:
    """Return the governed v2 public-options validation error."""

    return ValueError(f"{AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED.value}: {detail}")


def normalize_audio_output_artifacts(value: object) -> tuple[str, ...]:
    """Normalize requested audio transcript artifacts with JSON as authority."""

    if value is None:
        return (CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT,)
    if isinstance(value, str) or not isinstance(value, list | tuple):
        raise audio_public_options_error("unsupported option 'output_artifacts'")
    requested: set[str] = set()
    for entry in value:
        if not isinstance(entry, str) or entry.strip() == "":
            raise audio_public_options_error("unsupported option 'output_artifacts'")
        normalized = entry.strip().lower()
        if normalized not in TRANSCRIPT_OUTPUT_ARTIFACT_ORDER:
            raise audio_public_options_error("unsupported option 'output_artifacts'")
        requested.add(normalized)
    requested.add(CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT)
    return tuple(artifact for artifact in TRANSCRIPT_OUTPUT_ARTIFACT_ORDER if artifact in requested)


def reject_unsupported_audio_option_keys(value: object) -> object:
    """Reject backend-native or unknown audio option keys before model coercion."""

    if not isinstance(value, Mapping):
        return value
    keys = frozenset(key for key in value.keys() if isinstance(key, str))
    forbidden = sorted(keys.intersection(FORBIDDEN_PUBLIC_BACKEND_OPTION_KEYS))
    if forbidden:
        raise audio_public_options_error(f"unsupported option '{forbidden[0]}'")
    unsupported = sorted(keys.difference(AUDIO_TRANSCRIPTION_OPTION_KEYS_V2))
    if unsupported:
        raise audio_public_options_error(f"unsupported option '{unsupported[0]}'")
    return value
