"""Focused tests for reusable diagnostic-state capture control-plane flow.

Purpose:
    Verify that the public `capture-diagnostic-state` surface mints a
    deterministic near-boundary checkpoint with automated step-threshold stop
    control rather than manual operator timing.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.cli.ml.qwen_train`.
    - Exercises `capture_diagnostic_state_use_case.py` with faked detached
      launch/runtime services.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.cli.ml.qwen_train import main
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane import build_parser
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_CAPTURE_DIAGNOSTIC_STATE_TARGET_OPTIMIZER_STEP,
    DEFAULT_DOCKERFILE_PATH,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    DetachedStatus,
    TrainingSettings,
    TrainingSettingsSnapshot,
)


def _settings(*, scratch_root: Path) -> TrainingSettings:
    """Build deterministic training settings for capture-use-case tests."""
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
        checkpoint_interval_steps=500,
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )


def _launch_payload(*, scratch_root: Path, repo_root: Path) -> DetachedLaunch:
    """Build one detached source launch payload for capture-use-case tests."""
    settings = _settings(scratch_root=scratch_root)
    run_root = settings.runs_root / "launch-a"
    return DetachedLaunch(
        generated_at="2026-03-16T09:00:00Z",
        launch_kind="training",
        launch_id="launch-a",
        container_name="qwen-train-launch-a",
        container_id="container-id",
        repo_root=repo_root.as_posix(),
        run_root=run_root.as_posix(),
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


def test_capture_diagnostic_state_parser_exposes_canonical_defaults() -> None:
    """The capture parser should default to the planned near-boundary step."""
    parser = build_parser()
    args = parser.parse_args(["capture-diagnostic-state"])

    assert args.target_optimizer_step == DEFAULT_CAPTURE_DIAGNOSTIC_STATE_TARGET_OPTIMIZER_STEP
    assert args.gradient_accumulation_steps is None
    assert args.checkpoint_interval_steps is None
    assert args.disable_resource_monitor is False
    assert args.skip_build is False


def test_capture_diagnostic_state_cli_mints_reusable_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The capture CLI should auto-stop at the target step and persist the artifact."""
    scratch_root = tmp_path / "srv/scratch/sir-convert-a-lot/build"
    output_root = scratch_root / "verification/qwen-training"
    repo_root = tmp_path / "recorded-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    launch_payload = _launch_payload(scratch_root=scratch_root, repo_root=repo_root)
    source_launch_root = output_root / launch_payload.launch_id
    source_run_root = Path(launch_payload.run_root)
    source_checkpoint_path = source_run_root / "checkpoints/state-step-00001238"
    source_checkpoint_path.mkdir(parents=True, exist_ok=True)
    Path(launch_payload.pilot_bundle_root).mkdir(parents=True, exist_ok=True)
    (source_run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": source_checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )
    source_launch_root.mkdir(parents=True, exist_ok=True)
    (source_launch_root / "launch.json").write_text(
        json.dumps(asdict(launch_payload)) + "\n",
        encoding="utf-8",
    )
    captured_settings: list[TrainingSettings] = []
    captured_extra_probe_args: list[str] = []

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.capture_diagnostic_state_use_case.prepare_runtime_dependencies",
        lambda *, settings, dockerfile_path, skip_build: (
            False,
            "sha256:test",
            MountResolution(
                canonical_root=scratch_root / "cache/huggingface",
                effective_root=scratch_root / "cache/huggingface",
                used_home_mount=False,
            ),
            MountResolution(
                canonical_root=scratch_root,
                effective_root=scratch_root,
                used_home_mount=False,
            ),
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.capture_diagnostic_state_use_case.ensure_training_bundle_exists",
        lambda bundle_root, *, train_manifest_family, eval_manifest_family: None,
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
        dockerfile_path: Path | None = None,
        run_root: Path | None = None,
        resume_from_checkpoint: Path | None = None,
        launch_kind: str = "training",
        trainer_module: str = "scripts.sir_convert_a_lot.ml.qwen.training.trainer",
        extra_probe_args: list[str] | None = None,
        diagnostic: dict[str, object] | None = None,
    ) -> DetachedLaunch:
        del hf_mount, scratch_mount, dockerfile_path, trainer_module
        assert run_root is not None
        captured_settings.append(settings)
        captured_extra_probe_args.extend([] if extra_probe_args is None else list(extra_probe_args))
        return DetachedLaunch(
            generated_at="2026-03-16T10:00:00Z",
            launch_kind=launch_kind,
            launch_id=launch_id,
            container_name=container_name,
            container_id="capture-container-id",
            repo_root=repo_root.as_posix(),
            run_root=run_root.as_posix(),
            pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
            train_jsonl=launch_payload.train_jsonl,
            eval_jsonl=launch_payload.eval_jsonl,
            train_manifest_family=settings.train_manifest_family,
            eval_manifest_family=settings.eval_manifest_family,
            dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
            resumed_from_checkpoint_path=(
                None if resume_from_checkpoint is None else resume_from_checkpoint.as_posix()
            ),
            settings=launch_payload.settings,
            command=["docker", "run", "-d"],
            diagnostic=diagnostic,
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.capture_diagnostic_state_use_case.launch_detached_training",
        fake_launch_detached_training,
    )

    status_sequence = iter(
        [
            DetachedStatus(
                checked_at="2026-03-16T10:00:00Z",
                launch_kind="capture-diagnostic-state",
                launch_id="capture-a",
                container_name="qwen-capture-capture-a",
                container_id="capture-container-id",
                status="running",
                running=True,
                exit_code=0,
                oom_killed=False,
                started_at="2026-03-16T10:00:00Z",
                finished_at="",
                pilot_status_found=True,
                pilot_status={"current_optimizer_step": 1399},
                pilot_report_found=False,
                pilot_report=None,
                latest_checkpoint_found=False,
                latest_checkpoint=None,
                logs_tail="",
                resource_monitor=None,
            ),
            DetachedStatus(
                checked_at="2026-03-16T10:03:00Z",
                launch_kind="capture-diagnostic-state",
                launch_id="capture-a",
                container_name="qwen-capture-capture-a",
                container_id="capture-container-id",
                status="exited",
                running=False,
                exit_code=0,
                oom_killed=False,
                started_at="2026-03-16T10:00:00Z",
                finished_at="2026-03-16T10:03:00Z",
                pilot_status_found=True,
                pilot_status={"current_optimizer_step": 1401, "status": "completed"},
                pilot_report_found=False,
                pilot_report=None,
                latest_checkpoint_found=True,
                latest_checkpoint={
                    "checkpoint_path": (
                        scratch_root
                        / "verification/qwen-training/capture-a"
                        / "diagnostic-state/checkpoints/state-step-00001401"
                    ).as_posix(),
                },
                logs_tail="",
                resource_monitor=None,
            ),
        ]
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.capture_diagnostic_state_use_case.inspect_detached_training",
        lambda launch: _status_with_capture_artifact(
            next(status_sequence),
            output_root / "capture-a/diagnostic_state_capture.json",
            checkpoint_path=(
                output_root / "capture-a/diagnostic-state/checkpoints/state-step-00001401"
            ),
            source_checkpoint_path=source_checkpoint_path,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.capture_diagnostic_state_use_case.sleep",
        lambda seconds: None,
    )

    def fake_load_latest_checkpoint(run_root: Path) -> Path:
        if run_root == source_run_root:
            return source_checkpoint_path
        checkpoint_path = run_root / "checkpoints/state-step-00001401"
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        return checkpoint_path

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.capture_diagnostic_state_use_case.load_latest_checkpoint",
        fake_load_latest_checkpoint,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.capture_diagnostic_state_use_case.write_json",
        lambda path, payload: (
            path.parent.mkdir(parents=True, exist_ok=True)
            or path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        ),
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    result = main(
        [
            "capture-diagnostic-state",
            "--output-root",
            output_root.as_posix(),
            "--launch-root",
            source_launch_root.as_posix(),
            "--launch-id",
            "capture-a",
            "--skip-build",
            "--disable-resource-monitor",
            "--poll-interval-seconds",
            "0.01",
        ]
    )

    assert result == 0
    settings = captured_settings[0]
    assert settings.max_steps == 1401
    assert settings.checkpoint_interval_steps == 1402
    assert settings.eval_interval_steps == 1402
    assert "--diagnostic-kind" in captured_extra_probe_args
    assert "capture-diagnostic-state" in captured_extra_probe_args
    assert "--diagnostic-target-optimizer-step" in captured_extra_probe_args
    assert "1401" in captured_extra_probe_args
    capture_payload = json.loads(
        (output_root / "capture-a/diagnostic_state_capture.json").read_text(encoding="utf-8")
    )
    assert capture_payload["target_optimizer_step"] == 1401
    assert capture_payload["captured_checkpoint_step"] == 1401
    assert capture_payload["source_checkpoint_path"] == source_checkpoint_path.as_posix()


def _status_with_capture_artifact(
    status: DetachedStatus,
    artifact_path: Path,
    *,
    checkpoint_path: Path,
    source_checkpoint_path: Path,
) -> DetachedStatus:
    """Persist one trainer-native capture artifact when the fake run exits."""
    if status.running:
        return status
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "kind": "capture-diagnostic-state",
                "source_launch_root": "/tmp/source-launch",
                "source_checkpoint_path": source_checkpoint_path.as_posix(),
                "target_optimizer_step": 1401,
                "launch_root": artifact_path.parent.as_posix(),
                "run_root": checkpoint_path.parent.parent.as_posix(),
                "captured_checkpoint_path": checkpoint_path.as_posix(),
                "captured_checkpoint_step": 1401,
                "final_status": {"status": status.status, "exit_code": status.exit_code},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return status
