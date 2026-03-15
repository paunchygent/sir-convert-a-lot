"""Tests for epoch-aware Qwen schedule control.

Purpose:
    Verify the new schedule runner chooses epoch boundaries from checkpoint
    metadata, preserves recorded path provenance, and fails closed when a
    training segment dies before the planned stop boundary.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner`.
    - Exercises the public `qwen-train schedule` CLI validation surface.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DurableCheckpointMetadata,
)
from scripts.sir_convert_a_lot.cli.ml.qwen_train import DEFAULT_DOCKERFILE_PATH, main
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    DetachedStatus,
    TrainingSettings,
    TrainingSettingsSnapshot,
)
from scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner import (
    _resume_from_checkpoint,
    _target_optimizer_step,
    run_schedule_cycle,
)


def _settings(*, scratch_root: Path) -> TrainingSettings:
    """Build one deterministic training-settings fixture."""
    return TrainingSettings(
        output_root=scratch_root / "verification/qwen-training",
        image="sir-convert-a-lot-qwen-finetune-hemma:latest",
        hf_cache_dir=scratch_root / "cache/huggingface",
        hf_cache_home_mount=scratch_root / "cache/huggingface-home",
        scratch_build_root=scratch_root,
        scratch_build_home_mount=scratch_root,
        pilot_bundle_root=scratch_root / "reference/qwen-bundle",
        runs_root=scratch_root / "runs/qwen",
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        batch_size=8,
        throughput_profile_label="hemma-throughput-balanced-v1",
        lr=2e-5,
        num_epochs=6,
        max_steps=6000,
        checkpoint_interval_steps=100,
        eval_interval_steps=100,
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )


def _launch_payload(*, scratch_root: Path, repo_root: Path) -> DetachedLaunch:
    """Build one detached launch payload for schedule tests."""
    settings = _settings(scratch_root=scratch_root)
    return DetachedLaunch(
        generated_at="2026-03-15T10:00:00Z",
        launch_id="launch-a",
        container_name="qwen-train-launch-a",
        container_id="container-id",
        repo_root=repo_root.as_posix(),
        run_root=(settings.runs_root / "launch-a").as_posix(),
        pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
        train_jsonl=(
            settings.pilot_bundle_root / "manifests/swedish_pilot_train.prepared.jsonl"
        ).as_posix(),
        eval_jsonl=(
            settings.pilot_bundle_root / "manifests/swedish_checkpoint_dev.prepared.jsonl"
        ).as_posix(),
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
        dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
        resumed_from_checkpoint_path=None,
        settings=TrainingSettingsSnapshot(
            output_root=settings.output_root.as_posix(),
            image=settings.image,
            hf_cache_dir=settings.hf_cache_dir.as_posix(),
            hf_cache_home_mount=settings.hf_cache_home_mount.as_posix(),
            scratch_build_root=settings.scratch_build_root.as_posix(),
            scratch_build_home_mount=settings.scratch_build_home_mount.as_posix(),
            pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
            runs_root=settings.runs_root.as_posix(),
            model_id=settings.model_id,
            train_manifest_family=settings.train_manifest_family,
            eval_manifest_family=settings.eval_manifest_family,
            batch_size=settings.batch_size,
            throughput_profile_label=settings.throughput_profile_label,
            lr=settings.lr,
            num_epochs=settings.num_epochs,
            max_steps=settings.max_steps,
            checkpoint_interval_steps=settings.checkpoint_interval_steps,
            eval_interval_steps=settings.eval_interval_steps,
            durable_checkpoint_retention=settings.durable_checkpoint_retention,
            durable_checkpoint_min_free_bytes=settings.durable_checkpoint_min_free_bytes,
        ),
        command=["docker", "run", "-d"],
    )


def _write_checkpoint_metadata(
    checkpoint_path: Path,
    *,
    optimizer_steps_completed: int,
    epoch: int,
    next_epoch: int,
    next_step_in_epoch: int,
) -> None:
    """Materialize one durable checkpoint metadata payload."""
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    metadata = DurableCheckpointMetadata(
        checkpoint_path=checkpoint_path.as_posix(),
        saved_at="2026-03-15T10:20:00Z",
        reason="interval",
        optimizer_steps_completed=optimizer_steps_completed,
        epoch=epoch,
        next_epoch=next_epoch,
        next_step_in_epoch=next_step_in_epoch,
    )
    (checkpoint_path / "training_state.json").write_text(
        json.dumps(asdict(metadata)) + "\n",
        encoding="utf-8",
    )
    (checkpoint_path / "accelerate_state_marker.txt").write_text("saved\n", encoding="utf-8")


def test_target_optimizer_step_uses_checkpoint_cursor_and_epoch_length() -> None:
    """Epoch-aware target math should use the checkpoint cursor, not raw row guesses."""
    checkpoint_metadata = DurableCheckpointMetadata(
        checkpoint_path="/tmp/state-step-00000042",
        saved_at="2026-03-15T10:20:00Z",
        reason="interval",
        optimizer_steps_completed=42,
        epoch=0,
        next_epoch=0,
        next_step_in_epoch=53,
    )

    target_step = _target_optimizer_step(
        checkpoint_metadata=checkpoint_metadata,
        dataloader_length=100,
        epochs_per_segment=2,
    )

    assert target_step == 79


def test_resume_from_checkpoint_uses_recorded_repo_root_and_dockerfile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Schedule resume should relaunch from the source repo root and dockerfile."""
    scratch_root = tmp_path / "srv/scratch/sir-convert-a-lot/build"
    settings = _settings(scratch_root=scratch_root)
    repo_root = tmp_path / "recorded-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    source_run_root = settings.runs_root / "launch-a"
    checkpoint_path = source_run_root / "checkpoints/state-step-00000100"
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    output_root = settings.output_root
    dockerfile_path = Path("containers/custom-qwen/Dockerfile")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.default_launch_id",
        lambda: "launch-b",
    )

    def fake_launch_detached_training(
        settings: TrainingSettings,
        *,
        repo_root: Path,
        hf_mount: MountResolution,
        scratch_mount: MountResolution,
        launch_id: str,
        container_name: str,
        launch_root: Path,
        dockerfile_path: Path | None,
        run_root: Path | None,
        resume_from_checkpoint: Path | None,
    ) -> DetachedLaunch:
        del hf_mount, scratch_mount
        assert dockerfile_path is not None
        assert run_root is not None
        assert resume_from_checkpoint is not None
        captured.update(
            {
                "repo_root": repo_root,
                "dockerfile_path": dockerfile_path,
                "run_root": run_root,
                "resume_from_checkpoint": resume_from_checkpoint,
                "launch_root": launch_root,
                "launch_id": launch_id,
            }
        )
        return DetachedLaunch(
            generated_at="2026-03-15T10:30:00Z",
            launch_id=launch_id,
            container_name=container_name,
            container_id="container-id",
            repo_root=repo_root.as_posix(),
            run_root=run_root.as_posix(),
            pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
            train_jsonl="train.jsonl",
            eval_jsonl="eval.jsonl",
            train_manifest_family=settings.train_manifest_family,
            eval_manifest_family=settings.eval_manifest_family,
            dockerfile_path=dockerfile_path.as_posix(),
            resumed_from_checkpoint_path=resume_from_checkpoint.as_posix(),
            settings=TrainingSettingsSnapshot(
                output_root=settings.output_root.as_posix(),
                image=settings.image,
                hf_cache_dir=settings.hf_cache_dir.as_posix(),
                hf_cache_home_mount=settings.hf_cache_home_mount.as_posix(),
                scratch_build_root=settings.scratch_build_root.as_posix(),
                scratch_build_home_mount=settings.scratch_build_home_mount.as_posix(),
                pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
                runs_root=settings.runs_root.as_posix(),
                model_id=settings.model_id,
                train_manifest_family=settings.train_manifest_family,
                eval_manifest_family=settings.eval_manifest_family,
                batch_size=settings.batch_size,
                throughput_profile_label=settings.throughput_profile_label,
                lr=settings.lr,
                num_epochs=settings.num_epochs,
                max_steps=settings.max_steps,
                checkpoint_interval_steps=settings.checkpoint_interval_steps,
                eval_interval_steps=settings.eval_interval_steps,
                durable_checkpoint_retention=settings.durable_checkpoint_retention,
                durable_checkpoint_min_free_bytes=settings.durable_checkpoint_min_free_bytes,
            ),
            command=["docker", "run", "-d"],
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.launch_detached_training",
        fake_launch_detached_training,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.write_json",
        lambda path, payload: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.launch_resource_monitor",
        lambda **kwargs: {"launch_id": kwargs["training_launch_id"]},
    )

    launch_root, launch = _resume_from_checkpoint(
        source_launch_root=output_root / "launch-a",
        source_run_root=source_run_root,
        settings=settings,
        repo_root=repo_root,
        dockerfile_path=dockerfile_path,
        output_root=output_root,
        resume_checkpoint_path=checkpoint_path,
        skip_build=True,
        build_performed=False,
        image_id="sha256:test",
        hf_mount=MountResolution(
            canonical_root=settings.hf_cache_dir,
            effective_root=settings.hf_cache_dir,
            used_home_mount=False,
        ),
        scratch_mount=MountResolution(
            canonical_root=settings.scratch_build_root,
            effective_root=settings.scratch_build_root,
            used_home_mount=False,
        ),
        disable_resource_monitor=True,
        resource_monitor_interval_seconds=1.0,
        resource_monitor_runtime_kind="rocm",
        resource_monitor_duration_seconds=None,
    )

    assert launch_root == output_root / "launch-b"
    assert launch.launch_id == "launch-b"
    assert captured["repo_root"] == repo_root
    assert captured["dockerfile_path"] == dockerfile_path
    assert captured["run_root"] == source_run_root
    assert captured["resume_from_checkpoint"] == checkpoint_path


