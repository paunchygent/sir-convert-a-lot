"""Tests for the detached Task 101 Qwen pilot lane."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_LR,
    DEFAULT_MAX_STEPS,
    DEFAULT_MODEL_ID,
    DEFAULT_NUM_EPOCHS,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    _build_parser,
    _ensure_train_manifest_exists,
    _resolve_launch_root,
)
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import MountResolution
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime import (
    Task101DetachedLaunch,
    Task101PilotSettings,
    build_detached_pilot_command,
    inspect_detached_pilot,
)


def test_task101_parser_launch_defaults() -> None:
    """The Task 101 runner should expose deterministic bounded pilot defaults."""
    parser = _build_parser()
    args = parser.parse_args(["launch"])

    assert args.model_id == DEFAULT_MODEL_ID
    assert args.train_manifest_family == DEFAULT_TRAIN_MANIFEST_FAMILY
    assert args.batch_size == DEFAULT_BATCH_SIZE
    assert args.lr == DEFAULT_LR
    assert args.num_epochs == DEFAULT_NUM_EPOCHS
    assert args.max_steps == DEFAULT_MAX_STEPS
    assert args.skip_build is False


def test_task101_status_defaults_to_latest_pointer() -> None:
    """The Task 101 status command should default to the latest launch pointer."""
    parser = _build_parser()
    args = parser.parse_args(["status"])

    assert args.launch_root is None


def test_build_detached_pilot_command_uses_rocm_mounts_and_prepared_manifest() -> None:
    """The detached pilot command should target the prepared pilot manifest on scratch."""
    settings = Task101PilotSettings(
        output_root=Path("/srv/scratch/sir-convert-a-lot/build/verification/task-101"),
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        scratch_build_root=Path("/srv/scratch/sir-convert-a-lot/build"),
        scratch_build_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/build"),
        promoted_corpus_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus"
        ),
        runs_root=Path("/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune"),
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_manifest_family="swedish_pilot_train",
        batch_size=1,
        lr=2e-5,
        num_epochs=1,
        max_steps=8,
    )
    hf_mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )
    scratch_mount = MountResolution(
        canonical_root=settings.scratch_build_root,
        effective_root=settings.scratch_build_home_mount,
        used_home_mount=True,
    )

    command, run_root = build_detached_pilot_command(
        settings,
        repo_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id="task101-20260309t120000z",
        container_name="task101-20260309t120000z-container",
    )

    assert run_root.as_posix().endswith("/task101-20260309t120000z")
    assert "--device" in command
    assert "/dev/kfd" in command
    assert "--ipc=host" in command
    assert "HF_HOME=/cache/huggingface" in command
    assert "/home/paunchygent/.data/sir-convert-a-lot/build:/app/build" in command
    assert (
        "/app/build/reference/qwen3-tts-swedish-corpus/manifests/"
        "swedish_pilot_train.prepared.jsonl" in command
    )


def test_inspect_detached_pilot_reads_container_status_and_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The detached Task 101 status view should combine Docker and pilot outputs."""
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "status.json").write_text(
        json.dumps({"status": "completed", "optimizer_steps_completed": 8}) + "\n",
        encoding="utf-8",
    )
    (run_root / "report.json").write_text(
        json.dumps({"training_summary": {"optimizer_steps_completed": 8}}) + "\n",
        encoding="utf-8",
    )
    launch = Task101DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="task101-20260309t120000z",
        container_name="task101-20260309t120000z-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=run_root.as_posix(),
        promoted_corpus_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus",
        train_manifest_family="swedish_pilot_train",
        command=["sudo", "-n", "docker", "run", "-d"],
    )

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        if args[0] == "inspect":
            return json.dumps(
                [
                    {
                        "Id": "container-id",
                        "State": {
                            "Status": "exited",
                            "Running": False,
                            "ExitCode": 0,
                            "OOMKilled": False,
                            "StartedAt": "2026-03-09T12:00:01Z",
                            "FinishedAt": "2026-03-09T12:04:01Z",
                        },
                    }
                ]
            )
        if args[0] == "logs":
            return "pilot log tail"
        raise AssertionError(f"Unexpected docker args: {args} ({label})")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime.docker_checked",
        _fake_docker_checked,
    )

    status = inspect_detached_pilot(launch)

    assert status.running is False
    assert status.exit_code == 0
    assert status.pilot_status_found is True
    assert status.pilot_report_found is True
    assert status.pilot_report is not None
    training_summary = status.pilot_report.get("training_summary")
    assert isinstance(training_summary, dict)
    assert training_summary["optimizer_steps_completed"] == 8
    assert status.logs_tail == "pilot log tail"


def test_task101_resolve_launch_root_uses_latest_pointer(tmp_path: Path) -> None:
    """Status inspection should reuse the latest recorded launch when present."""
    output_root = tmp_path / "verification"
    launch_root = output_root / "task101-20260309t120000z"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "latest-launch.json").write_text(
        json.dumps({"launch_root": launch_root.as_posix()}) + "\n",
        encoding="utf-8",
    )

    assert _resolve_launch_root(output_root, None) == launch_root


def test_task101_requires_prepared_manifest_before_launch(tmp_path: Path) -> None:
    """Launch should fail fast when the promoted preprocessing family is missing."""
    promoted_root = tmp_path / "reference"
    promoted_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SystemExit, match="prepared manifest"):
        _ensure_train_manifest_exists(promoted_root, "swedish_pilot_train")
