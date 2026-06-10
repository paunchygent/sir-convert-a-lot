"""Audio transcription sidecar live observation mapping.

Purpose:
    Convert sanitized speech-to-text sidecar observation envelopes into typed
    profile-proof evidence.

Relationships:
    - Feeds the STT profile-proof runner with projection, blocked-live, and
      live Hemma evidence objects.
    - References only bounded benchmark contracts and avoids importing STT,
      diarization, Hugging Face, FFmpeg, or sidecar runtime libraries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_contracts import (
    AudioTranscriptionBackendDependencyEvidence,
    AudioTranscriptionBatchLifecycleEvidence,
    AudioTranscriptionCodecBoundaryEvidence,
    AudioTranscriptionHuggingFaceReadinessEvidence,
    AudioTranscriptionSidecarLaunchEvidence,
    AudioTranscriptionSidecarProfileProofEvidence,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_proof import (
    REQUIRED_COMMON_AUDIO_CODECS,
    REQUIRED_HF_CACHE_ENV_VARS,
    REQUIRED_HF_TOKEN_ENV_VARS,
    REQUIRED_PYTHON_PACKAGES,
    REQUIRED_SIDECAR_COMPOSE_SERVICE,
    REQUIRED_SIDECAR_IMAGE_NAME,
    REQUIRED_SYSTEM_TOOLS,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_benchmark_profiles import (
    AudioBenchmarkContentSafetyEvidence,
    AudioBenchmarkEvidence,
    AudioBenchmarkLanguageEvidence,
    AudioBenchmarkProfileLabels,
    AudioBenchmarkRuntimeEvidence,
    AudioBenchmarkSpeakerHintEvidence,
    AudioBenchmarkSyntheticDurationEvidence,
    BenchmarkBackendFamily,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)

LIVE_OBSERVATION_SCHEMA_VERSION = "audio_transcription_sidecar_live_observation_v1"


def read_live_observation_mapping(path: Path) -> Mapping[str, object]:
    """Read a sanitized live-observation JSON object."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "live observation must be a JSON object"
        raise ValueError(msg)
    return {str(key): value for key, value in payload.items() if isinstance(key, str)}


def build_projection_profile_proof_evidence() -> AudioTranscriptionSidecarProfileProofEvidence:
    """Build deterministic local projection evidence that never selects profiles."""

    return AudioTranscriptionSidecarProfileProofEvidence(
        evidence_mode="projection",
        sidecar_launch=_default_sidecar_launch(),
        codec_boundary=_empty_codec_boundary(),
        backend_dependencies=_empty_backend_dependencies(),
        huggingface_readiness=_empty_huggingface_readiness(),
        benchmark_evidence=_empty_benchmark_evidence(),
        batch_lifecycle=_empty_batch_lifecycle(),
        audio_transcript_route_registered=False,
    )


def build_blocked_live_profile_proof_evidence(
    reason: str,
) -> AudioTranscriptionSidecarProfileProofEvidence:
    """Build live-mode evidence that fails closed with a concrete reason."""

    return AudioTranscriptionSidecarProfileProofEvidence(
        evidence_mode="live_hemma",
        sidecar_launch=_default_sidecar_launch(),
        codec_boundary=_empty_codec_boundary(),
        backend_dependencies=_empty_backend_dependencies(),
        huggingface_readiness=_empty_huggingface_readiness(),
        benchmark_evidence=_empty_benchmark_evidence(),
        batch_lifecycle=_empty_batch_lifecycle(),
        audio_transcript_route_registered=False,
        observation_failure_reasons=(reason,),
    )


def build_live_profile_proof_evidence_from_observation(
    payload: Mapping[str, object],
) -> AudioTranscriptionSidecarProfileProofEvidence:
    """Build typed profile-proof evidence from a sanitized live observation."""

    return AudioTranscriptionSidecarProfileProofEvidence(
        evidence_mode=_string_at(payload, "evidence_mode", default="live_hemma"),
        sidecar_launch=_sidecar_launch_from_mapping(_mapping_at(payload, "sidecar_launch")),
        codec_boundary=_codec_boundary_from_mapping(_mapping_at(payload, "codec_boundary")),
        backend_dependencies=_backend_dependencies_from_mapping(
            _mapping_at(payload, "backend_dependencies"),
        ),
        huggingface_readiness=_huggingface_readiness_from_mapping(
            _mapping_at(payload, "huggingface_readiness"),
        ),
        benchmark_evidence=_benchmark_evidence_from_mapping(payload),
        batch_lifecycle=_batch_lifecycle_from_mapping(_mapping_at(payload, "batch_lifecycle")),
        audio_transcript_route_registered=False,
        observation_failure_reasons=_string_tuple_at(payload, "observation_failure_reasons"),
    )


