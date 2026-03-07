"""Tests for the Task 86 Hemma Chatterbox benchmark helpers.

Purpose:
    Catch local regressions in cache discovery, Docker command assembly, and
    argument parsing before the live Hemma benchmark is run.

Relationships:
    - Exercises `run_task86_hemma_chatterbox_benchmark`.
    - Mirrors the helper-coverage style used by the other TTS benchmark tasks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_task86_hemma_chatterbox_benchmark
from scripts.sir_convert_a_lot.devops.task81_openvoice_runtime import MountResolution
from scripts.sir_convert_a_lot.devops.task86_chatterbox_reporting import (
    BenchmarkReport,
    ProbeResult,
    build_report_markdown,
)
from scripts.sir_convert_a_lot.devops.task86_chatterbox_runtime import (
    BenchmarkSettings,
    discover_model_snapshot_path,
    start_sidecar,
)


def test_parse_args_prefers_canonical_hemma_cache_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH",
        "/srv/scratch/custom/cache/huggingface",
    )
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT",
        "/home/paunchygent/.data/custom/cache/huggingface",
    )

    settings = run_task86_hemma_chatterbox_benchmark._parse_args([])

    assert settings.hf_cache_dir == Path("/srv/scratch/custom/cache/huggingface")
    assert settings.hf_cache_home_mount == Path("/home/paunchygent/.data/custom/cache/huggingface")
    assert settings.cfg_weight == 0.5
    assert settings.exaggeration == 0.5
    assert settings.segment_text is False
    assert settings.segment_max_chars == 220
    assert settings.segment_cross_fade_ms == 80


def test_parse_args_accepts_probe_text_file(tmp_path: Path) -> None:
    probe_text_file = tmp_path / "probe_text.txt"
    probe_text_file.write_text("fonemiserad svensk text", encoding="utf-8")

    settings = run_task86_hemma_chatterbox_benchmark._parse_args(
        [
            "--probe-text-file",
            probe_text_file.as_posix(),
            "--segment-text",
            "--segment-max-chars",
            "180",
            "--segment-cross-fade-ms",
            "90",
        ]
    )

    assert settings.probe_text == "fonemiserad svensk text"
    assert settings.segment_text is True
    assert settings.segment_max_chars == 180
    assert settings.segment_cross_fade_ms == 90


def test_discover_model_snapshot_path_handles_hf_root_and_hub_root(tmp_path: Path) -> None:
    direct_snapshot = tmp_path / "models--ResembleAI--chatterbox" / "snapshots" / "abc"
    direct_snapshot.mkdir(parents=True)

    assert discover_model_snapshot_path(tmp_path) == direct_snapshot

    other_root = tmp_path / "alt"
    hub_snapshot = other_root / "hub" / "models--ResembleAI--chatterbox" / "snapshots" / "def"
    hub_snapshot.mkdir(parents=True)

    assert discover_model_snapshot_path(other_root) == hub_snapshot


def test_start_sidecar_uses_buildkit_ready_mounts_and_envs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_commands: list[list[str]] = []

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        assert label == "docker run task86 sidecar"
        recorded_commands.append(args)
        return "container-id"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task86_chatterbox_runtime.docker_checked",
        _fake_docker_checked,
    )
    settings = BenchmarkSettings(
        output_root=tmp_path / "output",
        dockerfile_path=tmp_path / "Dockerfile",
        image="test-image",
        network="hule-network",
        network_alias="task86-sidecar",
        container_name="task86",
        service_container="sir_convert_a_lot_prod",
        container_port=8094,
        host_port=38094,
        startup_timeout_seconds=600.0,
        hf_cache_dir=tmp_path / "hf-cache",
        hf_cache_home_mount=tmp_path / "hf-home",
        reference_audio_path=tmp_path / "voice.m4a",
        english_reference_audio_path=None,
        smoke_text="This is a smoke test.",
        probe_text="Hej världen",
        exaggeration=0.7,
        cfg_weight=0.3,
        segment_text=True,
        segment_max_chars=180,
        segment_cross_fade_ms=120,
        segment_debug_dir=tmp_path / "segment-debug",
        build_image=False,
        retain_container=False,
    )
    mount = MountResolution(
        canonical_root=tmp_path / "hf-cache",
        effective_root=tmp_path / "hf-home",
        used_home_mount=True,
    )

    start_sidecar(settings, hf_mount=mount)

    command = recorded_commands[0]
    assert "SIR_TTS_SIDECAR_CHATTERBOX_EXAGGERATION=0.7" in command
    assert "SIR_TTS_SIDECAR_CHATTERBOX_CFG_WEIGHT=0.3" in command
    assert "SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_TEXT=1" in command
    assert "SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_MAX_CHARS=180" in command
    assert "SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_CROSS_FADE_MS=120" in command
    assert "SIR_TTS_SIDECAR_CHATTERBOX_SEGMENT_DEBUG_DIR=/segment-debug" in command
    assert f"{mount.effective_root.as_posix()}:/cache/huggingface" in command
    assert settings.segment_debug_dir is not None
    assert f"{settings.segment_debug_dir.resolve().as_posix()}:/segment-debug" in command
    assert "TORCH_HOME=/cache/huggingface/torch" in command


def test_build_report_markdown_includes_restart_and_probe_sections() -> None:
    report = BenchmarkReport(
        benchmark_id="task-86",
        run_id="20260307T120000Z",
        generated_at="2026-03-07T12:00:00Z",
        repo_head="deadbeef",
        host_base_url="http://127.0.0.1:38094",
        internal_base_url="http://task86:8094",
        image="test-image",
        image_id="sha256:test",
        build_performed=True,
        package_versions_path="/tmp/package_versions.json",
        model_snapshot_path="/tmp/models--ResembleAI--chatterbox/snapshots/abc",
        model_snapshot_present_before_start=False,
        model_snapshot_downloaded_during_first_start=True,
        first_startup_seconds=12.3,
        cold_start_seconds=12.3,
        warm_restart_seconds=5.4,
        service_probe_ok=True,
        service_backend_id="chatterbox_multilingual",
        service_ready=True,
        capability_backend_id="chatterbox_multilingual",
        capability_reference_transcript_required=False,
        capability_language_support_sv="official",
        voices_count=1,
        smoke_text="This is a smoke test.",
        smoke_probe=ProbeResult(
            ok=True,
            output_path="/tmp/smoke.wav",
            sha256="abc",
            content_type="audio/wav",
            duration_seconds=1.1,
            peak_gpu_busy_percent=70,
            peak_vram_used_bytes=1024,
        ),
        probe_text="Hej världen",
        swedish_clone_probe=ProbeResult(
            ok=True,
            output_path="/tmp/clone.wav",
            sha256="def",
            content_type="audio/wav",
            duration_seconds=2.2,
            peak_gpu_busy_percent=80,
            peak_vram_used_bytes=2048,
        ),
        cross_language_probe=None,
        reference_audio_path="/tmp/ref.m4a",
        reference_audio_duration_seconds=8.0,
        reference_audio_sample_rate_hz=24000,
        english_reference_audio_path=None,
        english_reference_audio_duration_seconds=None,
        english_reference_audio_sample_rate_hz=None,
        exaggeration=0.5,
        cfg_weight=0.5,
        segment_text=True,
        segment_max_chars=220,
        segment_cross_fade_ms=80,
        segment_debug_dir="/tmp/segment-debug",
        hf_cache_host_root="/srv/cache/hf",
        gpu_product_name="AMD Radeon AI PRO R9700",
        gpu_gfx_architecture="gfx1201",
        gpu_before_path="/tmp/gpu-before.txt",
        gpu_after_path="/tmp/gpu-after.txt",
        docker_logs_path="/tmp/docker_logs.txt",
    )

    markdown = build_report_markdown(report)

    assert "warm_restart_seconds" in markdown
    assert "Smoke Probe" in markdown
    assert "Swedish Clone Probe" in markdown
    assert "segment_text" in markdown


def test_chatterbox_dockerfile_prefetches_spacy_pkuseg_model() -> None:
    dockerfile = Path("containers/tts-sidecar-chatterbox/Dockerfile").read_text(encoding="utf-8")

    assert "PKUSEG_HOME=/root/.pkuseg" in dockerfile
    assert "download_model(c.model_urls['spacy_ontonotes']" in dockerfile
