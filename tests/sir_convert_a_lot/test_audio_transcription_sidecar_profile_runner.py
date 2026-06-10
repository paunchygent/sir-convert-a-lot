"""Audio transcription sidecar profile-proof runner behavior.

Purpose:
    Prove the operator command surface writes content-safe profile-proof
    evidence in projection and live Hemma modes without exposing the audio
    transcript route.

Relationships:
    - Exercises the STT benchmark profile-proof CLI boundary.
    - Reads the PDM command table as the operator-facing command contract.
"""

from __future__ import annotations

import importlib
import json
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType


def test_profile_proof_pdm_command_targets_purpose_named_runner() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    scripts = payload["tool"]["pdm"]["scripts"]

    assert scripts["benchmark:stt-sidecar-profile-proof"] == (
        "python -m scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_profile_proof"
    )


def test_projection_mode_writes_rejected_content_safe_report(tmp_path: Path) -> None:
    runner = _runner_module()

    exit_code = runner.main(["--mode", "projection", "--output-root", tmp_path.as_posix()])

    report = _read_report(tmp_path)
    persisted_text = _persisted_report_text(tmp_path)
    assert exit_code == 0
    assert report["evidence_mode"] == "projection"
    assert report["proof_ready"] is False
    profile_selection = _mapping_at(report, "profile_selection")
    assert profile_selection["selected"] is False
    assert "live_hemma_evidence_missing" in _sequence_at(
        profile_selection,
        "rejection_reasons",
    )
    assert report["sidecar_launch"] == {
        "image_name": "sir-convert-a-lot-stt-sidecar",
        "image_tag": "benchmark",
        "compose_service": "stt-sidecar-benchmark",
        "build_contract": "buildkit",
        "launch_observed": False,
        "isolated_runtime_marker": True,
        "required_system_tools": ["ffmpeg", "ffprobe"],
        "required_python_packages": [
            "faster-whisper",
            "huggingface_hub",
            "pyannote.audio",
            "torch",
            "torchaudio",
            "torchcodec",
        ],
        "gpu_acceleration_required": True,
        "hf_token_env_var_names": ["HF_TOKEN"],
        "hf_cache_env_var_names": ["HF_HOME", "HF_HUB_CACHE"],
    }
    route_registration = _mapping_at(report, "route_registration")
    assert route_registration["audio_transcript_bundle_registered"] is False
    assert "hf_private_token_value" not in persisted_text
    assert "provider/private-stt-model" not in persisted_text
    assert "/srv/scratch" not in persisted_text
    assert "hello this must not render" not in persisted_text


def test_live_mode_without_observation_fails_closed(tmp_path: Path) -> None:
    runner = _runner_module()

    exit_code = runner.main(["--mode", "live", "--output-root", tmp_path.as_posix()])

    report = _read_report(tmp_path)
    assert exit_code == 2
    assert report["evidence_mode"] == "live_hemma"
    assert report["proof_ready"] is False
    profile_selection = _mapping_at(report, "profile_selection")
    assert profile_selection["selected"] is False
    assert "live_observation_missing" in _sequence_at(
        profile_selection,
        "rejection_reasons",
    )


def test_live_mode_accepts_complete_sanitized_observation(tmp_path: Path) -> None:
    runner = _runner_module()
    observation_path = tmp_path / "live-observation.json"
    observation_path.write_text(
        json.dumps(_complete_live_observation()),
        encoding="utf-8",
    )

    exit_code = runner.main(
        [
            "--mode",
            "live",
            "--live-observation-json",
            observation_path.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
        ],
    )

    report = _read_report(tmp_path)
    persisted_text = _persisted_report_text(tmp_path)
    assert exit_code == 0
    assert report["proof_ready"] is True
    assert _mapping_at(report, "profile_selection") == {
        "selected": True,
        "stt_profile": "stt_sv_en_primary",
        "diarization_profile": "diarization_sv_en_primary",
        "rejection_reasons": [],
    }
    required_evidence = _mapping_at(report, "required_evidence")
    assert required_evidence["sidecar_launch"] is True
    assert required_evidence["gpu_required_execution"] is True
    assert required_evidence["batch_lifecycle"] is True
    assert "hf_private_token_value" not in persisted_text
    assert "provider/private-stt-model" not in persisted_text
    assert "/srv/scratch" not in persisted_text
    assert "hej detta ska inte synas" not in persisted_text