def _sidecar_launch_from_mapping(
    payload: Mapping[str, object],
) -> AudioTranscriptionSidecarLaunchEvidence:
    return AudioTranscriptionSidecarLaunchEvidence(
        image_name=_string_at(payload, "image_name"),
        image_tag=_string_at(payload, "image_tag"),
        compose_service=_string_at(payload, "compose_service"),
        build_contract=_string_at(payload, "build_contract"),
        launch_observed=_bool_at(payload, "launch_observed"),
        isolated_runtime_marker=_bool_at(payload, "isolated_runtime_marker"),
        required_system_tools=_string_tuple_at(payload, "required_system_tools"),
        required_python_packages=_string_tuple_at(payload, "required_python_packages"),
        gpu_acceleration_required=_bool_at(payload, "gpu_acceleration_required"),
        hf_token_env_var_names=_string_tuple_at(payload, "hf_token_env_var_names"),
        hf_cache_env_var_names=_string_tuple_at(payload, "hf_cache_env_var_names"),
        environment_values_exposed=_bool_at(payload, "environment_values_exposed"),
        private_paths_exposed=_bool_at(payload, "private_paths_exposed"),
        raw_model_identifiers_exposed=_bool_at(payload, "raw_model_identifiers_exposed"),
    )


def _codec_boundary_from_mapping(
    payload: Mapping[str, object],
) -> AudioTranscriptionCodecBoundaryEvidence:
    return AudioTranscriptionCodecBoundaryEvidence(
        ffmpeg_available=_bool_at(payload, "ffmpeg_available"),
        ffprobe_available=_bool_at(payload, "ffprobe_available"),
        supported_audio_codecs=_string_tuple_at(payload, "supported_audio_codecs"),
        valid_audio_probe_exercised=_bool_at(payload, "valid_audio_probe_exercised"),
        bad_media_fails_closed=_bool_at(payload, "bad_media_fails_closed"),
        no_audio_fails_closed=_bool_at(payload, "no_audio_fails_closed"),
        unsupported_media_fails_closed=_bool_at(payload, "unsupported_media_fails_closed"),
        bounded_metadata_projected=_bool_at(payload, "bounded_metadata_projected"),
        source_media_paths=(),
    )


def _backend_dependencies_from_mapping(
    payload: Mapping[str, object],
) -> AudioTranscriptionBackendDependencyEvidence:
    return AudioTranscriptionBackendDependencyEvidence(
        faster_whisper_importable=_bool_at(payload, "faster_whisper_importable"),
        pyannote_audio_importable=_bool_at(payload, "pyannote_audio_importable"),
        huggingface_hub_importable=_bool_at(payload, "huggingface_hub_importable"),
        torch_importable=_bool_at(payload, "torch_importable"),
        torchaudio_importable=_bool_at(payload, "torchaudio_importable"),
        torchcodec_audio_decoder_importable=_bool_at(
            payload,
            "torchcodec_audio_decoder_importable",
        ),
        miopen_hiprtc_headers_available=_bool_at(
            payload,
            "miopen_hiprtc_headers_available",
        ),
        sidecar_runtime_isolated=_bool_at(payload, "sidecar_runtime_isolated"),
        main_service_dependency_change_observed=_bool_at(
            payload,
            "main_service_dependency_change_observed",
        ),
    )