def test_run_schedule_cycle_writes_failure_artifacts_when_segment_exits_early(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Schedule control should fail closed if the segment dies before its target boundary."""
    scratch_root = tmp_path / "srv/scratch/sir-convert-a-lot/build"
    repo_root = tmp_path / "recorded-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    launch_payload = _launch_payload(scratch_root=scratch_root, repo_root=repo_root)
    source_launch_root = Path(launch_payload.settings.output_root) / launch_payload.launch_id
    source_launch_root.mkdir(parents=True, exist_ok=True)
    (source_launch_root / "status.json").write_text(
        json.dumps({"dataloader_length": 100}) + "\n",
        encoding="utf-8",
    )
    run_root = Path(launch_payload.run_root)
    checkpoint_path = run_root / "checkpoints/state-step-00000040"
    _write_checkpoint_metadata(
        checkpoint_path,
        optimizer_steps_completed=40,
        epoch=0,
        next_epoch=0,
        next_step_in_epoch=20,
    )
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.default_schedule_id",
        lambda: "schedule-test",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.run_checked",
        lambda args, *, label: "rocm-smi-ok",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.prepare_qwen_image",
        lambda args: (False, "sha256:test"),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.resolve_effective_hf_cache_dir",
        lambda args: MountResolution(
            canonical_root=scratch_root / "cache/huggingface",
            effective_root=scratch_root / "cache/huggingface",
            used_home_mount=False,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.resolve_effective_bind_root",
        lambda canonical_root, home_mount, *, image, sync_home_into_canonical: MountResolution(
            canonical_root=canonical_root,
            effective_root=canonical_root,
            used_home_mount=False,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.inspect_detached_training",
        lambda launch: DetachedStatus(
            checked_at="2026-03-15T10:40:00Z",
            launch_id=launch.launch_id,
            container_name=launch.container_name,
            container_id=launch.container_id,
            status="running",
            running=True,
            exit_code=0,
            oom_killed=False,
            started_at="2026-03-15T10:00:00Z",
            finished_at="",
            pilot_status_found=True,
            pilot_status={"current_optimizer_step": 40, "status": "running"},
            pilot_report_found=False,
            pilot_report=None,
            latest_checkpoint_found=True,
            latest_checkpoint={"checkpoint_path": checkpoint_path.as_posix()},
            logs_tail="",
            resource_monitor=None,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner._monitor_to_target_and_stop",
        lambda *, launch, target_optimizer_step, poll_interval_seconds: (
            DetachedStatus(
                checked_at="2026-03-15T10:45:00Z",
                launch_id=launch.launch_id,
                container_name=launch.container_name,
                container_id=launch.container_id,
                status="exited",
                running=False,
                exit_code=1,
                oom_killed=False,
                started_at="2026-03-15T10:00:00Z",
                finished_at="2026-03-15T10:45:00Z",
                pilot_status_found=True,
                pilot_status={"current_optimizer_step": 44, "status": "failed"},
                pilot_report_found=False,
                pilot_report=None,
                latest_checkpoint_found=True,
                latest_checkpoint={"checkpoint_path": checkpoint_path.as_posix()},
                logs_tail="boom",
                resource_monitor=None,
            ),
            False,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.schedule_runner.run_standalone_eval",
        lambda *args, **kwargs: pytest.fail(
            "standalone eval should not run after an early failure"
        ),
    )

    with pytest.raises(SystemExit, match="before reaching the planned optimizer-step boundary"):
        run_schedule_cycle(
            source_launch_root=source_launch_root,
            source_launch=launch_payload,
            output_root=Path(launch_payload.settings.output_root),
            checkpoint_path=None,
            eval_jsonl=None,
            pilot_bundle_root=None,
            epochs_per_segment=1,
            poll_interval_seconds=0.0,
            skip_build=True,
            disable_resource_monitor=True,
            resource_monitor_interval_seconds=1.0,
            resource_monitor_runtime_kind="rocm",
            resource_monitor_duration_seconds=None,
        )

    schedule_output_root = Path(launch_payload.settings.output_root) / "schedules/schedule-test"
    failure_report_path = schedule_output_root / "report.json"
    failure_status_path = schedule_output_root / "status.json"
    failure_report = json.loads(failure_report_path.read_text(encoding="utf-8"))
    failure_status = json.loads(failure_status_path.read_text(encoding="utf-8"))

    assert failure_report["status"] == "failed"
    assert (
        "before reaching the planned optimizer-step boundary" in failure_report["failure"]["error"]
    )
    assert failure_status["status"] == "failed"
    assert failure_status["final_status"]["exit_code"] == 1


def test_schedule_command_rejects_eval_paths_outside_scratch_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public schedule CLI should fail early on eval paths outside the mounted scratch root."""
    scratch_root = tmp_path / "srv/scratch/sir-convert-a-lot/build"
    output_root = scratch_root / "verification/qwen-training"
    repo_root = tmp_path / "recorded-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    launch_payload = _launch_payload(scratch_root=scratch_root, repo_root=repo_root)
    launch_root = output_root / launch_payload.launch_id
    launch_root.mkdir(parents=True, exist_ok=True)
    (launch_root / "launch.json").write_text(
        json.dumps(asdict(launch_payload)) + "\n",
        encoding="utf-8",
    )
    (output_root / "latest-launch.json").write_text(
        json.dumps({"launch_root": launch_root.as_posix()}) + "\n",
        encoding="utf-8",
    )
    called = {"value": False}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_train.run_schedule_cycle",
        lambda **kwargs: called.__setitem__("value", True),
    )

    outside_eval_path = tmp_path / "outside-eval.jsonl"
    outside_eval_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="`eval_jsonl` must live under"):
        main(
            [
                "schedule",
                "--output-root",
                output_root.as_posix(),
                "--launch-root",
                launch_root.as_posix(),
                "--eval-jsonl",
                outside_eval_path.as_posix(),
            ]
        )

    assert called["value"] is False