def test_live_mode_rejects_cpu_execution_from_observation(tmp_path: Path) -> None:
    runner = _runner_module()
    observation = _complete_live_observation()
    runtime = _mapping_at(observation, "runtime")
    runtime["gpu_execution_confirmed"] = False
    runtime["cpu_fallback_observed"] = True
    observation["runtime"] = runtime
    observation_path = tmp_path / "live-observation.json"
    observation_path.write_text(json.dumps(observation), encoding="utf-8")

    exit_code = runner.main(
        [
            "--mode",
            "live",
            "--live-observation-json",
            observation_path.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
        ],
    )

    report = _read_report(tmp_path)
    assert exit_code == 2
    assert report["proof_ready"] is False
    rejection_reasons = _sequence_at(_mapping_at(report, "profile_selection"), "rejection_reasons")
    assert "gpu_required_execution_not_proven" in rejection_reasons
    assert "cpu_fallback_observed" in rejection_reasons


def test_live_mode_rejects_missing_sidecar_launch_metadata(tmp_path: Path) -> None:
    runner = _runner_module()
    observation = _complete_live_observation()
    del observation["sidecar_launch"]
    observation_path = tmp_path / "live-observation.json"
    observation_path.write_text(json.dumps(observation), encoding="utf-8")

    exit_code = runner.main(
        [
            "--mode",
            "live",
            "--live-observation-json",
            observation_path.as_posix(),
            "--output-root",
            tmp_path.as_posix(),
        ],
    )

    report = _read_report(tmp_path)
    assert exit_code == 2
    assert report["proof_ready"] is False
    assert _mapping_at(report, "required_evidence")["sidecar_launch"] is False
    assert "sidecar_launch_not_ready" in _sequence_at(
        _mapping_at(report, "profile_selection"),
        "rejection_reasons",
    )


def _runner_module() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_profile_proof"
    )