def _huggingface_readiness_from_mapping(
    payload: Mapping[str, object],
) -> AudioTranscriptionHuggingFaceReadinessEvidence:
    return AudioTranscriptionHuggingFaceReadinessEvidence(
        token_env_var_names=_string_tuple_at(payload, "token_env_var_names"),
        token_env_vars_present=_bool_at(payload, "token_env_vars_present"),
        cache_roots_ready=_bool_at(payload, "cache_roots_ready"),
        cache_status=_string_at(payload, "cache_status"),
        model_access_status=_string_at(payload, "model_access_status"),
        secret_values_exposed=_bool_at(payload, "secret_values_exposed"),
        private_cache_paths_exposed=_bool_at(payload, "private_cache_paths_exposed"),
        raw_model_identifiers_exposed=_bool_at(payload, "raw_model_identifiers_exposed"),
        token_value_samples=(),
        private_cache_paths=(),
    )


def _benchmark_evidence_from_mapping(payload: Mapping[str, object]) -> AudioBenchmarkEvidence:
    return AudioBenchmarkEvidence(
        profiles=_profile_labels_from_mapping(_mapping_at(payload, "profiles")),
        runtime=_runtime_evidence_from_mapping(_mapping_at(payload, "runtime")),
        language_evidence=_language_evidence_from_mapping(payload),
        speaker_hints=_speaker_hints_from_mapping(_mapping_at(payload, "speaker_hints")),
        duration=_duration_from_mapping(_mapping_at(payload, "duration")),
        content_safety=_content_safety_from_mapping(_mapping_at(payload, "content_safety")),
    )


def _profile_labels_from_mapping(payload: Mapping[str, object]) -> AudioBenchmarkProfileLabels:
    raw_targets_recorded = _bool_at(payload, "raw_model_access_targets_recorded")
    return AudioBenchmarkProfileLabels(
        stt_profile=_string_at(payload, "stt_profile"),
        diarization_profile=_string_at(payload, "diarization_profile"),
        stt_backend_family=_backend_family(
            _string_at(payload, "stt_backend_family"),
            expected=BenchmarkBackendFamily.FASTER_WHISPER,
        ),
        diarization_backend_family=_backend_family(
            _string_at(payload, "diarization_backend_family"),
            expected=BenchmarkBackendFamily.PYANNOTE_AUDIO,
        ),
        raw_model_identifiers=("recorded",) if raw_targets_recorded else (),
    )


def _runtime_evidence_from_mapping(payload: Mapping[str, object]) -> AudioBenchmarkRuntimeEvidence:
    return AudioBenchmarkRuntimeEvidence(
        acceleration_family=_string_at(payload, "acceleration_family"),
        gpu_execution_confirmed=_bool_at(payload, "gpu_execution_confirmed"),
        cpu_fallback_observed=_bool_at(payload, "cpu_fallback_observed"),
        cache_family=_string_at(payload, "cache_family"),
        cache_reuse_observed=_bool_at(payload, "cache_reuse_observed"),
        cache_roots_ready=_bool_at(payload, "cache_roots_ready"),
        missing_model_access_failure_code=_model_access_failure_code(
            _string_at(payload, "missing_model_access_failure_code"),
        ),
        required_secret_names=_string_tuple_at(payload, "required_secret_names"),
        required_secret_values_exposed=_bool_at(payload, "required_secret_values_exposed"),
        private_cache_paths=(),
    )


def _language_evidence_from_mapping(
    payload: Mapping[str, object],
) -> tuple[AudioBenchmarkLanguageEvidence, ...]:
    value = payload.get("language_evidence")
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(_language_fixture_from_mapping(item) for item in value if isinstance(item, dict))


def _language_fixture_from_mapping(payload: Mapping[str, object]) -> AudioBenchmarkLanguageEvidence:
    return AudioBenchmarkLanguageEvidence(
        fixture_label=_string_at(payload, "fixture_label"),
        language=_string_at(payload, "language"),
        detected_language=_string_at(payload, "detected_language"),
        diarized_segment_count=_int_at(payload, "diarized_segment_count"),
        exclusive_speaker_segments=_bool_at(payload, "exclusive_speaker_segments"),
        alignment_suitable=_bool_at(payload, "alignment_suitable"),
        word_timestamps_available=_bool_at(payload, "word_timestamps_available"),
        transcript_text_retained=_bool_at(payload, "transcript_text_retained"),
        transcript_text_samples=(),
    )


