"""Speech-to-text audio route domain contracts and constants.

Purpose:
    Define the stable data language for audio transcription admission,
    sidecar readiness, route-level caps, and deterministic public error codes.

Relationships:
    - Imported by `domain.audio_transcription_policy` for admission and sidecar
      readiness decisions.
    - Aligns code-level route contracts with ADR-0013 and the audio converter
      contract across admission, sidecar readiness, and later execution slices.
    - Reuses `domain.specs.AccelerationPolicy` so GPU-required policy stays
      consistent with existing Sir Convert execution language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy
from scripts.sir_convert_a_lot.domain.transcript_formatter_artifacts import (
    TRANSCRIPT_OUTPUT_ARTIFACT_ORDER,
)

STT_SIDECAR_CONTRACT_VERSION = "stt-sidecar-v1"
MAX_AUDIO_UPLOAD_BYTES = 524_288_000
MAX_AUDIO_DURATION_SECONDS = 7_200
DAY_ONE_OUTPUT_ARTIFACTS: frozenset[str] = frozenset(TRANSCRIPT_OUTPUT_ARTIFACT_ORDER)
DAY_ONE_LANGUAGE_VALUES: frozenset[str] = frozenset({"auto", "sv", "en"})
DAY_ONE_MEDIA_CONTAINERS: frozenset[str] = frozenset(
    {
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
    }
)
FORBIDDEN_PUBLIC_BACKEND_OPTION_KEYS: frozenset[str] = frozenset(
    {
        "backend_profile_id",
        "beam_size",
        "cache_path",
        "compute_type",
        "device",
        "diarization_model_id",
        "model_id",
        "model_path",
        "prompt",
        "quantization",
        "stt_model_id",
        "vad_filter",
    }
)
FORBIDDEN_SIDECAR_CAPABILITY_KEYS: frozenset[str] = frozenset(
    {
        "access_token",
        "beam_size",
        "compute_type",
        "diarization_model_id",
        "model_id",
        "model_path",
        "prompt",
        "quantization",
        "secret_value",
        "stt_model_id",
        "token",
        "vad_filter",
    }
)
_ALLOWED_PUBLIC_OPTION_KEYS: frozenset[str] = frozenset(
    {"diarization", "language", "max_duration_seconds", "output_artifacts"}
)


class AudioTranscriptionErrorCode(StrEnum):
    """Deterministic public error codes for the audio route."""

    ROUTE_DISABLED = "audio_route_disabled"
    ROUTE_CAPACITY_EXCEEDED = "audio_route_capacity_exceeded"
    UPLOAD_SIZE_EXCEEDED = "audio_upload_size_exceeded"
    INPUT_PROTOCOL_UNSUPPORTED = "audio_input_protocol_unsupported"
    STREAM_MISSING = "audio_stream_missing"
    CONTAINER_UNSUPPORTED = "audio_container_unsupported"
    UNSUPPORTED_CODEC = "unsupported_audio_codec"
    DURATION_EXCEEDED = "audio_duration_exceeded"
    PROBE_FAILED = "audio_probe_failed"
    PROBE_TIMEOUT = "audio_probe_timeout"
    NORMALIZATION_FAILED = "audio_normalization_failed"
    NORMALIZATION_TIMEOUT = "audio_normalization_timeout"
    SIDECAR_UNAVAILABLE = "audio_sidecar_unavailable"
    TRANSCRIPTION_BACKEND_UNAVAILABLE = "audio_transcription_backend_unavailable"
    DIARIZATION_BACKEND_UNAVAILABLE = "audio_diarization_backend_unavailable"
    MODEL_CACHE_UNAVAILABLE = "audio_model_cache_unavailable"
    MODEL_ACCESS_DENIED = "audio_model_access_denied"
    GPU_REQUIRED_UNAVAILABLE = "audio_gpu_required_unavailable"
    TRANSCRIPTION_FAILED = "audio_transcription_failed"
    DIARIZATION_FAILED = "audio_diarization_failed"
    SEGMENT_ALIGNMENT_FAILED = "audio_segment_alignment_failed"
    SIDECAR_CANCELED = "audio_sidecar_canceled"
    TRANSCRIPT_ARTIFACT_UNAVAILABLE = "audio_transcript_artifact_unavailable"
    DIARIZATION_OPTIONS_INVALID = "audio_diarization_options_invalid"
    PUBLIC_OPTIONS_UNSUPPORTED = "audio_public_options_unsupported"
    RETENTION_PIN_UNSUPPORTED = "audio_retention_pin_unsupported"


class AudioAdmissionQueueBehavior(StrEnum):
    """Route admission behavior once one of the concrete caps is exhausted."""

    REJECT = "reject"


class AudioInputProtocol(StrEnum):
    """Accepted source protocol classes for uploaded audio media."""

    LOCAL_UPLOAD = "local_upload"
    REMOTE_URL = "remote_url"
    FILE_PATH = "file_path"
    DEVICE = "device"
    PLAYLIST = "playlist"


class AudioDiarizationMode(StrEnum):
    """Public diarization speaker-hint modes accepted by the audio route policy."""

    AUTO = "auto"
    KNOWN_SPEAKER_COUNT = "known_speaker_count"
    SPEAKER_RANGE = "speaker_range"


@dataclass(frozen=True, slots=True)
class AudioTranscriptionCaps:
    """Concrete route-level caps for a single Sir Convert service instance."""

    max_active_stt_jobs_per_instance: int
    max_active_probe_normalization_workers: int
    max_active_sidecar_transcription_requests: int
    gpu_slots_per_instance: int
    queue_behavior: AudioAdmissionQueueBehavior
    capacity_error_code: AudioTranscriptionErrorCode


DEFAULT_AUDIO_TRANSCRIPTION_CAPS = AudioTranscriptionCaps(
    max_active_stt_jobs_per_instance=2,
    max_active_probe_normalization_workers=2,
    max_active_sidecar_transcription_requests=1,
    gpu_slots_per_instance=1,
    queue_behavior=AudioAdmissionQueueBehavior.REJECT,
    capacity_error_code=AudioTranscriptionErrorCode.ROUTE_CAPACITY_EXCEEDED,
)


@dataclass(frozen=True, slots=True)
class AudioTranscriptionCapacitySnapshot:
    """Current route occupancy used for deterministic admission decisions."""

    active_stt_jobs: int
    active_probe_normalization_workers: int
    active_sidecar_transcription_requests: int
    gpu_slots_in_use: int

    @classmethod
    def empty(cls) -> "AudioTranscriptionCapacitySnapshot":
        """Return a zero-occupancy capacity snapshot."""

        return cls(
            active_stt_jobs=0,
            active_probe_normalization_workers=0,
            active_sidecar_transcription_requests=0,
            gpu_slots_in_use=0,
        )

    def exhausted_by(self, caps: AudioTranscriptionCaps) -> str | None:
        """Return the exhausted cap name, or `None` when capacity is available."""

        if self.active_stt_jobs >= caps.max_active_stt_jobs_per_instance:
            return "max_active_stt_jobs_per_instance"
        if self.active_probe_normalization_workers >= caps.max_active_probe_normalization_workers:
            return "max_active_probe_normalization_workers"
        if (
            self.active_sidecar_transcription_requests
            >= caps.max_active_sidecar_transcription_requests
        ):
            return "max_active_sidecar_transcription_requests"
        if self.gpu_slots_in_use >= caps.gpu_slots_per_instance:
            return "gpu_slots_per_instance"
        return None


@dataclass(frozen=True, slots=True)
class AudioDiarizationOptions:
    """Public speaker-hint options for fail-closed diarization."""

    mode: AudioDiarizationMode
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None

    def validation_error(self) -> str | None:
        """Return a stable validation reason, or `None` when options are valid."""

        if self.mode == AudioDiarizationMode.AUTO:
            if (
                self.num_speakers is not None
                or self.min_speakers is not None
                or self.max_speakers is not None
            ):
                return "auto_forbids_speaker_hints"
            return None
        if self.mode == AudioDiarizationMode.KNOWN_SPEAKER_COUNT:
            if self.num_speakers is None or self.num_speakers < 1:
                return "known_speaker_count_requires_positive_num_speakers"
            if self.min_speakers is not None or self.max_speakers is not None:
                return "known_speaker_count_forbids_speaker_range"
            return None
        if self.mode == AudioDiarizationMode.SPEAKER_RANGE:
            if self.num_speakers is not None:
                return "speaker_range_forbids_num_speakers"
            if self.min_speakers is None or self.max_speakers is None:
                return "speaker_range_requires_min_and_max_speakers"
            if self.min_speakers < 1:
                return "speaker_range_requires_positive_min_speakers"
            if self.max_speakers < self.min_speakers:
                return "speaker_range_requires_max_greater_or_equal_min"
            return None
        return "unsupported_diarization_mode"


@dataclass(frozen=True, slots=True)
class AudioTranscriptionPublicOptions:
    """Public request options allowed before backend-native routing exists."""

    language: str
    diarization: AudioDiarizationOptions
    max_duration_seconds: int
    output_artifacts: tuple[str, ...]
    raw_option_keys: frozenset[str] = field(default_factory=frozenset)

    def validation_failure(self) -> tuple[AudioTranscriptionErrorCode, dict[str, str]] | None:
        """Return the first public option failure in deterministic order."""

        forbidden = sorted(self.raw_option_keys.intersection(FORBIDDEN_PUBLIC_BACKEND_OPTION_KEYS))
        if forbidden:
            return (
                AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED,
                {"unsupported_option": forbidden[0]},
            )
        unsupported_keys = sorted(self.raw_option_keys.difference(_ALLOWED_PUBLIC_OPTION_KEYS))
        if unsupported_keys:
            return (
                AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED,
                {"unsupported_option": unsupported_keys[0]},
            )
        if self.language not in DAY_ONE_LANGUAGE_VALUES:
            return (
                AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED,
                {"unsupported_option": "language"},
            )
        unsupported_artifacts = sorted(
            artifact
            for artifact in self.output_artifacts
            if artifact not in DAY_ONE_OUTPUT_ARTIFACTS
        )
        if unsupported_artifacts:
            return (
                AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED,
                {"unsupported_option": "output_artifacts"},
            )
        diarization_failure = self.diarization.validation_error()
        if diarization_failure is not None:
            return (
                AudioTranscriptionErrorCode.DIARIZATION_OPTIONS_INVALID,
                {"reason": diarization_failure},
            )
        if self.max_duration_seconds <= 0:
            return (
                AudioTranscriptionErrorCode.DURATION_EXCEEDED,
                {
                    "minimum_seconds": "1",
                    "reason": "max_duration_seconds_must_be_positive",
                },
            )
        if self.max_duration_seconds > MAX_AUDIO_DURATION_SECONDS:
            return (
                AudioTranscriptionErrorCode.DURATION_EXCEEDED,
                {"limit_seconds": str(MAX_AUDIO_DURATION_SECONDS)},
            )
        return None


@dataclass(frozen=True, slots=True)
class AudioProbeEvidence:
    """Media-probe facts consumed by route admission before sidecar execution."""

    container: str
    codec: str
    has_audio_stream: bool
    duration_seconds: float
    upload_size_bytes: int


@dataclass(frozen=True, slots=True)
class AudioTranscriptionRouteRequest:
    """Route-admission request facts independent of HTTP transport details."""

    route_enabled: bool
    input_protocol: AudioInputProtocol
    acceleration_policy: AccelerationPolicy
    retention_pin: bool
    public_options: AudioTranscriptionPublicOptions


@dataclass(frozen=True, slots=True)
class AudioTranscriptionPolicyDecision:
    """Accepted or rejected route-admission decision with public diagnostics."""

    accepted: bool
    error_code: AudioTranscriptionErrorCode | None = None
    details: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SttSidecarReadinessDecision:
    """Fail-closed readiness decision for the internal STT sidecar contract."""

    ready: bool
    error_code: AudioTranscriptionErrorCode | None = None
    details: dict[str, str] = field(default_factory=dict)
    profile_labels: dict[str, str] = field(default_factory=dict)
