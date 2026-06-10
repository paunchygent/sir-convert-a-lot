"""Audio transcription sidecar profile-proof reports.

Purpose:
    Build content-safe live benchmark proof reports for speech-to-text sidecar
    profile selection.

Relationships:
    - Consumes audio transcription benchmark evidence from the domain layer.
    - Adds Hemma sidecar proof evidence for codec probing, isolated runtime
      dependencies, Hugging Face readiness, long-job lifecycle behavior, and
      route safety.
    - Writes generated verification artifacts without importing STT,
      diarization, Hugging Face, FFmpeg, or sidecar runtime dependencies.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import (
    enforce_generated_output_path,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_contracts import (
    AudioTranscriptionBackendDependencyEvidence,
    AudioTranscriptionBackendDependencyReport,
    AudioTranscriptionBatchLifecycleEvidence,
    AudioTranscriptionBatchLifecycleReport,
    AudioTranscriptionCodecBoundaryEvidence,
    AudioTranscriptionCodecBoundaryReport,
    AudioTranscriptionHuggingFaceReadinessEvidence,
    AudioTranscriptionHuggingFaceReadinessReport,
    AudioTranscriptionProfileSelectionReport,
    AudioTranscriptionRequiredEvidenceReport,
    AudioTranscriptionSidecarLaunchEvidence,
    AudioTranscriptionSidecarLaunchReport,
    AudioTranscriptionSidecarProfileProofEvidence,
    AudioTranscriptionSidecarProfileProofReport,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_benchmark_profiles import (
    AudioBenchmarkEvidence,
    BenchmarkProfileSelectionStatus,
    build_content_safe_audio_benchmark_report,
    evaluate_audio_benchmark_profile_selection,
)

PROFILE_PROOF_SCHEMA_VERSION = "audio_transcription_sidecar_profile_proof_v1"
REQUIRED_COMMON_AUDIO_CODECS = ("aac", "flac", "m4a", "mp3", "ogg", "opus", "wav")
REQUIRED_SYSTEM_TOOLS = ("ffmpeg", "ffprobe")
REQUIRED_PYTHON_PACKAGES = (
    "faster-whisper",
    "huggingface_hub",
    "pyannote.audio",
    "torch",
    "torchaudio",
    "torchcodec",
)
REQUIRED_HF_TOKEN_ENV_VARS = ("HF_TOKEN",)
REQUIRED_HF_CACHE_ENV_VARS = ("HF_HOME", "HF_HUB_CACHE")
REQUIRED_SIDECAR_IMAGE_NAME = "sir-convert-a-lot-stt-sidecar"
REQUIRED_SIDECAR_COMPOSE_SERVICE = "stt-sidecar-benchmark"
REQUIRED_LIVE_EVIDENCE_MODE = "live_hemma"
REQUIRED_BATCH_DURATION_SECONDS = 7_200.0


def build_live_profile_proof_report(
    evidence: AudioTranscriptionSidecarProfileProofEvidence,
) -> AudioTranscriptionSidecarProfileProofReport:
    """Build a content-safe live STT sidecar profile-proof report."""

    required_evidence = _required_evidence_report(evidence)
    rejection_reasons = tuple(_profile_proof_rejection_reasons(evidence, required_evidence))
    profile_decision = evaluate_audio_benchmark_profile_selection(evidence.benchmark_evidence)
    selected = (
        not rejection_reasons
        and profile_decision.status is BenchmarkProfileSelectionStatus.SELECTED
    )
    profile_report: AudioTranscriptionProfileSelectionReport = {
        "selected": selected,
        "stt_profile": profile_decision.stt_profile if selected else None,
        "diarization_profile": profile_decision.diarization_profile if selected else None,
        "rejection_reasons": rejection_reasons,
    }
    return {
        "schema_version": PROFILE_PROOF_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "evidence_mode": evidence.evidence_mode,
        "proof_ready": selected,
        "required_evidence": required_evidence,
        "profile_selection": profile_report,
        "sidecar_launch": _sidecar_launch_report(evidence.sidecar_launch),
        "codec_boundary": _codec_boundary_report(evidence.codec_boundary),
        "backend_dependencies": _backend_dependency_report(evidence.backend_dependencies),
        "huggingface_readiness": _huggingface_readiness_report(
            evidence.huggingface_readiness,
        ),
        "benchmark": build_content_safe_audio_benchmark_report(evidence.benchmark_evidence),
        "batch_lifecycle": _batch_lifecycle_report(evidence.batch_lifecycle),
        "route_registration": {
            "audio_transcript_bundle_registered": evidence.audio_transcript_route_registered,
        },
    }


def write_live_profile_proof_report(
    report: AudioTranscriptionSidecarProfileProofReport,
    *,
    output_root: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown profile-proof reports under a generated root."""

    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "profile-proof.json"
    report_markdown_path = output_root / "profile-proof.md"
    report_json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_markdown_path.write_text(
        _render_profile_proof_markdown(report),
        encoding="utf-8",
    )
    return report_json_path, report_markdown_path