def _speaker_hints_from_mapping(
    payload: Mapping[str, object],
) -> AudioBenchmarkSpeakerHintEvidence:
    return AudioBenchmarkSpeakerHintEvidence(
        exact_speaker_count_supported=_bool_at(payload, "exact_speaker_count_supported"),
        exact_speaker_count_exercised=_bool_at(payload, "exact_speaker_count_exercised"),
        min_max_speaker_range_supported=_bool_at(payload, "min_max_speaker_range_supported"),
        min_max_speaker_range_exercised=_bool_at(payload, "min_max_speaker_range_exercised"),
    )


def _duration_from_mapping(
    payload: Mapping[str, object],
) -> AudioBenchmarkSyntheticDurationEvidence:
    return AudioBenchmarkSyntheticDurationEvidence(
        proof_kind=_string_at(payload, "proof_kind"),
        duration_seconds=_float_at(payload, "duration_seconds"),
        chunk_count=_int_at(payload, "chunk_count"),
        max_chunk_duration_seconds=_float_at(payload, "max_chunk_duration_seconds"),
        lifecycle_assumptions_exercised=_bool_at(payload, "lifecycle_assumptions_exercised"),
    )


def _content_safety_from_mapping(
    payload: Mapping[str, object],
) -> AudioBenchmarkContentSafetyEvidence:
    return AudioBenchmarkContentSafetyEvidence(
        transcript_text_in_report=_bool_at(payload, "transcript_text_in_report"),
        raw_model_ids_in_report=_bool_at(payload, "raw_model_ids_in_report"),
        secret_values_in_report=_bool_at(payload, "secret_values_in_report"),
        private_paths_in_report=_bool_at(payload, "private_paths_in_report"),
        generated_artifacts_in_repo=_bool_at(payload, "generated_artifacts_in_repo"),
    )


def _batch_lifecycle_from_mapping(
    payload: Mapping[str, object],
) -> AudioTranscriptionBatchLifecycleEvidence:
    return AudioTranscriptionBatchLifecycleEvidence(
        duration_seconds=_float_at(payload, "duration_seconds"),
        chunk_count=_int_at(payload, "chunk_count"),
        max_chunk_duration_seconds=_float_at(payload, "max_chunk_duration_seconds"),
        progress_updates_observed=_bool_at(payload, "progress_updates_observed"),
        checkpoints_observed=_bool_at(payload, "checkpoints_observed"),
        detached_status_capable=_bool_at(payload, "detached_status_capable"),
        cancel_semantics_observed=_bool_at(payload, "cancel_semantics_observed"),
        retry_semantics_observed=_bool_at(payload, "retry_semantics_observed"),
    )


def _empty_benchmark_evidence() -> AudioBenchmarkEvidence:
    return AudioBenchmarkEvidence(
        profiles=AudioBenchmarkProfileLabels(
            stt_profile="",
            diarization_profile="",
            stt_backend_family=BenchmarkBackendFamily.PYANNOTE_AUDIO,
            diarization_backend_family=BenchmarkBackendFamily.FASTER_WHISPER,
            raw_model_identifiers=(),
        ),
        runtime=AudioBenchmarkRuntimeEvidence(
            acceleration_family="",
            gpu_execution_confirmed=False,
            cpu_fallback_observed=False,
            cache_family="",
            cache_reuse_observed=False,
            cache_roots_ready=False,
            missing_model_access_failure_code=None,
            required_secret_names=(),
            required_secret_values_exposed=False,
            private_cache_paths=(),
        ),
        language_evidence=(),
        speaker_hints=AudioBenchmarkSpeakerHintEvidence(
            exact_speaker_count_supported=False,
            exact_speaker_count_exercised=False,
            min_max_speaker_range_supported=False,
            min_max_speaker_range_exercised=False,
        ),
        duration=AudioBenchmarkSyntheticDurationEvidence(
            proof_kind="",
            duration_seconds=0.0,
            chunk_count=0,
            max_chunk_duration_seconds=0.0,
            lifecycle_assumptions_exercised=False,
        ),
        content_safety=AudioBenchmarkContentSafetyEvidence(
            transcript_text_in_report=False,
            raw_model_ids_in_report=False,
            secret_values_in_report=False,
            private_paths_in_report=False,
            generated_artifacts_in_repo=False,
        ),
    )


