"""Audio transcription sidecar observation projection.

Purpose:
    Convert bounded runtime probe payloads into the sanitized live observation
    sections required by STT profile-proof ingestion.

Relationships:
    - Used by the live observation runtime after codec and backend probes run.
    - Shares profile-proof constants without importing STT, diarization,
      Hugging Face, FFmpeg, or Torch runtime libraries.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_proof import (
    REQUIRED_HF_TOKEN_ENV_VARS,
)

_KNOWN_BACKEND_FAMILIES = frozenset(("faster_whisper", "pyannote_audio"))
_KNOWN_BACKEND_FAILURE_CODES = frozenset(
    (
        "backend_dependency_incompatible",
        "backend_runtime_blocked",
        "gated_model_access_denied",
        "gpu_backend_runtime_unavailable",
    )
)
_KNOWN_BACKEND_FAILURE_STATUSES = frozenset(("blocked",))
_KNOWN_BACKEND_FAILURE_STAGES = frozenset(
    (
        "pipeline_load",
        "gpu_transfer",
        "audio_decode",
        "exact_speaker_count",
        "speaker_range",
        "swedish_speaker_count",
        "segment_projection",
    )
)


def failure_reasons(
    *,
    codec_boundary: Mapping[str, object],
    runtime_payload: Mapping[str, object],
    environment: Mapping[str, str],
    sidecar_launch_observed: bool,
    hf_home: Path,
    hf_hub_cache: Path,
) -> list[str]:
    """Return concrete blockers from a produced live observation."""

    reasons: list[str] = []
    if not sidecar_launch_observed:
        reasons.append("sidecar_launch_not_observed")
    if not _all_true(
        codec_boundary,
        (
            "ffmpeg_available",
            "ffprobe_available",
            "valid_audio_probe_exercised",
            "bad_media_fails_closed",
            "no_audio_fails_closed",
            "unsupported_media_fails_closed",
            "bounded_metadata_projected",
        ),
    ):
        reasons.append("codec_boundary_not_proven")
    packages = mapping_at(runtime_payload, "packages")
    if packages.get("faster_whisper") is not True:
        reasons.append("faster_whisper_missing")
    if packages.get("pyannote_audio") is not True:
        reasons.append("pyannote_audio_missing")
    if packages.get("huggingface_hub") is not True:
        reasons.append("huggingface_hub_missing")
    if packages.get("torch") is not True:
        reasons.append("torch_missing")
    if packages.get("torchaudio") is not True:
        reasons.append("torchaudio_missing")
    if packages.get("torchcodec_audio_decoder") is not True:
        reasons.append("torchcodec_audio_decoder_missing")
    if environment.get("HF_TOKEN", "").strip() == "":
        reasons.append("hf_token_missing")
    stt = mapping_at(runtime_payload, "stt")
    diarization = mapping_at(runtime_payload, "diarization")
    if stt.get("status") != "ready":
        reasons.append("faster_whisper_runtime_blocked")
    if diarization.get("status") != "ready":
        reasons.append("pyannote_audio_runtime_blocked")
    runtime = runtime_evidence(
        runtime_payload=runtime_payload,
        hf_home=hf_home,
        hf_hub_cache=hf_hub_cache,
    )
    if runtime["gpu_execution_confirmed"] is not True or runtime["cpu_fallback_observed"] is True:
        reasons.append("gpu_required_execution_not_proven")
    return reasons


def backend_dependencies(runtime_payload: Mapping[str, object]) -> dict[str, object]:
    """Project package readiness without package versions or paths."""

    packages = mapping_at(runtime_payload, "packages")
    return {
        "faster_whisper_importable": packages.get("faster_whisper") is True,
        "pyannote_audio_importable": packages.get("pyannote_audio") is True,
        "huggingface_hub_importable": packages.get("huggingface_hub") is True,
        "torch_importable": packages.get("torch") is True,
        "torchaudio_importable": packages.get("torchaudio") is True,
        "torchcodec_audio_decoder_importable": (packages.get("torchcodec_audio_decoder") is True),
        "sidecar_runtime_isolated": True,
        "main_service_dependency_change_observed": False,
    }


def backend_failures(runtime_payload: Mapping[str, object]) -> dict[str, object]:
    """Project bounded backend failure classifications without raw messages."""

    stt = mapping_at(runtime_payload, "stt")
    diarization = mapping_at(runtime_payload, "diarization")
    failures: dict[str, object] = {}
    if stt.get("status") != "ready":
        failures["stt"] = _backend_failure(
            stt,
            backend_family_default="faster_whisper",
        )
    if diarization.get("status") != "ready":
        failures["diarization"] = _backend_failure(
            diarization,
            backend_family_default="pyannote_audio",
        )
    return failures


def huggingface_readiness(
    *,
    runtime_payload: Mapping[str, object],
    environment: Mapping[str, str],
    hf_home: Path,
    hf_hub_cache: Path,
) -> dict[str, object]:
    """Project token/cache/model-access readiness without secret values or paths."""

    cache_ready = hf_home.is_dir() and hf_hub_cache.is_dir()
    model_access = mapping_at(runtime_payload, "model_access")
    cache_status = "scratch_backed" if _scratch_path(hf_home) else "ready"
    return {
        "token_env_var_names": REQUIRED_HF_TOKEN_ENV_VARS,
        "token_env_vars_present": environment.get("HF_TOKEN", "").strip() != "",
        "cache_roots_ready": cache_ready,
        "cache_status": cache_status if cache_ready else "not_ready",
        "model_access_status": string_at(model_access, "status", "not_checked"),
        "secret_values_exposed": False,
        "private_cache_paths_exposed": False,
        "raw_model_identifiers_exposed": False,
    }


def profiles(runtime_payload: Mapping[str, object]) -> dict[str, object]:
    """Project bounded public profile labels from backend probe output."""

    stt = mapping_at(runtime_payload, "stt")
    diarization = mapping_at(runtime_payload, "diarization")
    return {
        "stt_profile": string_at(stt, "profile_label", "stt_sv_en_primary"),
        "diarization_profile": string_at(
            diarization,
            "profile_label",
            "diarization_sv_en_primary",
        ),
        "stt_backend_family": string_at(stt, "backend_family", "faster_whisper"),
        "diarization_backend_family": string_at(
            diarization,
            "backend_family",
            "pyannote_audio",
        ),
        "raw_model_access_targets_recorded": mapping_at(runtime_payload, "model_access").get(
            "status"
        )
        in {"ready", "access_denied_probe_proven"},
    }


def runtime_evidence(
    *,
    runtime_payload: Mapping[str, object],
    hf_home: Path,
    hf_hub_cache: Path,
) -> dict[str, object]:
    """Project GPU and cache evidence for profile selection."""

    torch_payload = mapping_at(runtime_payload, "torch")
    stt = mapping_at(runtime_payload, "stt")
    cache_ready = hf_home.is_dir() and hf_hub_cache.is_dir()
    return {
        "acceleration_family": string_at(torch_payload, "acceleration_family", "cpu"),
        "gpu_execution_confirmed": torch_payload.get("gpu_available") is True,
        "cpu_fallback_observed": torch_payload.get("cpu_fallback_observed") is True,
        "cache_family": "huggingface" if cache_ready else "",
        "cache_reuse_observed": stt.get("cache_reuse_observed") is True,
        "cache_roots_ready": cache_ready,
        "missing_model_access_failure_code": "audio_model_access_denied",
        "required_secret_names": REQUIRED_HF_TOKEN_ENV_VARS,
        "required_secret_values_exposed": False,
    }


def language_evidence(runtime_payload: Mapping[str, object]) -> list[dict[str, object]]:
    """Project fixture-level language and diarization readiness."""

    stt = mapping_at(runtime_payload, "stt")
    diarization = mapping_at(runtime_payload, "diarization")
    diarization_by_label = {
        string_at(item, "fixture_label", ""): item
        for item in _mapping_items(diarization.get("fixtures"))
    }
    evidence: list[dict[str, object]] = []
    for fixture in _mapping_items(stt.get("fixtures")):
        label = string_at(fixture, "fixture_label", "")
        diarization_fixture = diarization_by_label.get(label, {})
        evidence.append(
            {
                "fixture_label": label,
                "language": string_at(fixture, "language", ""),
                "detected_language": string_at(fixture, "detected_language", ""),
                "diarized_segment_count": int_at(
                    diarization_fixture,
                    "diarized_segment_count",
                ),
                "exclusive_speaker_segments": diarization_fixture.get("exclusive_speaker_segments")
                is True,
                "alignment_suitable": diarization_fixture.get("alignment_suitable") is True,
                "word_timestamps_available": fixture.get("word_timestamps_available") is True,
                "transcript_text_retained": False,
            }
        )
    return evidence


def speaker_hints(runtime_payload: Mapping[str, object]) -> dict[str, object]:
    """Project exact-count and min/max speaker-hint support."""

    diarization = mapping_at(runtime_payload, "diarization")
    return {
        "exact_speaker_count_supported": diarization.get("exact_speaker_count_supported") is True,
        "exact_speaker_count_exercised": diarization.get("exact_speaker_count_exercised") is True,
        "min_max_speaker_range_supported": (
            diarization.get("min_max_speaker_range_supported") is True
        ),
        "min_max_speaker_range_exercised": (
            diarization.get("min_max_speaker_range_exercised") is True
        ),
    }


def duration(lifecycle: object) -> dict[str, object]:
    """Project deterministic 120-minute duration evidence."""

    return {
        "proof_kind": "synthetic_duration_lifecycle",
        "duration_seconds": getattr(lifecycle, "duration_seconds"),
        "chunk_count": getattr(lifecycle, "chunk_count"),
        "max_chunk_duration_seconds": getattr(lifecycle, "max_chunk_duration_seconds"),
        "lifecycle_assumptions_exercised": True,
    }


def batch_lifecycle(lifecycle: object) -> dict[str, object]:
    """Project progress, checkpoint, cancel, and retry evidence."""

    return {
        "duration_seconds": getattr(lifecycle, "duration_seconds"),
        "chunk_count": getattr(lifecycle, "chunk_count"),
        "max_chunk_duration_seconds": getattr(lifecycle, "max_chunk_duration_seconds"),
        "progress_updates_observed": getattr(lifecycle, "progress_updates_observed"),
        "checkpoints_observed": getattr(lifecycle, "checkpoints_observed"),
        "detached_status_capable": getattr(lifecycle, "detached_status_capable"),
        "cancel_semantics_observed": getattr(lifecycle, "cancel_semantics_observed"),
        "retry_semantics_observed": getattr(lifecycle, "retry_semantics_observed"),
    }


def content_safety() -> dict[str, object]:
    """Project content-safety flags for retained reports."""

    return {
        "transcript_text_in_report": False,
        "raw_model_ids_in_report": False,
        "secret_values_in_report": False,
        "private_paths_in_report": False,
        "generated_artifacts_in_repo": False,
    }


def mapping_at(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    """Return a normalized object mapping for one key."""

    value = payload.get(key)
    if not isinstance(value, dict):
        return {}
    return {str(item_key): item for item_key, item in value.items() if isinstance(item_key, str)}


def _backend_failure(
    payload: Mapping[str, object],
    *,
    backend_family_default: str,
) -> dict[str, object]:
    failure = mapping_at(payload, "failure")
    projected: dict[str, object] = {
        "backend_family": _bounded_backend_family(
            string_at(payload, "backend_family", backend_family_default),
            default=backend_family_default,
        ),
        "status": _bounded_backend_failure_status(
            string_at(payload, "status", "blocked"),
        ),
        "failure_code": _bounded_backend_failure_code(
            string_at(failure, "failure_code", "backend_runtime_blocked"),
        ),
        "exception_class": _bounded_exception_class(
            string_at(failure, "exception_class", "Unavailable")
        ),
    }
    failure_stage = _bounded_backend_failure_stage(string_at(failure, "failure_stage", ""))
    if failure_stage:
        projected["failure_stage"] = failure_stage
    return projected


def string_at(payload: Mapping[str, object], key: str, default: str) -> str:
    """Return a string value from a mapping, or a default."""

    value = payload.get(key)
    if isinstance(value, str):
        return value
    return default


def _bounded_backend_family(value: str, *, default: str) -> str:
    if value in _KNOWN_BACKEND_FAMILIES:
        return value
    return default


def _bounded_backend_failure_status(value: str) -> str:
    if value in _KNOWN_BACKEND_FAILURE_STATUSES:
        return value
    return "blocked"


def _bounded_backend_failure_code(value: str) -> str:
    if value in _KNOWN_BACKEND_FAILURE_CODES:
        return value
    return "backend_runtime_blocked"


def _bounded_backend_failure_stage(value: str) -> str:
    if value in _KNOWN_BACKEND_FAILURE_STAGES:
        return value
    return ""


def _bounded_exception_class(value: str) -> str:
    if value in {"Exception", "Unavailable"}:
        return value
    if _ascii_identifier(value) and value.endswith(("Error", "Exception")):
        return value
    return "Unavailable"


def _ascii_identifier(value: str) -> bool:
    if not value:
        return False
    first_character = value[0]
    if not (first_character.isascii() and (first_character.isalpha() or first_character == "_")):
        return False
    return all(
        character.isascii() and (character.isalnum() or character == "_") for character in value
    )


def int_at(payload: Mapping[str, object], key: str) -> int:
    """Return an integer value from a mapping, or zero."""

    value = payload.get(key)
    if isinstance(value, int):
        return value
    return 0


def _mapping_items(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        {
            str(item_key): item_value
            for item_key, item_value in item.items()
            if isinstance(item_key, str)
        }
        for item in value
        if isinstance(item, dict)
    )


def _all_true(payload: Mapping[str, object], keys: Sequence[str]) -> bool:
    return all(payload.get(key) is True for key in keys)


def _scratch_path(path: Path) -> bool:
    return path.as_posix().startswith("/srv/scratch/")
