"""Tests for the Task 81 Hemma OpenVoice benchmark helpers.

Purpose:
    Catch local regressions in cache resolution, Docker command assembly, and
    normalized synthesis probing before the live Hemma benchmark is rerun.

Relationships:
    - Exercises `run_task81_hemma_openvoice_benchmark` argument parsing.
    - Exercises `task81_openvoice_runtime` cache and sidecar helper functions.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Literal

import pytest

from scripts.sir_convert_a_lot.devops import run_task81_hemma_openvoice_benchmark
from scripts.sir_convert_a_lot.devops.task81_openvoice_reporting import (
    BenchmarkReport,
    CacheEvidence,
    GpuIdentity,
    InternalProbeEvidence,
    ReferenceAudioEvidence,
    SidecarRuntime,
    SynthesisProbeResult,
    build_report_markdown,
    write_json,
)
from scripts.sir_convert_a_lot.devops.task81_openvoice_runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_OPENVOICE_HOME,
    BenchmarkSettings,
    MountResolution,
    prefetch_openvoice_assets,
    reference_audio_evidence,
    resolve_effective_cache_dir,
    start_sidecar,
    synthesize_probe,
)
from scripts.sir_convert_a_lot.tts_sidecar.contracts import (
    CacheCapability,
    CapabilityResponse,
    LanguageCapability,
    LanguageSupportLevel,
    NetworkScope,
    OutputFormat,
    RuntimeCapability,
    SynthesisCapability,
    VoiceCapability,
    VoiceMode,
)


def _capabilities() -> CapabilityResponse:
    return CapabilityResponse(
        backend_id="openvoice_v2",
        backend_version="74a1d147",
        backend_profile="mms_tts_swe_base",
        runtime=RuntimeCapability(
            python_version="3.12.12",
            gpu_required=True,
            supports_rocm=True,
            network_scope=NetworkScope.INTERNAL_ONLY,
        ),
        cache=CacheCapability(
            cache_family="openvoice_assets",
            host_root="/srv/scratch/sir-convert-a-lot/cache/openvoice",
            container_root="/cache/openvoice",
            reuse_strategy="persistent_host_cache",
        ),
        auxiliary_caches=[
            CacheCapability(
                cache_family="huggingface",
                host_root="/srv/scratch/sir-convert-a-lot/cache/huggingface",
                container_root="/cache/huggingface",
                reuse_strategy="persistent_host_cache",
            )
        ],
        synthesis=SynthesisCapability(
            output_formats=[OutputFormat.WAV],
            sample_rates_hz=[22050],
            supports_streaming=False,
        ),
        voice=VoiceCapability(
            modes=[VoiceMode.REFERENCE_CLONE],
            reference_transcript_required=False,
            reference_audio_required=True,
        ),
        languages=[
            LanguageCapability(code="sv", support_level=LanguageSupportLevel.CROSS_LINGUAL_CLAIMED)
        ],
    )


def test_parse_args_accepts_reference_audio_only(tmp_path: Path) -> None:
    reference_audio = tmp_path / "voice.m4a"
    reference_audio.write_bytes(b"audio")

    settings = run_task81_hemma_openvoice_benchmark._parse_args(
        [
            "--reference-audio",
            reference_audio.as_posix(),
        ]
    )

    assert settings.reference_audio_path == reference_audio
    assert settings.image == "sir-convert-a-lot/openvoice-sidecar-task81:local"


def test_resolve_effective_cache_dir_uses_home_bind_mount_when_srv_probe_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_dir = tmp_path / "data-cache"
    home_mount = tmp_path / "home-cache"
    probe_calls: list[Path] = []
    bind_calls: list[tuple[Path, Path]] = []

    def _fake_probe(candidate: Path, *, image: str) -> bool:
        assert image == "test-image"
        probe_calls.append(candidate)
        return candidate == home_mount

    def _fake_bind(canonical_dir: Path, home_dir: Path) -> None:
        bind_calls.append((canonical_dir, home_dir))

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime._probe_docker_bind_mount",
        _fake_probe,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime._ensure_home_bind_mount",
        _fake_bind,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime._is_srv_cache_path",
        lambda path: path == cache_dir,
    )

    resolved = resolve_effective_cache_dir(
        cache_dir=cache_dir, home_mount=home_mount, image="test-image"
    )

    assert resolved.effective_root == home_mount
    assert resolved.canonical_root == cache_dir
    assert resolved.used_home_mount is True
    assert probe_calls == [cache_dir, home_mount]
    assert bind_calls == [(cache_dir, home_mount)]


def test_prefetch_openvoice_assets_extracts_archive_without_redownload(tmp_path: Path) -> None:
    cache_root = tmp_path / "openvoice-cache"
    archive_path = cache_root / "downloads" / "checkpoints_v2_0417.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("checkpoints_v2/converter/config.json", "{}")
        archive.writestr("checkpoints_v2/converter/checkpoint.pth", "weights")
    settings = BenchmarkSettings(
        output_root=tmp_path / "output",
        dockerfile_path=tmp_path / "Dockerfile",
        image="test-image",
        openvoice_checkpoint_url="https://example.invalid/checkpoints.zip",
        base_model_id="facebook/mms-tts-swe",
        network="hule-network",
        network_alias="task81-sidecar",
        container_name="task81",
        service_container="sir_convert_a_lot_prod",
        container_port=8092,
        host_port=38092,
        startup_timeout_seconds=600.0,
        hf_cache_dir=tmp_path / "hf-cache",
        hf_cache_home_mount=tmp_path / "hf-home",
        openvoice_cache_dir=cache_root,
        openvoice_cache_home_mount=tmp_path / "ov-home",
        reference_audio_path=tmp_path / "voice.m4a",
        probe_text="Hej världen",
        build_image=False,
        retain_container=False,
    )
    mount = MountResolution(
        canonical_root=cache_root, effective_root=cache_root, used_home_mount=False
    )

    prefetch_openvoice_assets(settings, mount)

    assert (cache_root / "checkpoints_v2" / "converter" / "config.json").exists() is True
    assert (cache_root / "checkpoints_v2" / "converter" / "checkpoint.pth").exists() is True


def test_start_sidecar_uses_persistent_cache_mounts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded_commands: list[list[str]] = []

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        assert label == "docker run task81 sidecar"
        recorded_commands.append(args)
        return "container-id"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime.docker_checked",
        _fake_docker_checked,
    )
    settings = BenchmarkSettings(
        output_root=tmp_path / "output",
        dockerfile_path=tmp_path / "Dockerfile",
        image="test-image",
        openvoice_checkpoint_url="https://example.invalid/checkpoints.zip",
        base_model_id="facebook/mms-tts-swe",
        network="hule-network",
        network_alias="task81-sidecar",
        container_name="task81",
        service_container="sir_convert_a_lot_prod",
        container_port=8092,
        host_port=38092,
        startup_timeout_seconds=600.0,
        hf_cache_dir=tmp_path / "hf-cache",
        hf_cache_home_mount=tmp_path / "hf-home",
        openvoice_cache_dir=tmp_path / "ov-cache",
        openvoice_cache_home_mount=tmp_path / "ov-home",
        reference_audio_path=tmp_path / "voice.m4a",
        probe_text="Hej världen",
        build_image=False,
        retain_container=False,
    )
    hf_mount = MountResolution(
        canonical_root=tmp_path / "hf-cache",
        effective_root=tmp_path / "hf-effective",
        used_home_mount=False,
    )
    openvoice_mount = MountResolution(
        canonical_root=tmp_path / "ov-cache",
        effective_root=tmp_path / "ov-effective",
        used_home_mount=True,
    )

    start_sidecar(settings, hf_mount=hf_mount, openvoice_mount=openvoice_mount)

    command = recorded_commands[0]
    assert f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}" in command
    assert f"{openvoice_mount.effective_root.as_posix()}:{CONTAINER_OPENVOICE_HOME}" in command
    assert (
        f"SIR_TTS_SIDECAR_OPENVOICE_CACHE_HOST_ROOT={openvoice_mount.canonical_root.as_posix()}"
        in command
    )
    assert f"SIR_TTS_SIDECAR_HF_CACHE_HOST_ROOT={hf_mount.canonical_root.as_posix()}" in command


def test_reference_audio_evidence_uses_benchmark_image_ffprobe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reference_audio = tmp_path / "voice.m4a"
    reference_audio.write_bytes(b"audio")
    recorded: list[list[str]] = []

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        assert label == "docker run ffprobe reference audio"
        recorded.append(args)
        return (
            '{"streams":[{"codec_type":"audio","sample_rate":"48000"}],'
            '"format":{"duration":"89.130667"}}'
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime.docker_checked",
        _fake_docker_checked,
    )

    evidence = reference_audio_evidence(reference_audio, image="test-image")

    assert evidence.filename == "voice.m4a"
    assert evidence.reference_role == "teacher_voice_cloning_reference"
    assert evidence.sample_rate_hz == 48000
    assert evidence.duration_seconds == 89.130667
    command = recorded[0]
    assert command[0:4] == ["run", "--rm", "-v", f"{reference_audio.parent.as_posix()}:/input:ro"]
    assert command[4:7] == ["--entrypoint", "ffprobe", "test-image"]
    assert command[-1] == "/input/voice.m4a"


def test_synthesize_probe_posts_normalized_contract_and_writes_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakeSampler:
        def start(self) -> None:
            return None

        def stop(self) -> tuple[int, int]:
            return (3, 4)

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

        def post(
            self, url: str, data: dict[str, str], files: dict[str, tuple[str, bytes, str]]
        ) -> _FakeResponse:
            assert url == "http://127.0.0.1:38092/synthesize"
            assert data["voice_mode"] == "reference_clone"
            assert data["language"] == "sv"
            assert files["reference_audio"][0] == "voice.m4a"
            return _FakeResponse()

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime._GpuSampler",
        _FakeSampler,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime.httpx.Client",
        _FakeClient,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task81_openvoice_runtime._wav_metadata",
        lambda _: (22050, 1.25),
    )
    reference_audio = tmp_path / "voice.m4a"
    reference_audio.write_bytes(b"ref-audio")
    settings = BenchmarkSettings(
        output_root=tmp_path / "output",
        dockerfile_path=tmp_path / "Dockerfile",
        image="test-image",
        openvoice_checkpoint_url="https://example.invalid/checkpoints.zip",
        base_model_id="facebook/mms-tts-swe",
        network="hule-network",
        network_alias="task81-sidecar",
        container_name="task81",
        service_container="sir_convert_a_lot_prod",
        container_port=8092,
        host_port=38092,
        startup_timeout_seconds=600.0,
        hf_cache_dir=tmp_path / "hf-cache",
        hf_cache_home_mount=tmp_path / "hf-home",
        openvoice_cache_dir=tmp_path / "ov-cache",
        openvoice_cache_home_mount=tmp_path / "ov-home",
        reference_audio_path=reference_audio,
        probe_text="Hej världen",
        build_image=False,
        retain_container=False,
    )
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    result, peak_busy, peak_vram = synthesize_probe(
        settings=settings,
        base_url="http://127.0.0.1:38092",
        artifacts_dir=artifacts_dir,
    )

    assert result.ok is True
    assert result.output_path == (artifacts_dir / "sample_sv.wav").as_posix()
    assert peak_busy == 3
    assert peak_vram == 4


def test_report_helpers_render_task81_markdown(tmp_path: Path) -> None:
    report = BenchmarkReport(
        benchmark_id="task-81-openvoice-v2-hemma",
        generated_at="2026-03-06T12:00:00Z",
        repo_head="abc123",
        host_base_url="http://127.0.0.1:38092",
        internal_base_url="http://sir-convert-a-lot-openvoice-task81:8092",
        gpu_identity=GpuIdentity(
            product_name="AMD Radeon AI PRO R9700",
            gfx_architecture="gfx1201",
            vram_total_bytes=32061259776,
            peak_gpu_busy_percent=41,
            peak_vram_used_bytes=3145728000,
        ),
        cache_evidence=CacheEvidence(
            openvoice_host_root="/srv/scratch/sir-convert-a-lot/cache/openvoice",
            openvoice_container_root="/cache/openvoice",
            hf_host_root="/srv/scratch/sir-convert-a-lot/cache/huggingface",
            hf_container_root="/cache/huggingface",
            openvoice_home_mount_used=False,
            hf_home_mount_used=True,
        ),
        sidecar_runtime=SidecarRuntime(
            image="test-image",
            image_id="sha256:test",
            container_name="task81",
            python_version="3.12.12",
            package_versions={"openvoice": "0.0.0", "transformers": "4.57.6", "torch": "2.10.0"},
            hf_home="/cache/huggingface",
            hf_hub_cache="/cache/huggingface/hub",
            transformers_cache="/cache/huggingface",
            openvoice_checkpoints_root="/cache/openvoice/checkpoints_v2",
        ),
        internal_probe=InternalProbeEvidence(
            host_probe_ok=True,
            service_probe_ok=True,
            service_backend_id="openvoice_v2",
            service_ready=True,
        ),
        capabilities=_capabilities(),
        reference_audio=ReferenceAudioEvidence(
            input_path="/tmp/voice.m4a",
            filename="voice.m4a",
            reference_role="teacher_voice_cloning_reference",
            duration_seconds=10.0,
            sample_rate_hz=48000,
        ),
        synthesis_result=SynthesisProbeResult(
            ok=True,
            status_code=200,
            content_type="audio/wav",
            byte_count=4096,
            sha256="deadbeef",
            output_path="build/verification/task-81-openvoice-v2-hemma/artifacts/sample_sv.wav",
            elapsed_seconds=2.0,
            sample_rate_hz=22050,
            duration_seconds=1.25,
            error_message=None,
        ),
        official_support_summary=["OpenVoice claims cross-lingual cloning."],
        listening_notes="Pending manual listening review.",
        pull_performed=False,
        build_performed=True,
        readiness_seconds=42.0,
        cleanup_performed=True,
        docker_logs_path="build/verification/task-81-openvoice-v2-hemma/docker_logs.txt",
    )

    json_path = tmp_path / "report.json"
    write_json(json_path, report)
    markdown = build_report_markdown(report)

    assert '"benchmark_id": "task-81-openvoice-v2-hemma"' in json_path.read_text(encoding="utf-8")
    assert "## Capability Snapshot" in markdown
    assert "openvoice_v2" in markdown
    assert "cross_lingual_claimed" in markdown
