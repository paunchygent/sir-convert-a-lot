"""Audio transcription sidecar profile-proof data contracts.

Purpose:
    Define content-safe evidence and report shapes for speech-to-text sidecar
    profile-proof generation.

Relationships:
    - Shared by the STT profile-proof report builder and runner command.
    - References audio benchmark domain evidence without importing STT,
      diarization, Hugging Face, FFmpeg, or sidecar runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from scripts.sir_convert_a_lot.domain.audio_transcription_benchmark_profiles import (
    AudioBenchmarkEvidence,
    AudioBenchmarkReport,
)


class AudioTranscriptionRequiredEvidenceReport(TypedDict):
    """Required live evidence gates for STT profile proof."""

    live_hemma_evidence: bool
    sidecar_launch: bool
    codec_boundary: bool
    backend_dependencies: bool
    huggingface_readiness: bool
    swedish_fixture: bool
    english_fixture: bool
    exact_speaker_count: bool
    min_max_speaker_range: bool
    gpu_required_execution: bool
    batch_lifecycle: bool
    content_safety: bool
    route_unregistered: bool


class AudioTranscriptionProfileSelectionReport(TypedDict):
    """Profile-selection result for the STT sidecar proof report."""

    selected: bool
    stt_profile: str | None
    diarization_profile: str | None
    rejection_reasons: tuple[str, ...]


class AudioTranscriptionSidecarLaunchReport(TypedDict):
    """Content-safe sidecar launch/build contract evidence."""

    image_name: str
    image_tag: str
    compose_service: str
    build_contract: str
    launch_observed: bool
    isolated_runtime_marker: bool
    required_system_tools: tuple[str, ...]
    required_python_packages: tuple[str, ...]
    gpu_acceleration_required: bool
    hf_token_env_var_names: tuple[str, ...]
    hf_cache_env_var_names: tuple[str, ...]


class AudioTranscriptionCodecBoundaryReport(TypedDict):
    """Content-safe codec boundary evidence."""

    ffmpeg_available: bool
    ffprobe_available: bool
    supported_audio_codecs: tuple[str, ...]
    valid_audio_probe_exercised: bool
    bad_media_fails_closed: bool
    no_audio_fails_closed: bool
    unsupported_media_fails_closed: bool
    bounded_metadata_projected: bool


class AudioTranscriptionBackendDependencyReport(TypedDict):
    """Content-safe isolated runtime dependency evidence."""

    faster_whisper_importable: bool
    pyannote_audio_importable: bool
    huggingface_hub_importable: bool
    torch_importable: bool
    torchaudio_importable: bool
    torchcodec_audio_decoder_importable: bool
    sidecar_runtime_isolated: bool
    main_service_dependency_change_observed: bool


class AudioTranscriptionHuggingFaceReadinessReport(TypedDict):
    """Content-safe Hugging Face readiness evidence."""

    token_env_var_names: tuple[str, ...]
    token_env_vars_present: bool
    cache_status: str
    cache_roots_ready: bool
    model_access_status: str
    secret_values_exposed: bool
    private_cache_paths_exposed: bool
    raw_model_identifiers_exposed: bool


class AudioTranscriptionBatchLifecycleReport(TypedDict):
    """Content-safe 120-minute lifecycle evidence."""

    duration_seconds: float
    chunk_count: int
    max_chunk_duration_seconds: float
    progress_updates_observed: bool
    checkpoints_observed: bool
    detached_status_capable: bool
    cancel_semantics_observed: bool
    retry_semantics_observed: bool


class AudioTranscriptionRouteRegistrationReport(TypedDict):
    """Route safety evidence for the benchmark proof."""

    audio_transcript_bundle_registered: bool


class AudioTranscriptionSidecarProfileProofReport(TypedDict):
    """Content-safe live STT sidecar profile-proof report."""

    schema_version: str
    generated_at_utc: str
    evidence_mode: str
    proof_ready: bool
    required_evidence: AudioTranscriptionRequiredEvidenceReport
    profile_selection: AudioTranscriptionProfileSelectionReport
    sidecar_launch: AudioTranscriptionSidecarLaunchReport
    codec_boundary: AudioTranscriptionCodecBoundaryReport
    backend_dependencies: AudioTranscriptionBackendDependencyReport
    huggingface_readiness: AudioTranscriptionHuggingFaceReadinessReport
    benchmark: AudioBenchmarkReport
    batch_lifecycle: AudioTranscriptionBatchLifecycleReport
    route_registration: AudioTranscriptionRouteRegistrationReport


@dataclass(frozen=True, slots=True)
class AudioTranscriptionSidecarLaunchEvidence:
    """Sidecar image, build, package, GPU, and environment-name evidence."""

    image_name: str
    image_tag: str
    compose_service: str
    build_contract: str
    launch_observed: bool
    isolated_runtime_marker: bool
    required_system_tools: tuple[str, ...]
    required_python_packages: tuple[str, ...]
    gpu_acceleration_required: bool
    hf_token_env_var_names: tuple[str, ...]
    hf_cache_env_var_names: tuple[str, ...]
    environment_values_exposed: bool
    private_paths_exposed: bool
    raw_model_identifiers_exposed: bool


@dataclass(frozen=True, slots=True)
class AudioTranscriptionCodecBoundaryEvidence:
    """Codec probing and fail-closed media-boundary evidence."""

    ffmpeg_available: bool
    ffprobe_available: bool
    supported_audio_codecs: tuple[str, ...]
    valid_audio_probe_exercised: bool
    bad_media_fails_closed: bool
    no_audio_fails_closed: bool
    unsupported_media_fails_closed: bool
    bounded_metadata_projected: bool
    source_media_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AudioTranscriptionBackendDependencyEvidence:
    """Isolated sidecar dependency readiness evidence."""

    faster_whisper_importable: bool
    pyannote_audio_importable: bool
    huggingface_hub_importable: bool
    torch_importable: bool
    torchaudio_importable: bool
    torchcodec_audio_decoder_importable: bool
    sidecar_runtime_isolated: bool
    main_service_dependency_change_observed: bool


@dataclass(frozen=True, slots=True)
class AudioTranscriptionHuggingFaceReadinessEvidence:
    """Hugging Face token, cache, and bounded model-access evidence."""

    token_env_var_names: tuple[str, ...]
    token_env_vars_present: bool
    cache_roots_ready: bool
    cache_status: str
    model_access_status: str
    secret_values_exposed: bool
    private_cache_paths_exposed: bool
    raw_model_identifiers_exposed: bool
    token_value_samples: tuple[str, ...]
    private_cache_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AudioTranscriptionBatchLifecycleEvidence:
    """Long audio batch progress, checkpoint, cancel, and retry evidence."""

    duration_seconds: float
    chunk_count: int
    max_chunk_duration_seconds: float
    progress_updates_observed: bool
    checkpoints_observed: bool
    detached_status_capable: bool
    cancel_semantics_observed: bool
    retry_semantics_observed: bool


@dataclass(frozen=True, slots=True)
class AudioTranscriptionSidecarProfileProofEvidence:
    """Complete live evidence used to accept or reject STT profiles."""

    evidence_mode: str
    sidecar_launch: AudioTranscriptionSidecarLaunchEvidence
    codec_boundary: AudioTranscriptionCodecBoundaryEvidence
    backend_dependencies: AudioTranscriptionBackendDependencyEvidence
    huggingface_readiness: AudioTranscriptionHuggingFaceReadinessEvidence
    benchmark_evidence: AudioBenchmarkEvidence
    batch_lifecycle: AudioTranscriptionBatchLifecycleEvidence
    audio_transcript_route_registered: bool
    observation_failure_reasons: tuple[str, ...] = ()
