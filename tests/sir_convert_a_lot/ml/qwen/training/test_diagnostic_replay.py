"""Focused tests for detached Qwen non-finite diagnostic replay.

Purpose:
    Verify the public `diagnose-non-finite` surface, the detached launch
    contract, and the machine-readable replay artifacts used for bounded root-
    cause investigation.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.cli.ml.qwen_train`.
    - Exercises `trainer.py` replay-bundle persistence on optimizer-boundary
      failures without requiring a live GPU run.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import ModuleType

import pytest

from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard import (
    OptimizerBoundaryCorruptionError,
)
from scripts.sir_convert_a_lot.cli.ml.qwen_train import main
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane import build_parser
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP,
    DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP,
    DEFAULT_DOCKERFILE_PATH,
)
from scripts.sir_convert_a_lot.ml.qwen.training.diagnostic_artifacts import (
    build_diagnostic_replay_bundle,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    TrainingSettings,
    TrainingSettingsSnapshot,
)


class _FakeSft12HzModule(ModuleType):
    """Provide the minimal top-level trainer dependency needed for import."""

    def train_with_args(self, *args: object, **kwargs: object) -> None:
        """Accept train entry calls without running the real training loop."""


_fake_sft_12hz = _FakeSft12HzModule("sft_12hz")
sys.modules.setdefault("sft_12hz", _fake_sft_12hz)
trainer = importlib.import_module("scripts.sir_convert_a_lot.ml.qwen.training.trainer")


def _settings(*, scratch_root: Path) -> TrainingSettings:
    """Build one deterministic settings fixture for detached replay tests."""
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
    """Build one detached training launch payload for replay CLI tests."""
    settings = _settings(scratch_root=scratch_root)
    run_root = settings.runs_root / "launch-a"
    return DetachedLaunch(
        generated_at="2026-03-15T10:00:00Z",
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


def _trainer_args(
    *,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
) -> argparse.Namespace:
    """Return one deterministic trainer arg namespace with diagnostic mode enabled."""
    return argparse.Namespace(
        launch_id="diagnose-launch",
        launch_metadata_path=None,
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_jsonl=train_jsonl,
        eval_jsonl=eval_jsonl,
        pilot_bundle_root=None,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        output_dir=output_dir,
        tracker_project_name="qwen-training",
        mlflow_experiment_name="qwen-training",
        mlflow_tracking_uri=None,
        mlflow_artifact_root=None,
        tensorboard_logging_dir=None,
        tracker_run_name=None,
        batch_size=8,
        throughput_profile_label="hemma-throughput-balanced-v1",
        lr=2e-5,
        num_epochs=1,
        max_steps=1406,
        checkpoint_interval_steps=500,
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        dataloader_persistent_workers=True,
        dataloader_prefetch_factor=4,
        non_blocking_transfer=True,
        data_path_proof_mode=False,
        heartbeat_interval_optimizer_steps=20,
        finite_loss_max_consecutive_steps=3,
        ref_mel_cache_enabled=True,
        ref_mel_cache_max_items=2048,
        torch_profiler_enabled=False,
        torch_profiler_wait_steps=1,
        torch_profiler_warmup_steps=1,
        torch_profiler_active_steps=4,
        torch_profiler_repeat=1,
        torch_profiler_record_shapes=True,
        torch_profiler_profile_memory=True,
        torch_profiler_with_stack=False,
        torch_profiler_trace_dir=None,
        resume_from_checkpoint=None,
        diagnostic_kind="diagnose-non-finite",
        diagnostic_source_launch_root=Path("/srv/scratch/source-launch"),
        diagnostic_source_checkpoint_path=Path("/srv/scratch/run/checkpoints/state-step-00001238"),
        diagnostic_start_optimizer_step=1405,
        diagnostic_end_optimizer_step=1406,
    )


def test_parser_diagnose_non_finite_defaults() -> None:
    """The public replay parser should expose the bounded diagnostic defaults."""
    parser = build_parser()
    args = parser.parse_args(["diagnose-non-finite"])

    assert args.start_optimizer_step == DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP
    assert args.end_optimizer_step == DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP
    assert args.disable_resource_monitor is False
    assert args.skip_build is False


def test_build_diagnostic_replay_bundle_preserves_failure_and_status_payloads() -> None:
    """Replay bundles should preserve the diagnostic metadata and failure payload."""
    bundle = build_diagnostic_replay_bundle(
        diagnostic={
            "kind": "diagnose-non-finite",
            "start_optimizer_step": 1405,
            "end_optimizer_step": 1406,
        },
        report={
            "status": "failed",
            "failure": {
                "optimizer_boundary_guard": {
                    "trigger_reason": "post_step_non_finite_parameters",
                }
            },
        },
        status={
            "status": "failed",
            "current_phase": "failed",
        },
    )

    diagnostic_payload = bundle["diagnostic"]
    failure_payload = bundle["failure"]
    status_payload = bundle["status"]
    assert isinstance(diagnostic_payload, dict)
    assert isinstance(failure_payload, dict)
    assert isinstance(status_payload, dict)
    optimizer_boundary_guard = failure_payload["optimizer_boundary_guard"]
    assert isinstance(optimizer_boundary_guard, dict)
    assert diagnostic_payload["kind"] == "diagnose-non-finite"
    assert optimizer_boundary_guard["trigger_reason"] == ("post_step_non_finite_parameters")
    assert status_payload["current_phase"] == "failed"


def test_diagnose_non_finite_cli_launches_detached_replay_without_latest_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public replay CLI should launch detached diagnosis without mutating latest pointer."""
    scratch_root = tmp_path / "srv/scratch/sir-convert-a-lot/build"
    output_root = scratch_root / "verification/qwen-training"
    repo_root = tmp_path / "recorded-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    launch_payload = _launch_payload(scratch_root=scratch_root, repo_root=repo_root)
    source_launch_root = output_root / launch_payload.launch_id
    run_root = Path(launch_payload.run_root)
    checkpoint_path = run_root / "checkpoints/state-step-00001238"
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    Path(launch_payload.pilot_bundle_root).mkdir(parents=True, exist_ok=True)
    (run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )
    source_launch_root.mkdir(parents=True, exist_ok=True)
    (source_launch_root / "launch.json").write_text(
        json.dumps(asdict(launch_payload)) + "\n",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.diagnose_use_case.prepare_runtime_dependencies",
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
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.diagnose_use_case.ensure_training_bundle_exists",
        lambda bundle_root, *, train_manifest_family, eval_manifest_family: None,
    )

    def fake_launch_detached_non_finite_diagnosis(
        settings: TrainingSettings,
        *,
        repo_root: Path,
        hf_mount: MountResolution,
        scratch_mount: MountResolution,
        launch_id: str,
        launch_root: Path,
        container_name: str,
        source_launch_root: Path,
        checkpoint_path: Path,
        start_optimizer_step: int,
        end_optimizer_step: int,
        dockerfile_path: Path | None = None,
    ) -> DetachedLaunch:
        del hf_mount, scratch_mount, dockerfile_path
        captured["repo_root"] = repo_root
        captured["settings"] = settings
        captured["launch_id"] = launch_id
        captured["launch_root"] = launch_root
        captured["container_name"] = container_name
        captured["source_launch_root"] = source_launch_root
        captured["checkpoint_path"] = checkpoint_path
        captured["start_optimizer_step"] = start_optimizer_step
        captured["end_optimizer_step"] = end_optimizer_step
        return DetachedLaunch(
            generated_at="2026-03-15T11:00:00Z",
            launch_kind="diagnose-non-finite",
            launch_id=launch_id,
            container_name=container_name,
            container_id="container-id",
            repo_root=repo_root.as_posix(),
            run_root=(launch_root / "diagnostic-run").as_posix(),
            pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
            train_jsonl=launch_payload.train_jsonl,
            eval_jsonl=launch_payload.eval_jsonl,
            train_manifest_family=settings.train_manifest_family,
            eval_manifest_family=settings.eval_manifest_family,
            dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
            resumed_from_checkpoint_path=checkpoint_path.as_posix(),
            settings=launch_payload.settings,
            command=["docker", "run", "-d"],
            diagnostic={
                "kind": "diagnose-non-finite",
                "source_launch_root": source_launch_root.as_posix(),
                "source_checkpoint_path": checkpoint_path.as_posix(),
                "start_optimizer_step": start_optimizer_step,
                "end_optimizer_step": end_optimizer_step,
            },
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.diagnose_use_case.launch_detached_non_finite_diagnosis",
        fake_launch_detached_non_finite_diagnosis,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.diagnose_use_case.write_json",
        lambda path, payload: captured.setdefault("launch_payload", payload),
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    result = main(
        [
            "diagnose-non-finite",
            "--output-root",
            output_root.as_posix(),
            "--launch-root",
            source_launch_root.as_posix(),
            "--skip-build",
            "--disable-resource-monitor",
        ]
    )

    assert result == 0
    assert captured["repo_root"] == repo_root
    assert captured["source_launch_root"] == source_launch_root
    assert captured["checkpoint_path"] == checkpoint_path
    assert captured["start_optimizer_step"] == DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP
    assert captured["end_optimizer_step"] == DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP
    launch_metadata_payload = captured["launch_payload"]
    assert isinstance(launch_metadata_payload, dict)
    diagnostic_payload = launch_metadata_payload["diagnostic"]
    assert isinstance(diagnostic_payload, dict)
    assert launch_metadata_payload["launch_kind"] == "diagnose-non-finite"
    assert diagnostic_payload["kind"] == "diagnose-non-finite"


def test_trainer_persists_optimizer_boundary_failure_and_replay_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diagnostic trainer failures should agree across status, report, and replay bundle."""
    train_jsonl = tmp_path / "manifests/train.jsonl"
    eval_jsonl = tmp_path / "manifests/eval.jsonl"
    output_dir = tmp_path / "run"
    train_jsonl.parent.mkdir(parents=True, exist_ok=True)
    train_jsonl.write_text("{}\n", encoding="utf-8")
    eval_jsonl.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        trainer,
        "_parse_args",
        lambda: _trainer_args(
            train_jsonl=train_jsonl,
            eval_jsonl=eval_jsonl,
            output_dir=output_dir,
        ),
    )
    monkeypatch.setattr(trainer.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(trainer.torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(trainer.torch.version, "hip", "6.4.0")
    monkeypatch.setattr(
        trainer.sft_12hz,
        "train_with_args",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OptimizerBoundaryCorruptionError(
                trigger_reason="post_step_non_finite_parameters",
                optimizer_step=1406,
                current_epoch=5,
                current_train_iteration=808,
                loss_value=1.0,
                main_loss_value=0.8,
                sub_talker_loss_value=0.2,
                grad_norm_value=1.0,
                optimizer_step_attempted=True,
                optimizer_step_completed=True,
                targeted_parameter_names=[
                    "text_embedding.embedding.weight",
                    "text_projection.weight",
                ],
                first_non_finite_surface="text_embedding.embedding.weight",
                pre_step_parameter_probes={
                    "probe_kind": "parameters",
                    "first_non_finite_surface": None,
                    "probes": {},
                },
                pre_step_gradient_probes={
                    "probe_kind": "gradients",
                    "first_non_finite_surface": None,
                    "probes": {},
                },
                pre_step_optimizer_state_probes={
                    "first_non_finite_surface": None,
                    "probes": {},
                },
                post_step_parameter_probes={
                    "probe_kind": "parameters",
                    "first_non_finite_surface": "text_embedding.embedding.weight",
                    "probes": {},
                },
                post_step_optimizer_state_probes={
                    "first_non_finite_surface": None,
                    "probes": {},
                },
                step_forensics={
                    "optimizer_step": 1406,
                    "first_non_finite_tensor": "input_text_embedding",
                },
            )
        ),
    )

    with pytest.raises(OptimizerBoundaryCorruptionError):
        trainer.main()

    status_payload = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
    report_payload = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    replay_bundle_payload = json.loads(
        (output_dir / "diagnostic_replay_bundle.json").read_text(encoding="utf-8")
    )

    assert status_payload["status"] == "failed"
    assert status_payload["diagnostic"]["kind"] == "diagnose-non-finite"
    assert status_payload["optimizer_boundary_guard"]["trigger_reason"] == (
        "post_step_non_finite_parameters"
    )
    assert report_payload["failure"]["optimizer_boundary_guard"]["optimizer_step"] == 1406
    assert report_payload["diagnostic"]["kind"] == "diagnose-non-finite"
    assert replay_bundle_payload["diagnostic"]["kind"] == "diagnose-non-finite"
    assert replay_bundle_payload["failure"]["optimizer_boundary_guard"][
        "first_non_finite_surface"
    ] == ("text_embedding.embedding.weight")
