"""Tests for the detached Task 108 Qwen proof runner and runtime."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task108_hemma_qwen_detached_proof import (
    DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    DEFAULT_CONTAINER_NAME_PREFIX,
    DEFAULT_GPU_ASR_WORKER_COUNT,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_ROW_WORKER_COUNT,
    _build_parser,
    _load_launch,
)
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import MountResolution
from scripts.sir_convert_a_lot.devops.task108_qwen_detached_proof_runtime import (
    Task108DetachedProofLaunch,
    build_detached_task108_command,
    inspect_detached_task108_proof,
)
from scripts.sir_convert_a_lot.devops.task109_qwen_containerized_preprocessing_runtime import (
    Task109ContainerizedPreprocessingSettings,
)


def test_task108_detached_parser_launch_defaults() -> None:
    """The detached Task 108 runner should expose deterministic launch defaults."""
    parser = _build_parser()
    args = parser.parse_args(["launch"])

    assert args.output_root == DEFAULT_OUTPUT_ROOT
    assert args.container_name_prefix == DEFAULT_CONTAINER_NAME_PREFIX
    assert args.audio_codes_chunk_size == DEFAULT_AUDIO_CODES_CHUNK_SIZE
    assert args.row_worker_count == DEFAULT_ROW_WORKER_COUNT
    assert args.gpu_asr_worker_count == DEFAULT_GPU_ASR_WORKER_COUNT


def test_build_detached_task108_command_drops_rm_and_adds_name() -> None:
    """The detached Task 108 command should launch a named background container."""
    settings = Task109ContainerizedPreprocessingSettings(
        output_root=Path("build/verification/task-109-qwen-containerized-preprocessing"),
        task103_runs_root=Path("/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing"),
        task103_run_id="task108-proof-run",
        task103_run_root=None,
        task103_promote_on_success=False,
        dockerfile_path=Path("containers/qwen-finetune-hemma/Dockerfile"),
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        scratch_build_root=Path("/srv/scratch/sir-convert-a-lot/build"),
        scratch_build_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/build"),
        data_root=Path("/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"),
        data_root_home_mount=Path(
            "/home/paunchygent/.data/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"
        ),
        build_image=False,
        fleurs_max_rows_per_split=8,
        rixvox_splits=("train", "dev", "test"),
        rixvox_max_rows_per_split=64,
        audio_codes_chunk_size=4,
        row_worker_count=10,
        gpu_asr_worker_count=5,
    )
    repo_root = Path("/home/paunchygent/apps/sir-convert-a-lot")
    hf_mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )
    data_mount = MountResolution(
        canonical_root=settings.data_root,
        effective_root=settings.data_root_home_mount,
        used_home_mount=True,
    )
    scratch_mount = MountResolution(
        canonical_root=settings.scratch_build_root,
        effective_root=settings.scratch_build_home_mount,
        used_home_mount=True,
    )

    command = build_detached_task108_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        data_mount=data_mount,
        scratch_mount=scratch_mount,
        container_name="task108-qwen-proof-20260309t120000z",
    )

    assert command[0:4] == ["run", "-d", "--name", "task108-qwen-proof-20260309t120000z"]
    assert "--rm" not in command
    assert "--audio-codes-chunk-size" in command
    assert "4" in command
    assert "--run-id" in command
    assert "task108-proof-run" in command
    assert "--row-worker-count" in command
    assert "10" in command
    assert "--gpu-asr-worker-count" in command
    assert "5" in command


def test_load_launch_reads_recorded_metadata(tmp_path: Path) -> None:
    """The detached Task 108 status surface should load prior launch metadata."""
    output_root = tmp_path / "proof"
    output_root.mkdir(parents=True, exist_ok=True)
    launch_path = output_root / "launch.json"
    launch_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-03-09T12:00:00Z",
                "container_name": "task108-qwen-proof-20260309t120000z",
                "container_id": "container-id",
                "repo_root": "/home/paunchygent/apps/sir-convert-a-lot",
                "task103_run_root": (
                    "/srv/scratch/sir-convert-a-lot/build/runs/"
                    "qwen3-tts-swedish-preprocessing/task108-qwen-proof-20260309t120000z"
                ),
                "task103_promoted_root": (
                    "/home/paunchygent/apps/sir-convert-a-lot/"
                    "build/reference/qwen3-tts-swedish-corpus"
                ),
                "command": ["sudo", "-n", "docker", "run", "-d"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    launch = _load_launch(output_root)

    assert launch.container_name == "task108-qwen-proof-20260309t120000z"
    assert launch.command == ["sudo", "-n", "docker", "run", "-d"]


def test_inspect_detached_task108_proof_reads_container_and_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The detached Task 108 status surface should combine Docker and report state."""
    repo_root = tmp_path / "repo"
    report_path = repo_root / "build/reference/qwen3-tts-swedish-corpus/report.json"
    run_root = tmp_path / "runs/task108-qwen-proof-20260309t120000z"
    report_path = run_root / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "output_root": report_path.parent.as_posix(),
                "prepared_rows": 23,
                "manifest_counts": {"swedish_smoke_train": 51},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    launch = Task108DetachedProofLaunch(
        generated_at="2026-03-09T12:00:00Z",
        container_name="task108-qwen-proof-20260309t120000z",
        container_id="container-id",
        repo_root=repo_root.as_posix(),
        task103_run_root=report_path.parent.as_posix(),
        task103_promoted_root=(repo_root / "build/reference/qwen3-tts-swedish-corpus").as_posix(),
        command=["sudo", "-n", "docker", "run", "-d"],
    )

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        if args[0] == "inspect":
            return json.dumps(
                [
                    {
                        "Id": "container-id",
                        "State": {
                            "Status": "running",
                            "Running": True,
                            "ExitCode": 0,
                            "OOMKilled": False,
                            "StartedAt": "2026-03-09T12:00:01Z",
                            "FinishedAt": "0001-01-01T00:00:00Z",
                        },
                    }
                ]
            )
        if args[0] == "logs":
            return "worker log tail"
        raise AssertionError(f"Unexpected docker args: {args} ({label})")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task108_qwen_detached_proof_runtime.docker_checked",
        _fake_docker_checked,
    )

    status = inspect_detached_task108_proof(launch)

    assert status.status == "running"
    assert status.running is True
    assert status.task103_report_found is True
    assert status.task103_report is not None
    assert status.task103_report["prepared_rows"] == 23
    assert status.logs_tail == "worker log tail"
