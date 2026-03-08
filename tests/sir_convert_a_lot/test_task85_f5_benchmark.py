"""Tests for the Task 85 Hemma F5 benchmark runner.

Purpose:
    Lock the Task 85 CLI parsing defaults and report formatting around the
    current Swedish F5-TTS benchmark surface without requiring Hemma or model
    downloads during local test runs.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.run_task85_hemma_f5_smoke`.
    - Complements adapter-only coverage in `test_tts_sidecar_f5_adapter.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch

from scripts.sir_convert_a_lot.devops.run_task85_hemma_f5_smoke import (
    BenchmarkReport,
    _build_report_markdown,
    _parse_args,
    _run_synthesis,
)
from scripts.sir_convert_a_lot.tts_sidecar.chatterbox_segmented_generation import (
    wave_bytes_from_waveform,
)


def test_parse_args_uses_quality_first_defaults() -> None:
    settings = _parse_args([])

    assert settings.remove_silence is True
    assert settings.nfe_step == 64
    assert settings.cfg_strength == 2.0
    assert settings.sway_sampling_coef == -1.0
    assert settings.speed == 1.0
    assert settings.fix_duration is None
    assert settings.cross_fade_duration == 0.15
    assert settings.target_rms == 0.1
    assert settings.load_vocoder_from_local is False
    assert settings.reference_max_seconds == 12.0
    assert settings.segment_text is False
    assert settings.segment_max_chars == 160
    assert settings.segment_cross_fade_ms == 80
    assert settings.segment_stitch_mode == "simple"
    assert settings.probe_text_path is None


def test_parse_args_reads_probe_text_from_file(tmp_path: Path) -> None:
    probe_text_file = tmp_path / "probe_text.txt"
    probe_text_file.write_text("[main] Hej. Paus, tack.\n", encoding="utf-8")

    settings = _parse_args(["--probe-text-file", probe_text_file.as_posix()])

    assert settings.probe_text == "[main] Hej. Paus, tack."
    assert settings.probe_text_path == probe_text_file


def test_parse_args_accepts_segment_controls() -> None:
    settings = _parse_args(
        [
            "--segment-text",
            "--segment-max-chars",
            "140",
            "--segment-cross-fade-ms",
            "60",
            "--segment-stitch-mode",
            "speech_aware",
            "--reference-max-seconds",
            "12.0",
        ]
    )

    assert settings.segment_text is True
    assert settings.segment_max_chars == 140
    assert settings.segment_cross_fade_ms == 60
    assert settings.segment_stitch_mode == "speech_aware"
    assert settings.reference_max_seconds == 12.0


def test_build_report_markdown_lists_new_f5_controls() -> None:
    report = BenchmarkReport(
        benchmark_id="task-85-f5-tts-hemma",
        run_id="20260308T010000Z",
        generated_at="2026-03-08T01:00:00Z",
        repo_head="abc123",
        host_base_url="http://127.0.0.1:38093",
        internal_base_url="http://sir-convert-a-lot-f5-task85:8093",
        image="sir-convert-a-lot/f5-sidecar-task85:local",
        image_id="sha256:test",
        build_performed=False,
        readiness_seconds=6.1,
        help_command_ok=True,
        help_output_path="help.txt",
        synthesized_ok=True,
        synthesized_output_path="artifacts/sample.wav",
        synthesized_sha256="deadbeef",
        synthesized_content_type="audio/wav",
        service_probe_ok=True,
        service_backend_id="f5_tts_swedish",
        service_ready=True,
        capability_backend_id="f5_tts_swedish",
        capability_language_support="experimental",
        capability_reference_transcript_required=True,
        reference_audio_path="reference.wav",
        reference_audio_duration_seconds=10.0,
        reference_audio_sample_rate_hz=24000,
        reference_transcript="Hej hej.",
        reference_transcript_path="reference.txt",
        probe_text="[main] Hej. Paus, tack.",
        probe_text_path="probe.txt",
        remove_silence=True,
        nfe_step=64,
        cfg_strength=2.0,
        sway_sampling_coef=-1.0,
        speed=1.0,
        fix_duration=None,
        cross_fade_duration=0.15,
        target_rms=0.1,
        vocoder_name="vocos",
        load_vocoder_from_local=False,
        reference_max_seconds=12.0,
        segment_text=True,
        segment_count=3,
        segment_max_chars=160,
        segment_cross_fade_ms=80,
        segment_stitch_mode="simple",
        segment_debug_dir="/tmp/segment-debug",
        hf_cache_host_root="/cache/hf",
        model_cache_host_root="/cache/model",
        model_files=["model_last.pt", "vocab.txt"],
        gpu_product_name="AMD Radeon AI PRO R9700",
        gpu_gfx_architecture="gfx1201",
        docker_logs_path="docker_logs.txt",
    )

    markdown = _build_report_markdown(report)

    assert "- speed: `1.0`" in markdown
    assert "- fix_duration: `None`" in markdown
    assert "- cross_fade_duration: `0.15`" in markdown
    assert "- target_rms: `0.1`" in markdown
    assert "- load_vocoder_from_local: `False`" in markdown
    assert "- reference_max_seconds: `12.0`" in markdown
    assert "- segment_text: `True`" in markdown
    assert "- segment_count: `3`" in markdown


def test_run_synthesis_segments_and_stitches(monkeypatch, tmp_path: Path) -> None:
    settings = _parse_args(
        [
            "--output-root",
            tmp_path.as_posix(),
            "--segment-text",
            "--segment-max-chars",
            "40",
        ]
    )
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    segment_bytes = wave_bytes_from_waveform(
        torch.tensor([[0.0, 0.1, 0.2, 0.1, 0.0]], dtype=torch.float32),
        sample_rate_hz=24000,
    )
    calls: list[str] = []

    def _fake_synthesize_probe(**kwargs: object) -> tuple[bytes, str | None]:
        text = str(kwargs["text"])
        output_path = Path(str(kwargs["output_path"]))
        calls.append(text)
        output_path.write_bytes(segment_bytes)
        return segment_bytes, "audio/wav"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task85_hemma_f5_smoke._synthesize_probe",
        _fake_synthesize_probe,
    )

    (
        synthesized_ok,
        output_path,
        synthesized_sha256,
        content_type,
        segment_count,
        segment_debug_dir,
    ) = _run_synthesis(
        settings=settings,
        base_url="http://127.0.0.1:38093",
        artifacts_dir=artifacts_dir,
        reference_transcript="Hej hej.",
        sample_rate_hz=24000,
    )

    assert synthesized_ok is True
    assert output_path == (artifacts_dir / "sample_sv.wav").as_posix()
    assert synthesized_sha256 is not None
    assert content_type == "audio/wav"
    assert segment_count is not None and segment_count >= 2
    assert segment_debug_dir == (tmp_path / "segment-debug").as_posix()
    assert len(calls) == segment_count
    assert (tmp_path / "segment-debug" / "segment_plan.json").exists()
    assert (tmp_path / "segment-debug" / "stitched.wav").exists()
    plan_payload = json.loads((tmp_path / "segment-debug" / "segment_plan.json").read_text())
    assert plan_payload["segment_count"] == segment_count