def _required_evidence_report(
    evidence: AudioTranscriptionSidecarProfileProofEvidence,
) -> AudioTranscriptionRequiredEvidenceReport:
    benchmark_evidence = evidence.benchmark_evidence
    return {
        "live_hemma_evidence": evidence.evidence_mode == REQUIRED_LIVE_EVIDENCE_MODE,
        "sidecar_launch": _sidecar_launch_ready(evidence.sidecar_launch),
        "codec_boundary": _codec_boundary_ready(evidence.codec_boundary),
        "backend_dependencies": _backend_dependencies_ready(evidence.backend_dependencies),
        "huggingface_readiness": _huggingface_readiness_ready(
            evidence.huggingface_readiness,
        ),
        "swedish_fixture": _language_fixture_ready(benchmark_evidence, "sv"),
        "english_fixture": _language_fixture_ready(benchmark_evidence, "en"),
        "exact_speaker_count": (
            benchmark_evidence.speaker_hints.exact_speaker_count_supported
            and benchmark_evidence.speaker_hints.exact_speaker_count_exercised
        ),
        "min_max_speaker_range": (
            benchmark_evidence.speaker_hints.min_max_speaker_range_supported
            and benchmark_evidence.speaker_hints.min_max_speaker_range_exercised
        ),
        "gpu_required_execution": _gpu_required_execution_ready(benchmark_evidence),
        "batch_lifecycle": _batch_lifecycle_ready(evidence.batch_lifecycle),
        "content_safety": _content_safety_ready(evidence),
        "route_unregistered": not evidence.audio_transcript_route_registered,
    }


def _profile_proof_rejection_reasons(
    evidence: AudioTranscriptionSidecarProfileProofEvidence,
    required_evidence: AudioTranscriptionRequiredEvidenceReport,
) -> list[str]:
    reasons = list(evidence.observation_failure_reasons)
    if not required_evidence["live_hemma_evidence"]:
        reasons.append("live_hemma_evidence_missing")
    if not required_evidence["sidecar_launch"]:
        reasons.append("sidecar_launch_not_ready")
    if not required_evidence["codec_boundary"]:
        reasons.append("codec_boundary_not_proven")
    if not required_evidence["backend_dependencies"]:
        reasons.append("backend_dependencies_not_ready")
    if not required_evidence["huggingface_readiness"]:
        reasons.append("huggingface_readiness_not_ready")
    if not required_evidence["gpu_required_execution"]:
        reasons.append("gpu_required_execution_not_proven")
    if not required_evidence["batch_lifecycle"]:
        reasons.append("120_minute_lifecycle_not_proven")
    if not required_evidence["content_safety"]:
        reasons.append("content_safety_not_proven")
    if not required_evidence["route_unregistered"]:
        reasons.append("route_registration_observed")
    profile_decision = evaluate_audio_benchmark_profile_selection(evidence.benchmark_evidence)
    for reason in profile_decision.rejection_reasons:
        if reason not in reasons:
            reasons.append(reason)
    return reasons


def _sidecar_launch_report(
    evidence: AudioTranscriptionSidecarLaunchEvidence,
) -> AudioTranscriptionSidecarLaunchReport:
    return {
        "image_name": evidence.image_name,
        "image_tag": evidence.image_tag,
        "compose_service": evidence.compose_service,
        "build_contract": evidence.build_contract,
        "launch_observed": evidence.launch_observed,
        "isolated_runtime_marker": evidence.isolated_runtime_marker,
        "required_system_tools": tuple(
            tool for tool in REQUIRED_SYSTEM_TOOLS if tool in set(evidence.required_system_tools)
        ),
        "required_python_packages": tuple(
            package
            for package in REQUIRED_PYTHON_PACKAGES
            if package in set(evidence.required_python_packages)
        ),
        "gpu_acceleration_required": evidence.gpu_acceleration_required,
        "hf_token_env_var_names": tuple(
            name
            for name in REQUIRED_HF_TOKEN_ENV_VARS
            if name in set(evidence.hf_token_env_var_names)
        ),
        "hf_cache_env_var_names": tuple(
            name
            for name in REQUIRED_HF_CACHE_ENV_VARS
            if name in set(evidence.hf_cache_env_var_names)
        ),
    }


