"""Tests for standalone Qwen eval orchestration surfaces.

Purpose:
    Verify the new standalone eval command and host-side Docker command wiring
    without requiring a real GPU container run.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.cli.ml.qwen_train`.
    - Exercises `scripts.sir_convert_a_lot.ml.qwen.training.eval_orchestrator`.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.cli.ml.qwen_train import main
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_DOCKERFILE_PATH,
)
from scripts.sir_convert_a_lot.ml.qwen.training.eval_orchestrator import (
    build_standalone_eval_command,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    StandaloneEvalReport,
    TrainingSettings,
    TrainingSettingsSnapshot,
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
        checkpoint_interval_steps=500,
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
        text_embedding_mask_policy="text_span_only",
    )


def _launch_payload(*, scratch_root: Path, repo_root: Path) -> DetachedLaunch:
    """Build one detached launch payload for CLI tests."""
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


def test_build_standalone_eval_command_containerizes_checkpoint_and_eval_paths() -> None:
    """Standalone eval should run inside the governed image with scratch paths containerized."""
    scratch_root = Path("/srv/scratch/sir-convert-a-lot/build")
    settings = _settings(scratch_root=scratch_root)
    repo_root = Path("/home/paunchygent/apps/sir-convert-a-lot")
    hf_mount = MountResolution(
        canonical_root=settings.hf_cache_dir,
        effective_root=settings.hf_cache_home_mount,
        used_home_mount=True,
    )
    scratch_mount = MountResolution(
        canonical_root=settings.scratch_build_root,
        effective_root=settings.scratch_build_home_mount,
        used_home_mount=False,
    )
    output_dir = settings.runs_root / "launch-a/evals/eval-a"
    checkpoint_path = settings.runs_root / "launch-a/checkpoints/state-step-00000100"
    eval_jsonl = settings.pilot_bundle_root / "manifests/swedish_checkpoint_dev.prepared.jsonl"

    command = build_standalone_eval_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        output_dir=output_dir,
        checkpoint_path=checkpoint_path,
        eval_jsonl=eval_jsonl,
        pilot_bundle_root=settings.pilot_bundle_root,
    )

    assert command[:3] == ["run", "--rm", "--device"]
    assert "-v" in command
    assert f"{repo_root.as_posix()}:/app" in " ".join(command)
    assert f"{settings.scratch_build_root.as_posix()}:/app/build" in " ".join(command)
    assert "--checkpoint-path" in command
    assert "/app/build/runs/qwen/launch-a/checkpoints/state-step-00000100" in command
    assert "--eval-jsonl" in command
    assert (
        "/app/build/reference/qwen-bundle/manifests/swedish_checkpoint_dev.prepared.jsonl"
        in command
    )
    assert "--pilot-bundle-root" in command
    assert "/app/build/reference/qwen-bundle" in command
    assert "--gradient-accumulation-steps" in command
    assert "4" in command
    assert "--text-embedding-mask-policy" in command
    assert "text_span_only" in command


def test_eval_command_uses_recorded_launch_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public eval CLI should mount the repo recorded in the source launch metadata."""
    scratch_root = tmp_path / "srv/scratch/sir-convert-a-lot/build"
    output_root = scratch_root / "verification/qwen-training"
    repo_root = tmp_path / "recorded-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    launch_payload = _launch_payload(scratch_root=scratch_root, repo_root=repo_root)
    launch_root = output_root / launch_payload.launch_id
    run_root = Path(launch_payload.run_root)
    checkpoint_path = run_root / "checkpoints/state-step-00000100"
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    (run_root / "latest_checkpoint.json").parent.mkdir(parents=True, exist_ok=True)
    (run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )
    eval_jsonl_path = Path(launch_payload.eval_jsonl)
    eval_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    eval_jsonl_path.write_text("{}\n", encoding="utf-8")
    bundle_root = Path(launch_payload.pilot_bundle_root)
    bundle_root.mkdir(parents=True, exist_ok=True)
    launch_root.mkdir(parents=True, exist_ok=True)
    (launch_root / "launch.json").write_text(
        json.dumps(asdict(launch_payload)) + "\n",
        encoding="utf-8",
    )
    (output_root / "latest-launch.json").write_text(
        json.dumps({"launch_root": launch_root.as_posix()}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.eval_use_case.prepare_runtime_dependencies",
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
    printed: dict[str, object] = {}

    def fake_run_standalone_eval(
        settings: TrainingSettings,
        *,
        repo_root: Path,
        hf_mount: MountResolution,
        scratch_mount: MountResolution,
        output_dir: Path,
        checkpoint_path: Path,
        eval_jsonl: Path,
        pilot_bundle_root: Path | None,
    ) -> StandaloneEvalReport:
        del hf_mount, scratch_mount
        printed["repo_root"] = repo_root
        printed["output_dir"] = output_dir
        printed["checkpoint_path"] = checkpoint_path
        printed["eval_jsonl"] = eval_jsonl
        printed["pilot_bundle_root"] = pilot_bundle_root
        return StandaloneEvalReport(
            generated_at="2026-03-15T10:10:00Z",
            status="completed",
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            checkpoint_path=checkpoint_path.as_posix(),
            eval_jsonl=eval_jsonl.as_posix(),
            output_dir=output_dir.as_posix(),
            eval_row_count=1,
            gradient_accumulation_steps=settings.gradient_accumulation_steps,
            text_embedding_mask_policy=settings.text_embedding_mask_policy,
            bundle_precomputed_reference_input=None,
            throughput_profile=None,
            eval_summary={"eval_loss": 1.25},
            failure=None,
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.eval_use_case.run_standalone_eval",
        fake_run_standalone_eval,
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    result = main(
        [
            "eval",
            "--output-root",
            output_root.as_posix(),
            "--launch-root",
            launch_root.as_posix(),
            "--skip-build",
        ]
    )

    assert result == 0
    assert printed["repo_root"] == repo_root
    assert printed["checkpoint_path"] == checkpoint_path.resolve()
    assert printed["eval_jsonl"] == eval_jsonl_path.resolve()
    assert printed["pilot_bundle_root"] == bundle_root.resolve()
