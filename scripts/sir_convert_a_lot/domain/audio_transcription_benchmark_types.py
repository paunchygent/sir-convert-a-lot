"""Audio transcription benchmark evidence data contracts.

Purpose:
    Define typed benchmark evidence objects and content-safe report shapes used
    to evaluate speech-to-text and diarization profile readiness.

Relationships:
    - Supplies immutable evidence records for
      `domain.audio_transcription_benchmark_profiles`.
    - References audio transcription public error-code language without
      importing STT, diarization, Hugging Face, FFmpeg, or sidecar runtimes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import NotRequired, TypedDict

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)


class _Unspecified:
    """Sentinel type for copy helpers where `None` is a meaningful value."""


_UNSPECIFIED = _Unspecified()


class BenchmarkBackendFamily(StrEnum):
    """Bounded backend families allowed in benchmark profile evidence."""

    FASTER_WHISPER = "faster_whisper"
    PYANNOTE_AUDIO = "pyannote_audio"


class BenchmarkProfileSelectionStatus(StrEnum):
    """Profile-selection result for the first audio transcription slice."""

    SELECTED = "selected"
    REJECTED = "rejected"


class AudioBenchmarkProfileReport(TypedDict):
    """Content-safe selected profile labels for public benchmark reports."""

    stt_profile: str
    diarization_profile: str
    stt_backend_family: str
    diarization_backend_family: str


class AudioBenchmarkFixtureReport(TypedDict):
    """Content-safe per-fixture evidence for public benchmark reports."""

    detected_language: str
    diarized_segment_count: int
    exclusive_speaker_segments: bool
    fixture_label: str
    language: str
    alignment_suitable: bool
    word_timestamps_available: bool


class AudioBenchmarkRuntimeReport(TypedDict):
    """Content-safe runtime evidence for public benchmark reports."""

    acceleration_family: str
    gpu_execution_confirmed: bool
    cpu_fallback_observed: bool
    cache_family: str
    cache_reuse_observed: bool
    cache_roots_ready: bool
    missing_model_access_failure_code: str
    required_secret_names: tuple[str, ...]


class AudioBenchmarkSpeakerHintReport(TypedDict):
    """Content-safe speaker-hint evidence for public benchmark reports."""

    exact_speaker_count_supported: bool
    exact_speaker_count_exercised: bool
    min_max_speaker_range_supported: bool
    min_max_speaker_range_exercised: bool


class AudioBenchmarkDurationReport(TypedDict):
    """Content-safe duration feasibility evidence for public benchmark reports."""

    proof_kind: str
    duration_seconds: float
    chunk_count: int
    max_chunk_duration_seconds: float
    lifecycle_assumptions_exercised: bool


class AudioBenchmarkReport(TypedDict):
    """Content-safe benchmark report projection."""

    profiles: AudioBenchmarkProfileReport
    runtime: AudioBenchmarkRuntimeReport
    fixtures: list[AudioBenchmarkFixtureReport]
    speaker_hints: AudioBenchmarkSpeakerHintReport
    duration: AudioBenchmarkDurationReport
    selected: bool
    rejection_reasons: tuple[str, ...]
    hemma_evidence_path: NotRequired[str]


@dataclass(frozen=True, slots=True)
class AudioBenchmarkProfileLabels:
    """Public profile labels plus private backend-family evidence."""

    stt_profile: str
    diarization_profile: str
    stt_backend_family: BenchmarkBackendFamily
    diarization_backend_family: BenchmarkBackendFamily
    raw_model_identifiers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AudioBenchmarkRuntimeEvidence:
    """GPU, cache, and model-access evidence for profile selection."""

    acceleration_family: str
    gpu_execution_confirmed: bool
    cpu_fallback_observed: bool
    cache_family: str
    cache_reuse_observed: bool
    cache_roots_ready: bool
    missing_model_access_failure_code: AudioTranscriptionErrorCode | None
    required_secret_names: tuple[str, ...]
    required_secret_values_exposed: bool
    private_cache_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AudioBenchmarkLanguageEvidence:
    """Content-safe fixture evidence for one benchmark language."""

    fixture_label: str
    language: str
    detected_language: str
    diarized_segment_count: int
    exclusive_speaker_segments: bool
    alignment_suitable: bool
    word_timestamps_available: bool
    transcript_text_retained: bool
    transcript_text_samples: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AudioBenchmarkSpeakerHintEvidence:
    """Diarization speaker-hint support and exercised-mode evidence."""

    exact_speaker_count_supported: bool
    exact_speaker_count_exercised: bool
    min_max_speaker_range_supported: bool
    min_max_speaker_range_exercised: bool


@dataclass(frozen=True, slots=True)
class AudioBenchmarkSyntheticDurationEvidence:
    """120-minute fixture or synthetic-duration feasibility evidence."""

    proof_kind: str
    duration_seconds: float
    chunk_count: int
    max_chunk_duration_seconds: float
    lifecycle_assumptions_exercised: bool


@dataclass(frozen=True, slots=True)
class AudioBenchmarkContentSafetyEvidence:
    """Content-safety assertions for persisted benchmark reports."""

    transcript_text_in_report: bool
    raw_model_ids_in_report: bool
    secret_values_in_report: bool
    private_paths_in_report: bool
    generated_artifacts_in_repo: bool


@dataclass(frozen=True, slots=True)
class AudioBenchmarkEvidence:
    """Complete benchmark evidence used to select or reject profiles."""

    profiles: AudioBenchmarkProfileLabels
    runtime: AudioBenchmarkRuntimeEvidence
    language_evidence: tuple[AudioBenchmarkLanguageEvidence, ...]
    speaker_hints: AudioBenchmarkSpeakerHintEvidence
    duration: AudioBenchmarkSyntheticDurationEvidence
    content_safety: AudioBenchmarkContentSafetyEvidence
    hemma_evidence_path: str | None = None

    def with_profiles(
        self,
        *,
        stt_profile: str | None = None,
        diarization_profile: str | None = None,
        stt_backend_family: BenchmarkBackendFamily | None = None,
        diarization_backend_family: BenchmarkBackendFamily | None = None,
        raw_model_identifiers: tuple[str, ...] | None = None,
    ) -> "AudioBenchmarkEvidence":
        """Return a copy with updated profile evidence."""

        return replace(
            self,
            profiles=replace(
                self.profiles,
                stt_profile=stt_profile if stt_profile is not None else self.profiles.stt_profile,
                diarization_profile=diarization_profile
                if diarization_profile is not None
                else self.profiles.diarization_profile,
                stt_backend_family=stt_backend_family
                if stt_backend_family is not None
                else self.profiles.stt_backend_family,
                diarization_backend_family=diarization_backend_family
                if diarization_backend_family is not None
                else self.profiles.diarization_backend_family,
                raw_model_identifiers=raw_model_identifiers
                if raw_model_identifiers is not None
                else self.profiles.raw_model_identifiers,
            ),
        )

    def with_runtime(
        self,
        *,
        acceleration_family: str | None = None,
        gpu_execution_confirmed: bool | None = None,
        cpu_fallback_observed: bool | None = None,
        cache_family: str | None = None,
        cache_reuse_observed: bool | None = None,
        cache_roots_ready: bool | None = None,
        missing_model_access_failure_code: (
            AudioTranscriptionErrorCode | None | _Unspecified
        ) = _UNSPECIFIED,
        required_secret_names: tuple[str, ...] | None = None,
        required_secret_values_exposed: bool | None = None,
        private_cache_paths: tuple[str, ...] | None = None,
    ) -> "AudioBenchmarkEvidence":
        """Return a copy with updated runtime evidence."""

        return replace(
            self,
            runtime=replace(
                self.runtime,
                acceleration_family=acceleration_family
                if acceleration_family is not None
                else self.runtime.acceleration_family,
                gpu_execution_confirmed=gpu_execution_confirmed
                if gpu_execution_confirmed is not None
                else self.runtime.gpu_execution_confirmed,
                cpu_fallback_observed=cpu_fallback_observed
                if cpu_fallback_observed is not None
                else self.runtime.cpu_fallback_observed,
                cache_family=cache_family
                if cache_family is not None
                else self.runtime.cache_family,
                cache_reuse_observed=cache_reuse_observed
                if cache_reuse_observed is not None
                else self.runtime.cache_reuse_observed,
                cache_roots_ready=cache_roots_ready
                if cache_roots_ready is not None
                else self.runtime.cache_roots_ready,
                missing_model_access_failure_code=missing_model_access_failure_code
                if not isinstance(missing_model_access_failure_code, _Unspecified)
                else self.runtime.missing_model_access_failure_code,
                required_secret_names=required_secret_names
                if required_secret_names is not None
                else self.runtime.required_secret_names,
                required_secret_values_exposed=required_secret_values_exposed
                if required_secret_values_exposed is not None
                else self.runtime.required_secret_values_exposed,
                private_cache_paths=private_cache_paths
                if private_cache_paths is not None
                else self.runtime.private_cache_paths,
            ),
        )

    def with_speaker_hints(
        self,
        *,
        exact_speaker_count_supported: bool | None = None,
        exact_speaker_count_exercised: bool | None = None,
        min_max_speaker_range_supported: bool | None = None,
        min_max_speaker_range_exercised: bool | None = None,
    ) -> "AudioBenchmarkEvidence":
        """Return a copy with updated diarization speaker-hint evidence."""

        return replace(
            self,
            speaker_hints=replace(
                self.speaker_hints,
                exact_speaker_count_supported=exact_speaker_count_supported
                if exact_speaker_count_supported is not None
                else self.speaker_hints.exact_speaker_count_supported,
                exact_speaker_count_exercised=exact_speaker_count_exercised
                if exact_speaker_count_exercised is not None
                else self.speaker_hints.exact_speaker_count_exercised,
                min_max_speaker_range_supported=min_max_speaker_range_supported
                if min_max_speaker_range_supported is not None
                else self.speaker_hints.min_max_speaker_range_supported,
                min_max_speaker_range_exercised=min_max_speaker_range_exercised
                if min_max_speaker_range_exercised is not None
                else self.speaker_hints.min_max_speaker_range_exercised,
            ),
        )

    def with_duration(
        self,
        *,
        proof_kind: str | None = None,
        duration_seconds: float | None = None,
        chunk_count: int | None = None,
        max_chunk_duration_seconds: float | None = None,
        lifecycle_assumptions_exercised: bool | None = None,
    ) -> "AudioBenchmarkEvidence":
        """Return a copy with updated 120-minute feasibility evidence."""

        return replace(
            self,
            duration=replace(
                self.duration,
                proof_kind=proof_kind if proof_kind is not None else self.duration.proof_kind,
                duration_seconds=duration_seconds
                if duration_seconds is not None
                else self.duration.duration_seconds,
                chunk_count=chunk_count if chunk_count is not None else self.duration.chunk_count,
                max_chunk_duration_seconds=max_chunk_duration_seconds
                if max_chunk_duration_seconds is not None
                else self.duration.max_chunk_duration_seconds,
                lifecycle_assumptions_exercised=lifecycle_assumptions_exercised
                if lifecycle_assumptions_exercised is not None
                else self.duration.lifecycle_assumptions_exercised,
            ),
        )


@dataclass(frozen=True, slots=True)
class AudioBenchmarkProfileSelectionDecision:
    """Selected profile labels or deterministic rejection reasons."""

    status: BenchmarkProfileSelectionStatus
    stt_profile: str | None
    diarization_profile: str | None
    rejection_reasons: tuple[str, ...]
