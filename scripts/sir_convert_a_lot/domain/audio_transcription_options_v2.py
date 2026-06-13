"""Transcript-bundle option validation helpers for Service API v2.

Purpose:
    Keep audio transcription public option validation and transcript formatter
    replay option validation out of the broader v2 job specification model.

Relationships:
    - Imported by `domain.specs_v2` so the v2 spec model can stay focused on
      cross-route request shape.
    - Shares governed audio error codes and formatter artifact constants with
      the audio transcription contract, replay contract, and formatter domain
      modules.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    FORBIDDEN_PUBLIC_BACKEND_OPTION_KEYS,
    AudioDiarizationMode,
    AudioTranscriptionErrorCode,
    AudioTranscriptionPublicOptions,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioDiarizationOptions as DomainAudioDiarizationOptions,
)
from scripts.sir_convert_a_lot.domain.transcript_formatter_artifacts import (
    CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT,
    TRANSCRIPT_OUTPUT_ARTIFACT_ORDER,
)

AUDIO_TRANSCRIPTION_OPTION_KEYS_V2 = frozenset(
    {"diarization", "language", "max_duration_seconds", "output_artifacts"}
)
TRANSCRIPT_FORMATTER_REPLAY_SCHEMA_VERSION = "transcript_formatter_replay_v1"


class AudioDiarizationOptionsV2(BaseModel):
    """Public speaker-hint options for audio transcription route admission."""

    model_config = ConfigDict(extra="forbid")

    mode: AudioDiarizationMode
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None


class AudioTranscriptionOptionsV2(BaseModel):
    """Public audio transcription options admitted through Service API v2."""

    model_config = ConfigDict(extra="forbid")

    language: str = "auto"
    diarization: AudioDiarizationOptionsV2
    max_duration_seconds: int = 7200
    output_artifacts: tuple[str, ...] = ("json",)

    @field_validator("output_artifacts", mode="before")
    @classmethod
    def _normalize_output_artifacts(cls, value: object) -> tuple[str, ...]:
        del cls
        return normalize_audio_output_artifacts(value)

    @model_validator(mode="before")
    @classmethod
    def _reject_unsupported_option_keys(cls, value: object) -> object:
        del cls
        return reject_unsupported_audio_option_keys(value)

    @model_validator(mode="after")
    def _validate_public_options(self) -> "AudioTranscriptionOptionsV2":
        diarization = DomainAudioDiarizationOptions(
            mode=self.diarization.mode,
            num_speakers=self.diarization.num_speakers,
            min_speakers=self.diarization.min_speakers,
            max_speakers=self.diarization.max_speakers,
        )
        options = AudioTranscriptionPublicOptions(
            language=self.language,
            diarization=diarization,
            max_duration_seconds=self.max_duration_seconds,
            output_artifacts=self.output_artifacts,
            raw_option_keys=AUDIO_TRANSCRIPTION_OPTION_KEYS_V2,
        )
        failure = options.validation_failure()
        if failure is not None:
            code, details = failure
            detail_text = ", ".join(f"{key}={value}" for key, value in sorted(details.items()))
            raise ValueError(f"{code.value}: {detail_text}")
        return self


class TranscriptFormatterRequestedArtifactV2(StrEnum):
    """Closed replay formatter artifact aliases accepted by Service API v2."""

    TXT = "txt"
    MD = "md"
    VTT = "vtt"
    SRT = "srt"


class SpeakerLabelOverrideV2(BaseModel):
    """Display-name override for one canonical transcript speaker label."""

    model_config = ConfigDict(extra="forbid")

    canonical_speaker_label: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("canonical_speaker_label")
    @classmethod
    def _validate_canonical_speaker_label(cls, value: str) -> str:
        del cls
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("speaker override values must not contain control characters")
        return value

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        del cls
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("speaker override values must not contain control characters")
        normalized = value.strip()
        if normalized == "":
            raise ValueError("display name must not be empty")
        return normalized


class TranscriptFormatterReplayOptionsV2(BaseModel):
    """Typed formatter replay options for canonical transcript JSON uploads."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transcript_formatter_replay_v1"]
    requested_artifacts: tuple[TranscriptFormatterRequestedArtifactV2, ...] = Field(min_length=1)
    speaker_label_overrides: tuple[SpeakerLabelOverrideV2, ...] = Field(min_length=1)

    @field_validator("requested_artifacts", mode="before")
    @classmethod
    def _normalize_requested_artifacts(cls, value: object) -> tuple[str, ...]:
        del cls
        return normalize_transcript_formatter_requested_artifacts(value)

    @field_validator("speaker_label_overrides", mode="before")
    @classmethod
    def _require_speaker_label_overrides(cls, value: object) -> object:
        del cls
        if isinstance(value, list | tuple) and not value:
            raise transcript_formatter_options_error(
                "at least one speaker label override is required"
            )
        return value

    @model_validator(mode="after")
    def _validate_uniqueness(self) -> "TranscriptFormatterReplayOptionsV2":
        labels: set[str] = set()
        display_names: set[str] = set()
        for override in self.speaker_label_overrides:
            if override.canonical_speaker_label in labels:
                raise ValueError("duplicate canonical speaker label")
            if override.display_name in display_names:
                raise ValueError("duplicate display name")
            labels.add(override.canonical_speaker_label)
            display_names.add(override.display_name)
        return self


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


def transcript_formatter_options_error(detail: str) -> ValueError:
    """Return a governed replay-options validation error."""

    return ValueError(detail)


def normalize_transcript_formatter_requested_artifacts(value: object) -> tuple[str, ...]:
    """Validate exact replay artifact aliases without admitting JSON as output."""

    if isinstance(value, str) or not isinstance(value, list | tuple):
        raise transcript_formatter_options_error("requested_artifacts must be a list")
    if not value:
        raise transcript_formatter_options_error("at least one requested artifact is required")
    allowed = {artifact.value for artifact in TranscriptFormatterRequestedArtifactV2}
    requested: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str) or entry == "":
            raise transcript_formatter_options_error("unsupported transcript formatter artifact")
        if entry not in allowed:
            raise transcript_formatter_options_error("unsupported transcript formatter artifact")
        if entry in seen:
            raise transcript_formatter_options_error("duplicate transcript formatter artifact")
        requested.append(entry)
        seen.add(entry)
    return tuple(requested)
