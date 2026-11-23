"""Tests for the Hemma TTS sidecar benchmark cache, measurement, and report probes.

Purpose:
    Protect the host-cache resolution, GPU measurement, audio-probe, and
    reporting helpers behind the live Hemma sidecar benchmark so local
    regressions are caught before remote runs.

Relationships:
    - Exercises `tts_sidecar_benchmark_probes`.
    - Exercises `tts_sidecar_benchmark_reporting`.
    - Docker launch/readiness cases live in `test_tts_sidecar_hemma_benchmark`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes import (
    audio_probe,
    extract_gpu_identity,
    python_recommendation,
    resolve_effective_hf_cache_dir,
    voice_names_from_payload,
)
from scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_reporting import (
    AudioProbeResult,
    BenchmarkReport,
    GpuIdentity,
    PythonRecommendation,
    SidecarRuntime,
    SpeechRequestEvidence,
    VoicesEvidence,
    build_report_markdown,
    write_json,
)
from tests.sir_convert_a_lot.speech.tts_sidecar_benchmark_test_support import (
    build_settings,
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


def test_voice_names_from_payload_allows_empty_voice_lists() -> None:
    assert voice_names_from_payload({"voices": []}) == []


def test_python_recommendation_marks_312_as_not_yet_314() -> None:
    recommendation = python_recommendation("3.12.11")

    assert recommendation.highest_proven_version == "3.12.11"
    assert recommendation.recommended_minor == "3.12"
    assert recommendation.python_3_14_supported is False


def test_resolve_effective_hf_cache_dir_uses_home_bind_mount_when_srv_probe_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hf_cache_dir = tmp_path / "hf-cache-data-disk"
    hf_cache_home_mount = tmp_path / "hf-cache-home"
    probe_calls: list[Path] = []
    bind_calls: list[tuple[Path, Path]] = []

    def _fake_probe(cache_dir: Path, *, image: str) -> bool:
        assert image == "vllm/vllm-omni-rocm:v0.16.0"
        probe_calls.append(cache_dir)
        return cache_dir == hf_cache_home_mount

    def _fake_bind_mount(canonical_dir: Path, home_mount: Path) -> None:
        bind_calls.append((canonical_dir, home_mount))

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes._probe_docker_bind_mount",
        _fake_probe,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes._ensure_home_bind_mount",
        _fake_bind_mount,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes._is_srv_cache_path",
        lambda cache_dir: cache_dir == hf_cache_dir,
    )
    settings = build_settings(
        tmp_path,
        hf_cache_dir=hf_cache_dir,
        hf_cache_home_mount=hf_cache_home_mount,
        voice="Chelsie",
    )

    effective_cache_dir = resolve_effective_hf_cache_dir(settings)

    assert effective_cache_dir == hf_cache_home_mount
    assert probe_calls == [hf_cache_dir, hf_cache_home_mount]
    assert bind_calls == [(hf_cache_dir, hf_cache_home_mount)]


def test_audio_probe_treats_json_success_payload_as_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakeSampler:
        def start(self) -> None:
            return None

        def stop(self) -> tuple[int, int]:
            return (0, 0)

    class _FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}
        content = b'{"error":{"message":"Invalid speaker"}}'
        text = '{"error":{"message":"Invalid speaker"}}'
        is_success = True

    class _FakeClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 600.0

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
            return False

        def post(self, url: str, json: dict[str, str]) -> _FakeResponse:
            assert url == "http://127.0.0.1:38091/v1/audio/speech"
            assert json["voice"] == "ryan"
            return _FakeResponse()

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes._GpuSampler",
        _FakeSampler,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes.httpx.Client",
        _FakeClient,
    )
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    stale_output_path = artifacts_dir / "sample.wav"
    stale_output_path.write_bytes(b"stale-audio")
    settings = build_settings(tmp_path)

    result, peak_busy, peak_vram = audio_probe(
        settings=settings,
        base_url="http://127.0.0.1:38091",
        response_format="wav",
        artifacts_dir=artifacts_dir,
    )

    assert result.ok is False
    assert result.error_message == '{"error":{"message":"Invalid speaker"}}'
    assert result.output_path is None
    assert stale_output_path.exists() is False
    assert (artifacts_dir / "sample.wav.error.txt").exists() is True
    assert peak_busy == 0
    assert peak_vram == 0


def test_audio_probe_success_removes_stale_error_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakeSampler:
        def start(self) -> None:
            return None

        def stop(self) -> tuple[int, int]:
            return (0, 0)

    class _FakeResponse:
        status_code = 200
        headers = {"content-type": "audio/wav"}
        content = b"RIFFfakewav"
        text = ""
        is_success = True

    class _FakeClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 600.0

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
            return False

        def post(self, url: str, json: dict[str, str]) -> _FakeResponse:
            assert url == "http://127.0.0.1:38091/v1/audio/speech"
            assert json["voice"] == "ryan"
            return _FakeResponse()

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes._GpuSampler",
        _FakeSampler,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes.httpx.Client",
        _FakeClient,
    )
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    stale_error_path = artifacts_dir / "sample.wav.error.txt"
    stale_error_path.write_text("old error\n", encoding="utf-8")
    settings = build_settings(tmp_path)

    result, peak_busy, peak_vram = audio_probe(
        settings=settings,
        base_url="http://127.0.0.1:38091",
        response_format="wav",
        artifacts_dir=artifacts_dir,
    )

    assert result.ok is True
    assert result.output_path == (artifacts_dir / "sample.wav").as_posix()
    assert stale_error_path.exists() is False
    assert peak_busy == 0
    assert peak_vram == 0


def test_report_helpers_write_expected_json_and_markdown(tmp_path: Path) -> None:
    report = BenchmarkReport(
        benchmark_id="tts-sidecar-hemma",
        generated_at="2026-03-06T12:00:00Z",
        repo_head="abc123",
        host_base_url="http://127.0.0.1:38091",
        internal_base_url="http://sir-convert-a-lot-tts-tts-sidecar:8091",
        host_hf_cache_dir="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        speech_request=SpeechRequestEvidence(
            task_type="Base",
            model="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            language="English",
            voice=None,
            probe_text_path="build/verification/tts-sidecar-hemma/inputs/probe_text.txt",
            instructions_path="build/verification/tts-sidecar-hemma/inputs/instructions.txt",
            reference_audio_path=(
                "build/verification/tts-sidecar-hemma/inputs/reference_audio.wav"
            ),
            reference_audio_sha256="cafebabe",
            reference_audio_duration_seconds=7.9,
            reference_transcript_path=(
                "build/verification/tts-sidecar-hemma/inputs/reference_transcript.txt"
            ),
        ),
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
            container_name="sir_convert_a_lot_tts_tts-sidecar",
            python_version="3.12.11",
            package_versions={"vllm": "0.16.0", "vllm-omni": None, "vllm_omni": None},
            stage_config_path="/workspace/tts-sidecar-stage-config.yaml",
            hf_home="/cache/huggingface",
            hf_hub_cache="/cache/huggingface/hub",
            transformers_cache="/cache/huggingface",
            triton_flash_attn_enabled=True,
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
                output_path="build/verification/tts-sidecar-hemma/artifacts/sample.wav",
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
        docker_logs_path="build/verification/tts-sidecar-hemma/docker_logs.txt",
    )

    json_path = tmp_path / "report.json"
    write_json(json_path, report)
    markdown = build_report_markdown(report)

    assert '"benchmark_id": "tts-sidecar-hemma"' in json_path.read_text(encoding="utf-8")
    assert "## Speech Request" in markdown
    assert "`Qwen/Qwen3-TTS-12Hz-0.6B-Base`" in markdown
    assert "## Sidecar Runtime" in markdown
    assert "`3.12.11`" in markdown
    assert "/srv/scratch/sir-convert-a-lot/cache/huggingface" in markdown
