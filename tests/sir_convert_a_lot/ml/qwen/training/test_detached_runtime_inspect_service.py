"""Focused tests for detached Qwen inspect and stop services.

Purpose:
    Verify the bounded detached inspection and stop services after the
    orchestrator split.

Relationships:
    - Exercises `detached_runtime.inspect_service`.
    - Exercises `detached_runtime.stop_service`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    inspect_detached_training,
    stop_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    DetachedStop,
    TrainingSettingsSnapshot,
)


def _launch(run_root: Path) -> DetachedLaunch:
    """Build one detached launch payload for focused runtime tests."""
    return DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_kind="training",
        launch_id="qwen-20260309t120000z",
        container_name="qwen-20260309t120000z-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=run_root.as_posix(),
        pilot_bundle_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle",
        train_jsonl="/bundle/manifests/train.prepared.jsonl",
        eval_jsonl="/bundle/manifests/eval.prepared.jsonl",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path="containers/qwen-finetune-hemma/Dockerfile",
        resumed_from_checkpoint_path=None,
        settings=TrainingSettingsSnapshot(
            output_root="/srv/scratch/sir-convert-a-lot/build/verification/qwen-training",
            image="sir-convert-a-lot-qwen-finetune-hemma:latest",
            hf_cache_dir="/srv/scratch/sir-convert-a-lot/cache/huggingface",
            hf_cache_home_mount="/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
            scratch_build_root="/srv/scratch/sir-convert-a-lot/build",
            scratch_build_home_mount="/home/paunchygent/.data/sir-convert-a-lot/build",
            pilot_bundle_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle",
            runs_root="/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune",
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            batch_size=8,
            throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=500,
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        ),
        command=["sudo", "-n", "docker", "run", "-d"],
    )


def test_inspect_detached_training_reads_container_status_and_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detached inspection should combine Docker state and persisted artifacts."""
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "status.json").write_text(
        json.dumps({"status": "completed", "optimizer_steps_completed": 8}) + "\n",
        encoding="utf-8",
    )
    (run_root / "report.json").write_text(
        json.dumps({"status": "completed", "training_summary": {"optimizer_steps_completed": 8}})
        + "\n",
        encoding="utf-8",
    )
    (run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": (run_root / "checkpoints/state-step-00000008").as_posix()})
        + "\n",
        encoding="utf-8",
    )

    def fake_docker_checked(args: list[str], *, label: str) -> str:
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
            return "training log tail"
        raise AssertionError(f"Unexpected docker args: {args} ({label})")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.inspect_service.docker_checked",
        fake_docker_checked,
    )

    status = inspect_detached_training(_launch(run_root))

    assert status.running is False
    assert status.pilot_status_found is True
    assert status.pilot_report_found is True
    assert status.latest_checkpoint_found is True
    assert status.logs_tail == "training log tail"


def test_stop_detached_training_calls_docker_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Detached stop should proxy one bounded docker stop call."""
    captured: dict[str, object] = {}

    def fake_docker_checked(args: list[str], *, label: str) -> str:
        captured["args"] = args
        captured["label"] = label
        return "qwen-prev-container"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.stop_service.docker_checked",
        fake_docker_checked,
    )

    stopped = stop_detached_training(_launch(Path("/tmp/qwen-run")))

    assert isinstance(stopped, DetachedStop)
    assert captured["args"] == ["stop", "--time", "300", "qwen-20260309t120000z-container"]