def _default_sidecar_launch() -> AudioTranscriptionSidecarLaunchEvidence:
    return AudioTranscriptionSidecarLaunchEvidence(
        image_name=REQUIRED_SIDECAR_IMAGE_NAME,
        image_tag="benchmark",
        compose_service=REQUIRED_SIDECAR_COMPOSE_SERVICE,
        build_contract="buildkit",
        launch_observed=False,
        isolated_runtime_marker=True,
        required_system_tools=REQUIRED_SYSTEM_TOOLS,
        required_python_packages=REQUIRED_PYTHON_PACKAGES,
        gpu_acceleration_required=True,
        hf_token_env_var_names=REQUIRED_HF_TOKEN_ENV_VARS,
        hf_cache_env_var_names=REQUIRED_HF_CACHE_ENV_VARS,
        environment_values_exposed=False,
        private_paths_exposed=False,
        raw_model_identifiers_exposed=False,
    )


def _empty_codec_boundary() -> AudioTranscriptionCodecBoundaryEvidence:
    return AudioTranscriptionCodecBoundaryEvidence(
        ffmpeg_available=False,
        ffprobe_available=False,
        supported_audio_codecs=REQUIRED_COMMON_AUDIO_CODECS,
        valid_audio_probe_exercised=False,
        bad_media_fails_closed=False,
        no_audio_fails_closed=False,
        unsupported_media_fails_closed=False,
        bounded_metadata_projected=False,
        source_media_paths=(),
    )


def _empty_backend_dependencies() -> AudioTranscriptionBackendDependencyEvidence:
    return AudioTranscriptionBackendDependencyEvidence(
        faster_whisper_importable=False,
        pyannote_audio_importable=False,
        huggingface_hub_importable=False,
        torch_importable=False,
        torchaudio_importable=False,
        torchcodec_audio_decoder_importable=False,
        miopen_hiprtc_headers_available=False,
        sidecar_runtime_isolated=True,
        main_service_dependency_change_observed=False,
    )


def _empty_huggingface_readiness() -> AudioTranscriptionHuggingFaceReadinessEvidence:
    return AudioTranscriptionHuggingFaceReadinessEvidence(
        token_env_var_names=REQUIRED_HF_TOKEN_ENV_VARS,
        token_env_vars_present=False,
        cache_roots_ready=False,
        cache_status="not_ready",
        model_access_status="not_checked",
        secret_values_exposed=False,
        private_cache_paths_exposed=False,
        raw_model_identifiers_exposed=False,
        token_value_samples=(),
        private_cache_paths=(),
    )


def _empty_batch_lifecycle() -> AudioTranscriptionBatchLifecycleEvidence:
    return AudioTranscriptionBatchLifecycleEvidence(
        duration_seconds=0.0,
        chunk_count=0,
        max_chunk_duration_seconds=0.0,
        progress_updates_observed=False,
        checkpoints_observed=False,
        detached_status_capable=False,
        cancel_semantics_observed=False,
        retry_semantics_observed=False,
    )


def _backend_family(
    value: str,
    *,
    expected: BenchmarkBackendFamily,
) -> BenchmarkBackendFamily:
    if value == expected.value:
        return expected
    if expected is BenchmarkBackendFamily.FASTER_WHISPER:
        return BenchmarkBackendFamily.PYANNOTE_AUDIO
    return BenchmarkBackendFamily.FASTER_WHISPER


def _model_access_failure_code(value: str) -> AudioTranscriptionErrorCode | None:
    if value == AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED.value:
        return AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED
    return None


def _mapping_at(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        return {}
    return {str(item_key): item for item_key, item in value.items() if isinstance(item_key, str)}


def _string_tuple_at(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _string_at(payload: Mapping[str, object], key: str, *, default: str = "") -> str:
    value = payload.get(key)
    if isinstance(value, str):
        return value
    return default


def _bool_at(payload: Mapping[str, object], key: str) -> bool:
    return payload.get(key) is True


def _float_at(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _int_at(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, int):
        return value
    return 0
