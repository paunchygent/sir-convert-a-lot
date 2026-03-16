"""Tests for the canonical Task 203 codebook-fusion proof surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import SmokeProbeResult
from scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof import (
    build_codebook_fusion_probe_command,
    main,
    parse_args,
    run_codebook_fusion_probe,
)


def test_parse_args_defaults_are_bounded() -> None:
    """The proof surface should expose deterministic bounded defaults."""
    settings = parse_args([])

    assert settings.output_root == Path("build/verification/qwen-codebook-fusion-proof")
    assert settings.batch_size == 8
    assert settings.sequence_length == 508
    assert settings.codebook_count == 15
    assert settings.embedding_dim == 2048
    assert settings.benchmark_iterations == 25
    assert settings.warmup_iterations == 10
    assert settings.dtype_names == ("bfloat16", "float16")
    assert settings.seeds == (0, 1, 2)
    assert settings.build_image is True


def test_build_probe_command_uses_rocm_runtime_flags() -> None:
    """The in-container proof command should keep the governed ROCm posture."""
    settings = parse_args(
        [
            "--batch-size",
            "4",
            "--benchmark-iterations",
            "12",
            "--warmup-iterations",
            "3",
            "--dtypes",
            "bf16,fp16",
            "--seeds",
            "7,11",
        ]
    )
    mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )

    command = build_codebook_fusion_probe_command(settings, hf_mount=mount)

    assert "--device" in command
    assert "/dev/kfd" in command
    assert "/dev/dri" in command
    assert "--ipc=host" in command
    assert "HF_HOME=/cache/huggingface" in command
    assert f"{mount.effective_root.as_posix()}:/cache/huggingface" in command
    assert "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_probe" in command
    assert "bfloat16,float16" in command
    assert "7,11" in command


def test_run_codebook_fusion_probe_parses_json_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The proof runner should parse the in-container JSON payload."""
    settings = parse_args([])
    mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=False,
    )

    def fake_docker_checked(args: list[str], *, label: str) -> str:
        assert args[0] == "run"
        assert label == "docker run qwen codebook fusion probe"
        return json.dumps(
            {
                "generated_at": "2026-03-16T17:00:00Z",
                "device_name": "AMD Radeon",
                "torch_version": "2.10.0+rocm7.1",
                "torch_hip_version": "7.1.25424",
                "shape": {
                    "batch_size": 8,
                    "sequence_length": 508,
                    "codebook_count": 15,
                    "embedding_dim": 2048,
                },
                "seeds": [0, 1, 2],
                "reference_dtype": "float32",
                "benchmark_iterations": 25,
                "warmup_iterations": 10,
                "dtype_summaries": [
                    {
                        "dtype": "bfloat16",
                        "seed_results": [],
                        "naive_mean_runtime_ms": 1.0,
                        "candidate_mean_runtime_ms": 1.1,
                        "candidate_runtime_ratio_vs_naive": 1.1,
                        "naive_worst_max_abs_error": 0.5,
                        "candidate_worst_max_abs_error": 0.25,
                        "naive_mean_mean_abs_error": 0.1,
                        "candidate_mean_mean_abs_error": 0.05,
                        "candidate_error_better_or_equal_all_seeds": True,
                    }
                ],
            }
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof.docker_checked",
        fake_docker_checked,
    )

    payload, command = run_codebook_fusion_probe(settings, hf_mount=mount)

    assert command[0:3] == ["sudo", "-n", "docker"]
    assert payload["device_name"] == "AMD Radeon"
    dtype_summaries = payload["dtype_summaries"]
    assert isinstance(dtype_summaries, list)
    assert dtype_summaries[0]["candidate_error_better_or_equal_all_seeds"] is True


def test_codebook_fusion_proof_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The proof runner should emit deterministic report artifacts."""
    mount = MountResolution(
        canonical_root=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        effective_root=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        used_home_mount=False,
    )
    smoke_result = SmokeProbeResult(
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        resolved_model_path="verified-in-container",
        resolved_config_path="verified-in-container",
        tts_model_type="qwen3_tts",
        torch_version="2.10.0+rocm7.1",
        torchaudio_version="2.10.0+rocm7.1",
        torch_cuda_available=True,
        torch_cuda_device_count=1,
        torch_hip_version="7.1.25424",
        flash_attn_importable=True,
        flash_attn_version="2.8.3",
        flash_attn_model_load_ok=True,
        dependency_versions={"transformers": "4.57.1"},
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof.run_checked",
        lambda command, *, label: f"{label}:{' '.join(command)}",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof.prepare_qwen_image",
        lambda settings: (False, "sha256:image-id"),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof.resolve_effective_hf_cache_dir",
        lambda settings: mount,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof.run_smoke_probe",
        lambda settings, *, hf_mount: (smoke_result, ["sudo", "-n", "docker", "run"]),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof.run_codebook_fusion_probe",
        lambda settings, *, hf_mount: (
            {
                "device_name": "AMD Radeon",
                "dtype_summaries": [
                    {
                        "dtype": "bfloat16",
                        "naive_mean_runtime_ms": 1.0,
                        "candidate_mean_runtime_ms": 1.1,
                        "candidate_runtime_ratio_vs_naive": 1.1,
                        "naive_worst_max_abs_error": 0.5,
                        "candidate_worst_max_abs_error": 0.25,
                        "candidate_error_better_or_equal_all_seeds": True,
                    }
                ],
            },
            ["sudo", "-n", "docker", "run", "probe"],
        ),
    )

    result = main(["--output-root", tmp_path.as_posix(), "--skip-build"])

    assert result == 0
    report_payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report_payload["image_id"] == "sha256:image-id"
    assert report_payload["probe_result"]["device_name"] == "AMD Radeon"
    assert report_payload["smoke_probe_result"]["torch_cuda_available"] is True
    assert report_payload["smoke_probe_command"] == ["sudo", "-n", "docker", "run"]
    assert (tmp_path / "report.md").exists() is True