def _read_report(output_root: Path) -> dict[str, object]:
    payload = json.loads((output_root / "profile-proof.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("profile proof report must be a JSON object")
    return {str(key): value for key, value in payload.items() if isinstance(key, str)}


def _persisted_report_text(output_root: Path) -> str:
    return (output_root / "profile-proof.json").read_text(encoding="utf-8") + (
        output_root / "profile-proof.md"
    ).read_text(encoding="utf-8")


def _mapping_at(payload: Mapping[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"{key} must be a JSON object")
    return {str(item_key): item for item_key, item in value.items() if isinstance(item_key, str)}


def _sequence_at(payload: Mapping[str, object], key: str) -> Sequence[object]:
    value = payload[key]
    if not isinstance(value, list):
        raise AssertionError(f"{key} must be a JSON array")
    return value


def _complete_live_observation() -> dict[str, object]:
    return {
        "schema_version": "audio_transcription_sidecar_live_observation_v1",
        "evidence_mode": "live_hemma",
        "sidecar_launch": {
            "image_name": "sir-convert-a-lot-stt-sidecar",
            "image_tag": "benchmark",
            "compose_service": "stt-sidecar-benchmark",
            "build_contract": "buildkit",
            "launch_observed": True,
            "isolated_runtime_marker": True,
            "required_system_tools": ("ffmpeg", "ffprobe"),
            "required_python_packages": (
                "faster-whisper",
                "huggingface_hub",
                "pyannote.audio",
                "torch",
                "torchaudio",
                "torchcodec",
            ),
            "gpu_acceleration_required": True,
            "hf_token_env_var_names": ("HF_TOKEN",),
            "hf_cache_env_var_names": ("HF_HOME", "HF_HUB_CACHE"),
            "environment_values_exposed": False,
            "private_paths_exposed": False,
            "raw_model_identifiers_exposed": False,
        },
        "codec_boundary": {
            "ffmpeg_available": True,
            "ffprobe_available": True,
            "supported_audio_codecs": ("aac", "flac", "m4a", "mp3", "ogg", "opus", "wav"),
            "valid_audio_probe_exercised": True,
            "bad_media_fails_closed": True,
            "no_audio_fails_closed": True,
            "unsupported_media_fails_closed": True,
            "bounded_metadata_projected": True,
        },
        "backend_dependencies": {
            "faster_whisper_importable": True,
            "pyannote_audio_importable": True,
            "huggingface_hub_importable": True,
            "torch_importable": True,
            "torchaudio_importable": True,
            "torchcodec_audio_decoder_importable": True,
            "sidecar_runtime_isolated": True,
            "main_service_dependency_change_observed": False,
        },
        "huggingface_readiness": {
            "token_env_var_names": ("HF_TOKEN",),
            "token_env_vars_present": True,
            "cache_roots_ready": True,
            "cache_status": "scratch_backed",
            "model_access_status": "ready",
            "secret_values_exposed": False,
            "private_cache_paths_exposed": False,
            "raw_model_identifiers_exposed": False,
        },
        "profiles": {
            "stt_profile": "stt_sv_en_primary",
            "diarization_profile": "diarization_sv_en_primary",
            "stt_backend_family": "faster_whisper",
            "diarization_backend_family": "pyannote_audio",
            "raw_model_access_targets_recorded": True,
        },
        "runtime": {
            "acceleration_family": "rocm",
            "gpu_execution_confirmed": True,
            "cpu_fallback_observed": False,
            "cache_family": "huggingface",
            "cache_reuse_observed": True,
            "cache_roots_ready": True,
            "missing_model_access_failure_code": "audio_model_access_denied",
            "required_secret_names": ("HF_TOKEN",),
            "required_secret_values_exposed": False,
        },
        "language_evidence": (
            {
                "fixture_label": "operator_sv_fixture",
                "language": "sv",
                "detected_language": "sv",
                "diarized_segment_count": 18,
                "exclusive_speaker_segments": True,
                "alignment_suitable": True,
                "word_timestamps_available": True,
                "transcript_text_retained": False,
            },
            {
                "fixture_label": "operator_en_fixture",
                "language": "en",
                "detected_language": "en",
                "diarized_segment_count": 21,
                "exclusive_speaker_segments": True,
                "alignment_suitable": True,
                "word_timestamps_available": True,
                "transcript_text_retained": False,
            },
        ),
        "speaker_hints": {
            "exact_speaker_count_supported": True,
            "exact_speaker_count_exercised": True,
            "min_max_speaker_range_supported": True,
            "min_max_speaker_range_exercised": True,
        },
        "duration": {
            "proof_kind": "detached_live_status",
            "duration_seconds": 7_200.0,
            "chunk_count": 12,
            "max_chunk_duration_seconds": 600.0,
            "lifecycle_assumptions_exercised": True,
        },
        "batch_lifecycle": {
            "duration_seconds": 7_200.0,
            "chunk_count": 12,
            "max_chunk_duration_seconds": 600.0,
            "progress_updates_observed": True,
            "checkpoints_observed": True,
            "detached_status_capable": True,
            "cancel_semantics_observed": True,
            "retry_semantics_observed": True,
        },
        "content_safety": {
            "transcript_text_in_report": False,
            "raw_model_ids_in_report": False,
            "secret_values_in_report": False,
            "private_paths_in_report": False,
            "generated_artifacts_in_repo": False,
        },
    }
