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
    extract_gpu_identity,
    python_recommendation,
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


def test_report_helpers_write_expected_json_and_markdown(tmp_path: Path) -> None:
    report = BenchmarkReport(
        benchmark_id="task-79-hemma-tts-sidecar",
        generated_at="2026-03-06T12:00:00Z",
        repo_head="abc123",
        host_base_url="http://127.0.0.1:38091",
        internal_base_url="http://sir-convert-a-lot-tts-task79:8091",
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
