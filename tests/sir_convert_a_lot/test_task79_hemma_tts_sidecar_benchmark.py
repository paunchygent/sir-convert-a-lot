"""Tests for the Task 79 Hemma TTS sidecar benchmark helpers.

Purpose:
    Protect the typed parsing and reporting helpers behind the live Hemma
    sidecar benchmark so local regressions are caught before remote runs.

Relationships:
    - Exercises `task79_hemma_tts_sidecar_runtime`.
    - Exercises `task79_hemma_tts_sidecar_reporting`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_task79_hemma_tts_sidecar_benchmark
from scripts.sir_convert_a_lot.devops.task79_hemma_tts_sidecar_reporting import (
    AudioProbeResult,
    BenchmarkReport,
    GpuIdentity,
    PythonRecommendation,
    SidecarRuntime,
    VoicesEvidence,
    build_report_markdown,
    write_json,
)
from scripts.sir_convert_a_lot.devops.task79_hemma_tts_sidecar_runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    BenchmarkSettings,
    extract_gpu_identity,
    python_recommendation,
    start_sidecar,
    voice_names_from_payload,
)


def test_extract_gpu_identity_parses_r9700_and_gfx1201() -> None:
    smi_output = (
        "GPU[0]\t\t: Card series: AMD Radeon AI PRO R9700\n"
        "GPU[0]\t\t: VRAM Total Memory (B): 32061259776\n"
        "GPU[0]\t\t: VRAM Total Used Memory (B): 2147483648\n"
        "GPU[0]\t\t: GPU use (%): 37\n"
    )
    rocminfo_output = "Name: gfx1201\nMarketing Name: AMD Radeon AI PRO R9700\n"

    identity = extract_gpu_identity(smi_output, rocminfo_output)

    assert identity.product_name == "AMD Radeon AI PRO R9700"
    assert identity.gfx_architecture == "gfx1201"
    assert identity.vram_total_bytes == 32061259776
    assert identity.peak_gpu_busy_percent == 37
    assert identity.peak_vram_used_bytes == 2147483648


def test_voice_names_from_payload_handles_dict_entries() -> None:
    payload = {"voices": [{"name": "Chelsie"}, {"voice": "Ryan"}, {"name": "Chelsie"}]}

    assert voice_names_from_payload(payload) == ["Chelsie", "Ryan"]


def test_python_recommendation_marks_312_as_not_yet_314() -> None:
    recommendation = python_recommendation("3.12.11")

    assert recommendation.highest_proven_version == "3.12.11"
    assert recommendation.recommended_minor == "3.12"
    assert recommendation.python_3_14_supported is False


def test_parse_args_prefers_canonical_hemma_cache_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH",
        "/srv/scratch/custom/cache/huggingface",
    )

    settings = run_task79_hemma_tts_sidecar_benchmark._parse_args([])

    assert settings.hf_cache_dir == Path("/srv/scratch/custom/cache/huggingface")


def test_start_sidecar_uses_persistent_hf_cache_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage_config_path = tmp_path / "task79_stage_config.yaml"
    stage_config_path.write_text("model: test\n", encoding="utf-8")
    hf_cache_dir = tmp_path / "hf-cache"
    recorded_commands: list[list[str]] = []

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        assert label == "docker run task79 sidecar"
        recorded_commands.append(args)
        return "container-id"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task79_hemma_tts_sidecar_runtime.docker_checked",
        _fake_docker_checked,
    )
    settings = BenchmarkSettings(
        output_root=tmp_path / "output",
        image="vllm/vllm-omni-rocm:v0.16.0",
        model="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        network="hule-network",
        network_alias="sir-convert-a-lot-tts-task79",
        container_name="sir_convert_a_lot_tts_task79",
        service_container="sir_convert_a_lot_prod",
        container_port=8091,
        host_port=38091,
        voice="Chelsie",
        response_formats=("wav",),
        startup_timeout_seconds=600.0,
        hf_cache_dir=hf_cache_dir,
        probe_text="hello",
        hf_token=None,
        pull_image=False,
        retain_container=False,
        stage_config_path=stage_config_path,
    )

    start_sidecar(settings)

    assert len(recorded_commands) == 1
    command = recorded_commands[0]
    assert f"{hf_cache_dir.as_posix()}:{CONTAINER_HF_HOME}" in command
    assert f"HF_HOME={CONTAINER_HF_HOME}" in command
    assert f"HF_HUB_CACHE={CONTAINER_HF_HUB_CACHE}" in command
    assert f"TRANSFORMERS_CACHE={CONTAINER_HF_HOME}" in command


def test_report_helpers_write_expected_json_and_markdown(tmp_path: Path) -> None:
    report = BenchmarkReport(
        benchmark_id="task-79-hemma-tts-sidecar",
        generated_at="2026-03-06T12:00:00Z",
        repo_head="abc123",
        host_base_url="http://127.0.0.1:38091",
        internal_base_url="http://sir-convert-a-lot-tts-task79:8091",
        host_hf_cache_dir="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        gpu_identity=GpuIdentity(
            product_name="AMD Radeon AI PRO R9700",
            gfx_architecture="gfx1201",
            vram_total_bytes=32061259776,
            peak_gpu_busy_percent=41,
            peak_vram_used_bytes=3145728000,
        ),
        sidecar_runtime=SidecarRuntime(
            image="vllm/vllm-omni-rocm:v0.16.0",
            image_id="sha256:test",
            container_name="sir_convert_a_lot_tts_task79",
            python_version="3.12.11",
            package_versions={"vllm": "0.16.0", "vllm-omni": None, "vllm_omni": None},
            stage_config_path="/workspace/task79_stage_config.yaml",
            hf_home="/cache/huggingface",
            hf_hub_cache="/cache/huggingface/hub",
            transformers_cache="/cache/huggingface",
        ),
        voices_evidence=VoicesEvidence(
            host_probe_ok=True,
            service_probe_ok=True,
            host_voice_count=2,
            service_voice_count=2,
            voice_names=["Chelsie", "Ryan"],
        ),
        audio_results=[
            AudioProbeResult(
                response_format="wav",
                ok=True,
                status_code=200,
                content_type="audio/wav",
                byte_count=4096,
                sha256="deadbeef",
                output_path="build/verification/task-79-hemma-tts-sidecar/artifacts/sample.wav",
                elapsed_seconds=2.5,
                sample_rate_hz=24000,
                duration_seconds=1.75,
                error_message=None,
            )
        ],
        python_recommendation=PythonRecommendation(
            highest_proven_version="3.12.11",
            recommended_minor="3.12",
            python_3_14_supported=False,
            rationale="3.12 is the highest live-proven version so far.",
        ),
        pull_performed=True,
        readiness_seconds=42.0,
        cleanup_performed=True,
        docker_logs_path="build/verification/task-79-hemma-tts-sidecar/docker_logs.txt",
    )

    json_path = tmp_path / "report.json"
    write_json(json_path, report)
    markdown = build_report_markdown(report)

    assert '"benchmark_id": "task-79-hemma-tts-sidecar"' in json_path.read_text(encoding="utf-8")
    assert "## Sidecar Runtime" in markdown
    assert "`3.12.11`" in markdown
    assert "/srv/scratch/sir-convert-a-lot/cache/huggingface" in markdown