def _codec_boundary_report(
    evidence: AudioTranscriptionCodecBoundaryEvidence,
) -> AudioTranscriptionCodecBoundaryReport:
    return {
        "ffmpeg_available": evidence.ffmpeg_available,
        "ffprobe_available": evidence.ffprobe_available,
        "supported_audio_codecs": tuple(
            codec
            for codec in REQUIRED_COMMON_AUDIO_CODECS
            if codec in set(evidence.supported_audio_codecs)
        ),
        "valid_audio_probe_exercised": evidence.valid_audio_probe_exercised,
        "bad_media_fails_closed": evidence.bad_media_fails_closed,
        "no_audio_fails_closed": evidence.no_audio_fails_closed,
        "unsupported_media_fails_closed": evidence.unsupported_media_fails_closed,
        "bounded_metadata_projected": evidence.bounded_metadata_projected,
    }


def _backend_dependency_report(
    evidence: AudioTranscriptionBackendDependencyEvidence,
) -> AudioTranscriptionBackendDependencyReport:
    return {
        "faster_whisper_importable": evidence.faster_whisper_importable,
        "pyannote_audio_importable": evidence.pyannote_audio_importable,
        "huggingface_hub_importable": evidence.huggingface_hub_importable,
        "torch_importable": evidence.torch_importable,
        "torchaudio_importable": evidence.torchaudio_importable,
        "torchcodec_audio_decoder_importable": (evidence.torchcodec_audio_decoder_importable),
        "sidecar_runtime_isolated": evidence.sidecar_runtime_isolated,
        "main_service_dependency_change_observed": (
            evidence.main_service_dependency_change_observed
        ),
    }


def _huggingface_readiness_report(
    evidence: AudioTranscriptionHuggingFaceReadinessEvidence,
) -> AudioTranscriptionHuggingFaceReadinessReport:
    return {
        "token_env_var_names": evidence.token_env_var_names,
        "token_env_vars_present": evidence.token_env_vars_present,
        "cache_status": evidence.cache_status,
        "cache_roots_ready": evidence.cache_roots_ready,
        "model_access_status": evidence.model_access_status,
        "secret_values_exposed": evidence.secret_values_exposed,
        "private_cache_paths_exposed": evidence.private_cache_paths_exposed,
        "raw_model_identifiers_exposed": evidence.raw_model_identifiers_exposed,
    }


def _batch_lifecycle_report(
    evidence: AudioTranscriptionBatchLifecycleEvidence,
) -> AudioTranscriptionBatchLifecycleReport:
    return {
        "duration_seconds": evidence.duration_seconds,
        "chunk_count": evidence.chunk_count,
        "max_chunk_duration_seconds": evidence.max_chunk_duration_seconds,
        "progress_updates_observed": evidence.progress_updates_observed,
        "checkpoints_observed": evidence.checkpoints_observed,
        "detached_status_capable": evidence.detached_status_capable,
        "cancel_semantics_observed": evidence.cancel_semantics_observed,
        "retry_semantics_observed": evidence.retry_semantics_observed,
    }


def _sidecar_launch_ready(evidence: AudioTranscriptionSidecarLaunchEvidence) -> bool:
    return (
        evidence.image_name == REQUIRED_SIDECAR_IMAGE_NAME
        and bool(evidence.image_tag)
        and evidence.compose_service == REQUIRED_SIDECAR_COMPOSE_SERVICE
        and evidence.build_contract == "buildkit"
        and evidence.launch_observed
        and evidence.isolated_runtime_marker
        and set(REQUIRED_SYSTEM_TOOLS).issubset(evidence.required_system_tools)
        and set(REQUIRED_PYTHON_PACKAGES).issubset(evidence.required_python_packages)
        and evidence.gpu_acceleration_required
        and set(REQUIRED_HF_TOKEN_ENV_VARS).issubset(evidence.hf_token_env_var_names)
        and set(REQUIRED_HF_CACHE_ENV_VARS).issubset(evidence.hf_cache_env_var_names)
        and not evidence.environment_values_exposed
        and not evidence.private_paths_exposed
        and not evidence.raw_model_identifiers_exposed
    )


