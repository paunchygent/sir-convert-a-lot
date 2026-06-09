"""Audio transcription sidecar benchmark preflight behavior.

Purpose:
    Guard content-safe Hemma readiness evidence for the STT sidecar benchmark
    before route registration consumes backend-profile data.

Relationships:
    - Reads the governed backlog record as the benchmark preflight
      authority.
    - Uses the public preflight report builder and CLI-safe probe helpers.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_benchmark import (
    BenchmarkPreflightSettings,
    CommandProbeResult,
    PythonModuleProbeResult,
    build_preflight_report,
    probe_python_module,
    write_preflight_report,
)
from tests.sir_convert_a_lot.backlog_document_test_support import backlog_document_path

STT_BENCHMARK_PREFLIGHT_TASK_PATH = backlog_document_path(
    category="tasks",
    title_slug="add-stt-sidecar-benchmark-runner-and-backend-profile-proof-preflight",
)


def test_preflight_report_redacts_secret_values_and_private_cache_paths(
    tmp_path: Path,
) -> None:
    settings = BenchmarkPreflightSettings(
        output_root=tmp_path,
        hf_home=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_hub_cache=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface/hub"),
        secret_env_var_names=("HF_TOKEN",),
        environment={"HF_TOKEN": "hf_secret_token_value"},
    )

    report = build_preflight_report(
        settings=settings,
        command_probe_results={
            "ffmpeg": CommandProbeResult(command_name="ffmpeg", found=False, version_line=""),
            "ffprobe": CommandProbeResult(command_name="ffprobe", found=False, version_line=""),
        },
        python_module_probe_results={
            "faster_whisper": PythonModuleProbeResult(
                module_name="faster_whisper",
                importable=False,
            ),
            "pyannote.audio": PythonModuleProbeResult(
                module_name="pyannote.audio",
                importable=False,
            ),
            "huggingface_hub": PythonModuleProbeResult(
                module_name="huggingface_hub",
                importable=True,
            ),
            "torch": PythonModuleProbeResult(module_name="torch", importable=True),
        },
    )

    assert report["preflight_ready"] is False
    assert report["profile_selection"]["selected"] is False
    assert "ffmpeg_missing" in report["blocking_reasons"]
    assert "ffprobe_missing" in report["blocking_reasons"]
    assert "faster_whisper_missing" in report["blocking_reasons"]
    assert "pyannote_audio_missing" in report["blocking_reasons"]
    assert report["secrets"]["required_env_vars"] == ("HF_TOKEN",)
    assert report["secrets"]["present_env_vars"] == ("HF_TOKEN",)
    assert report["secrets"]["secret_values_exposed"] is False

    report_json_path, report_markdown_path = write_preflight_report(report, output_root=tmp_path)
    persisted_text = report_json_path.read_text(encoding="utf-8")
    persisted_text += report_markdown_path.read_text(encoding="utf-8")

    assert "hf_secret_token_value" not in persisted_text
    assert "/srv/scratch/sir-convert-a-lot/cache/huggingface" not in persisted_text
    assert '"hf_home": "configured"' in persisted_text
    assert '"hf_hub_cache": "configured"' in persisted_text


def test_ready_preflight_still_refuses_profile_selection_before_live_fixtures(
    tmp_path: Path,
) -> None:
    settings = BenchmarkPreflightSettings(
        output_root=tmp_path,
        hf_home=tmp_path / "hf-home",
        hf_hub_cache=tmp_path / "hf-home/hub",
        secret_env_var_names=("HF_TOKEN",),
        environment={"HF_TOKEN": "hf_secret_token_value"},
    )
    settings.hf_home.mkdir()
    settings.hf_hub_cache.mkdir()

    report = build_preflight_report(
        settings=settings,
        command_probe_results={
            "ffmpeg": CommandProbeResult(
                command_name="ffmpeg",
                found=True,
                version_line="ffmpeg version 7.1",
            ),
            "ffprobe": CommandProbeResult(
                command_name="ffprobe",
                found=True,
                version_line="ffprobe version 7.1",
            ),
        },
        python_module_probe_results={
            "faster_whisper": PythonModuleProbeResult(
                module_name="faster_whisper",
                importable=True,
            ),
            "pyannote.audio": PythonModuleProbeResult(
                module_name="pyannote.audio",
                importable=True,
            ),
            "huggingface_hub": PythonModuleProbeResult(
                module_name="huggingface_hub",
                importable=True,
            ),
            "torch": PythonModuleProbeResult(module_name="torch", importable=True),
        },
    )

    assert report["preflight_ready"] is True
    assert report["profile_selection"]["selected"] is False
    assert report["profile_selection"]["rejection_reasons"] == (
        "sv_language_fixture_missing",
        "en_language_fixture_missing",
        "exact_speaker_count_not_exercised",
        "min_max_speaker_range_not_exercised",
        "duration_target_not_met",
        "duration_lifecycle_not_exercised",
    )
    assert report["next_required_evidence"] == (
        "run_swedish_fixture_with_language_detection",
        "run_english_fixture_with_language_detection",
        "exercise_exact_speaker_count_hint",
        "exercise_min_max_speaker_range_hint",
        "exercise_120_minute_batch_lifecycle",
    )


def test_nested_missing_python_module_probe_fails_closed_without_import_error() -> None:
    result = probe_python_module("missing_parent.audio")

    assert result.module_name == "missing_parent.audio"
    assert result.importable is False


def test_backlog_record_preserves_runner_scope_and_route_stop_condition() -> None:
    task_text = " ".join(STT_BENCHMARK_PREFLIGHT_TASK_PATH.read_text(encoding="utf-8").split())

    assert "STT sidecar benchmark runner" in task_text
    assert "governed production-profile rejection" in task_text
    assert "remains blocked" in task_text
    assert "faster-whisper" in task_text
    assert "pyannote.audio" in task_text
    assert "ffmpeg" in task_text
    assert "ffprobe" in task_text
    assert "Hugging Face token" in task_text
    assert "120-minute batch lifecycle" in task_text
    assert "does not register `audio -> transcript_bundle`" in task_text