def _codec_boundary_ready(evidence: AudioTranscriptionCodecBoundaryEvidence) -> bool:
    return (
        evidence.ffmpeg_available
        and evidence.ffprobe_available
        and set(REQUIRED_COMMON_AUDIO_CODECS).issubset(evidence.supported_audio_codecs)
        and evidence.valid_audio_probe_exercised
        and evidence.bad_media_fails_closed
        and evidence.no_audio_fails_closed
        and evidence.unsupported_media_fails_closed
        and evidence.bounded_metadata_projected
    )


def _backend_dependencies_ready(
    evidence: AudioTranscriptionBackendDependencyEvidence,
) -> bool:
    return (
        evidence.faster_whisper_importable
        and evidence.pyannote_audio_importable
        and evidence.huggingface_hub_importable
        and evidence.torch_importable
        and evidence.torchaudio_importable
        and evidence.torchcodec_audio_decoder_importable
        and evidence.sidecar_runtime_isolated
        and not evidence.main_service_dependency_change_observed
    )


def _huggingface_readiness_ready(
    evidence: AudioTranscriptionHuggingFaceReadinessEvidence,
) -> bool:
    return (
        bool(evidence.token_env_var_names)
        and evidence.token_env_vars_present
        and evidence.cache_roots_ready
        and evidence.cache_status in {"scratch_backed", "ready"}
        and evidence.model_access_status in {"ready", "access_denied_probe_proven"}
        and not evidence.secret_values_exposed
        and not evidence.private_cache_paths_exposed
        and not evidence.raw_model_identifiers_exposed
    )


def _language_fixture_ready(evidence: AudioBenchmarkEvidence, language: str) -> bool:
    for fixture in evidence.language_evidence:
        if (
            fixture.language == language
            and fixture.detected_language == language
            and fixture.diarized_segment_count > 0
            and fixture.exclusive_speaker_segments
            and fixture.alignment_suitable
            and fixture.word_timestamps_available
            and not fixture.transcript_text_retained
        ):
            return True
    return False


def _gpu_required_execution_ready(evidence: AudioBenchmarkEvidence) -> bool:
    return (
        evidence.runtime.acceleration_family in {"rocm", "cuda"}
        and evidence.runtime.gpu_execution_confirmed
        and not evidence.runtime.cpu_fallback_observed
    )


def _batch_lifecycle_ready(evidence: AudioTranscriptionBatchLifecycleEvidence) -> bool:
    return (
        evidence.duration_seconds >= REQUIRED_BATCH_DURATION_SECONDS
        and evidence.chunk_count > 0
        and evidence.max_chunk_duration_seconds > 0
        and evidence.progress_updates_observed
        and evidence.checkpoints_observed
        and evidence.detached_status_capable
        and evidence.cancel_semantics_observed
        and evidence.retry_semantics_observed
    )


def _content_safety_ready(evidence: AudioTranscriptionSidecarProfileProofEvidence) -> bool:
    content_safety = evidence.benchmark_evidence.content_safety
    return (
        not content_safety.transcript_text_in_report
        and not content_safety.raw_model_ids_in_report
        and not content_safety.secret_values_in_report
        and not content_safety.private_paths_in_report
        and not content_safety.generated_artifacts_in_repo
        and not evidence.benchmark_evidence.runtime.required_secret_values_exposed
        and not evidence.huggingface_readiness.secret_values_exposed
        and not evidence.huggingface_readiness.private_cache_paths_exposed
        and not evidence.huggingface_readiness.raw_model_identifiers_exposed
        and not evidence.sidecar_launch.environment_values_exposed
        and not evidence.sidecar_launch.private_paths_exposed
        and not evidence.sidecar_launch.raw_model_identifiers_exposed
    )


def _render_profile_proof_markdown(
    report: AudioTranscriptionSidecarProfileProofReport,
) -> str:
    reasons = ", ".join(report["profile_selection"]["rejection_reasons"]) or "none"
    evidence_lines = "\n".join(
        f"- `{name}`: `{ready}`" for name, ready in sorted(report["required_evidence"].items())
    )
    return (
        "# STT Sidecar Profile Proof\n\n"
        f"- Schema: `{report['schema_version']}`\n"
        f"- Generated: `{report['generated_at_utc']}`\n"
        f"- Evidence mode: `{report['evidence_mode']}`\n"
        f"- Proof ready: `{report['proof_ready']}`\n"
        f"- Profile selected: `{report['profile_selection']['selected']}`\n"
        f"- Rejection reasons: `{reasons}`\n\n"
        "## Required Evidence\n\n"
        f"{evidence_lines}\n"
    )
