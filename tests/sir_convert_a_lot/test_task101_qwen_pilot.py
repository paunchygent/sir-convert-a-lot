"""Tests for the detached Task 101 Qwen pilot lane."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_LR,
    DEFAULT_MAX_STEPS,
    DEFAULT_MODEL_ID,
    DEFAULT_NUM_EPOCHS,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    _build_parser,
    _ensure_pilot_bundle_exists,
    _load_latest_checkpoint,
    _resolve_launch_root,
    _validate_resume_checkpoint_path,
    main,
)
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import MountResolution
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime import (
    Task101DetachedLaunch,
    Task101DetachedStop,
    Task101PilotSettings,
    Task101PilotSettingsSnapshot,
    build_detached_pilot_command,
    inspect_detached_pilot,
    stop_detached_pilot,
)


def test_task101_parser_launch_defaults() -> None:
    """The Task 101 runner should expose deterministic bounded pilot defaults."""
    parser = _build_parser()
    args = parser.parse_args(["launch"])

    assert args.model_id == DEFAULT_MODEL_ID
    assert args.train_manifest_family == DEFAULT_TRAIN_MANIFEST_FAMILY
    assert args.eval_manifest_family == DEFAULT_EVAL_MANIFEST_FAMILY
    assert args.batch_size == DEFAULT_BATCH_SIZE
    assert args.lr == DEFAULT_LR
    assert args.num_epochs == DEFAULT_NUM_EPOCHS
    assert args.max_steps == DEFAULT_MAX_STEPS
    assert args.checkpoint_interval_steps == DEFAULT_CHECKPOINT_INTERVAL_STEPS
    assert args.skip_build is False


def test_task101_status_defaults_to_latest_pointer() -> None:
    """The Task 101 status command should default to the latest launch pointer."""
    parser = _build_parser()
    args = parser.parse_args(["status"])

    assert args.launch_root is None


def test_task101_resume_defaults_to_latest_checkpoint() -> None:
    """The Task 101 resume command should default to latest-checkpoint recovery."""
    parser = _build_parser()
    args = parser.parse_args(["resume"])

    assert args.resume_mode == "latest"
    assert args.checkpoint_path is None
    assert args.launch_root is None
    assert args.skip_build is False


def test_task101_stop_defaults_to_latest_launch_pointer() -> None:
    """Stop should target the latest detached launch when no launch root is provided."""
    parser = _build_parser()
    args = parser.parse_args(["stop"])

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
        pilot_bundle_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle"
        ),
        runs_root=Path("/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune"),
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        batch_size=1,
        lr=2e-5,
        num_epochs=1,
        max_steps=8,
        checkpoint_interval_steps=2,
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
    assert (
        "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface:/cache/huggingface" in command
    )
    assert "/home/paunchygent/.data/sir-convert-a-lot/build:/app/build" in command
    assert (
        "/app/build/reference/qwen3-tts-swedish-task101-pilot-bundle/manifests/"
        "swedish_pilot_train.prepared.jsonl" in command
    )
    assert (
        "/app/build/reference/qwen3-tts-swedish-task101-pilot-bundle/manifests/"
        "swedish_checkpoint_dev.prepared.jsonl" in command
    )
    assert "--checkpoint-interval-steps" in command
    checkpoint_index = command.index("--checkpoint-interval-steps")
    assert command[checkpoint_index + 1] == "2"
    eval_index = command.index("--eval-jsonl")
    assert command[eval_index + 1].endswith("/swedish_checkpoint_dev.prepared.jsonl")


def test_build_detached_pilot_command_includes_resume_checkpoint_when_requested() -> None:
    """The detached pilot command should surface the selected resume checkpoint."""
    settings = Task101PilotSettings(
        output_root=Path("/srv/scratch/sir-convert-a-lot/build/verification/task-101"),
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        scratch_build_root=Path("/srv/scratch/sir-convert-a-lot/build"),
        scratch_build_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/build"),
        pilot_bundle_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle"
        ),
        runs_root=Path("/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune"),
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        batch_size=1,
        lr=2e-5,
        num_epochs=1,
        max_steps=8,
        checkpoint_interval_steps=2,
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
        run_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-prev"
        ),
        resume_from_checkpoint=Path(
            "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/"
            "task101-prev/checkpoints/state-step-00000002"
        ),
    )

    assert run_root.as_posix().endswith("/task101-prev")
    assert "--resume-from-checkpoint" in command
    resume_index = command.index("--resume-from-checkpoint")
    assert command[resume_index + 1].endswith("/checkpoints/state-step-00000002")


def test_inspect_detached_pilot_reads_container_status_and_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The detached Task 101 status view should combine Docker and pilot outputs."""
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "optimizer_steps_completed": 8,
                "eval_jsonl": "/bundle/manifests/swedish_checkpoint_dev.prepared.jsonl",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "report.json").write_text(
        json.dumps(
            {
                "eval_jsonl": "/bundle/manifests/swedish_checkpoint_dev.prepared.jsonl",
                "upstream_trainer_uses_eval_manifest": False,
                "training_summary": {"optimizer_steps_completed": 8},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    launch = Task101DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="task101-20260309t120000z",
        container_name="task101-20260309t120000z-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=run_root.as_posix(),
        pilot_bundle_root=(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle"
        ),
        train_jsonl=(
            "/srv/scratch/sir-convert-a-lot/build/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle/manifests/"
            "swedish_pilot_train.prepared.jsonl"
        ),
        eval_jsonl=(
            "/srv/scratch/sir-convert-a-lot/build/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle/manifests/"
            "swedish_checkpoint_dev.prepared.jsonl"
        ),
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
        resumed_from_checkpoint_path=None,
        settings=Task101PilotSettingsSnapshot(
            output_root="/srv/scratch/sir-convert-a-lot/build/verification/task-101",
            image="sir-convert-a-lot-qwen-finetune-hemma:task100",
            hf_cache_dir="/srv/scratch/sir-convert-a-lot/cache/huggingface",
            hf_cache_home_mount="/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
            scratch_build_root="/srv/scratch/sir-convert-a-lot/build",
            scratch_build_home_mount="/home/paunchygent/.data/sir-convert-a-lot/build",
            pilot_bundle_root=(
                "/srv/scratch/sir-convert-a-lot/build/reference/"
                "qwen3-tts-swedish-task101-pilot-bundle"
            ),
            runs_root="/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune",
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            batch_size=1,
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=2,
        ),
        command=["sudo", "-n", "docker", "run", "-d"],
    )
    (run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": (run_root / "checkpoints/state-step-00000008").as_posix()})
        + "\n",
        encoding="utf-8",
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
    assert status.latest_checkpoint_found is True
    assert status.pilot_status is not None
    eval_jsonl = status.pilot_status["eval_jsonl"]
    assert isinstance(eval_jsonl, str)
    assert eval_jsonl.endswith("swedish_checkpoint_dev.prepared.jsonl")
    assert status.pilot_report is not None
    assert status.pilot_report["upstream_trainer_uses_eval_manifest"] is False
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


def test_task101_requires_pilot_bundle_artifacts_before_launch(tmp_path: Path) -> None:
    """Launch should fail fast when the deterministic pilot bundle is incomplete."""
    pilot_bundle_root = tmp_path / "pilot-bundle"
    pilot_bundle_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SystemExit, match="required pilot-bundle artifacts"):
        _ensure_pilot_bundle_exists(
            pilot_bundle_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
        )


def test_task101_requires_bundle_local_audio_and_ref_paths_before_launch(tmp_path: Path) -> None:
    """Launch should fail fast when prepared manifests reference missing bundle assets."""
    pilot_bundle_root = tmp_path / "pilot-bundle"
    manifests_dir = pilot_bundle_root / "manifests"
    reports_dir = pilot_bundle_root / "reports"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "task101_pilot_bundle_report.json").write_text("{}\n", encoding="utf-8")
    prepared_row = {
        "audio": "audio_24k/rixvox/train/speaker-a/train.wav",
        "text": "hej",
        "ref_audio": "refs/swedish_pilot_train/speaker-a/ref.wav",
        "speaker_id": "speaker-a",
        "dataset": "rixvox",
        "source_split": "train",
        "quality_tier": "high_trust",
        "audio_codes": [[1, 2]],
    }
    (manifests_dir / "swedish_pilot_train.prepared.jsonl").write_text(
        json.dumps(prepared_row) + "\n",
        encoding="utf-8",
    )
    (manifests_dir / "swedish_checkpoint_dev.prepared.jsonl").write_text(
        json.dumps(
            {
                **prepared_row,
                "audio": "audio_24k/rixvox/dev/speaker-a/dev.wav",
                "ref_audio": "refs/swedish_checkpoint_dev/speaker-a/ref.wav",
                "source_split": "dev",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="bundle integrity check failed"):
        _ensure_pilot_bundle_exists(
            pilot_bundle_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
        )


def test_task101_load_latest_checkpoint_pointer(tmp_path: Path) -> None:
    """Resume latest should resolve the run-root latest-checkpoint pointer."""
    run_root = tmp_path / "run"
    checkpoint_path = run_root / "checkpoints/state-step-00000008"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )

    assert _load_latest_checkpoint(run_root) == checkpoint_path


def test_task101_validate_resume_checkpoint_path_rejects_cross_run_mismatch(
    tmp_path: Path,
) -> None:
    """Explicit resume checkpoints must belong to the selected source run root."""
    source_run_root = tmp_path / "run-a"
    other_run_checkpoint = tmp_path / "run-b/checkpoints/state-step-00000008"
    source_run_root.mkdir(parents=True, exist_ok=True)
    other_run_checkpoint.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SystemExit, match="must belong to the selected source launch run root"):
        _validate_resume_checkpoint_path(source_run_root, other_run_checkpoint)


def test_task101_resume_reuses_dockerfile_path_from_launch_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should reuse the original launch dockerfile path instead of the default."""
    output_root = tmp_path / "verification"
    source_launch_root = output_root / "task101-prev"
    source_run_root = tmp_path / "runs/task101-prev"
    checkpoint_path = source_run_root / "checkpoints/state-step-00000008"
    output_root.mkdir(parents=True, exist_ok=True)
    source_launch_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    latest_pointer = source_run_root / "latest_checkpoint.json"
    latest_pointer.parent.mkdir(parents=True, exist_ok=True)
    latest_pointer.write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )

    launch_payload = Task101DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="task101-prev",
        container_name="task101-prev-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=source_run_root.as_posix(),
        pilot_bundle_root=(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle"
        ),
        train_jsonl=(
            "/srv/scratch/sir-convert-a-lot/build/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle/manifests/"
            "swedish_pilot_train.prepared.jsonl"
        ),
        eval_jsonl=(
            "/srv/scratch/sir-convert-a-lot/build/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle/manifests/"
            "swedish_checkpoint_dev.prepared.jsonl"
        ),
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path="containers/custom-qwen-finetune/Dockerfile",
        resumed_from_checkpoint_path=None,
        settings=Task101PilotSettingsSnapshot(
            output_root="/srv/scratch/sir-convert-a-lot/build/verification/task-101",
            image="sir-convert-a-lot-qwen-finetune-hemma:task100",
            hf_cache_dir="/srv/scratch/sir-convert-a-lot/cache/huggingface",
            hf_cache_home_mount="/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
            scratch_build_root="/srv/scratch/sir-convert-a-lot/build",
            scratch_build_home_mount="/home/paunchygent/.data/sir-convert-a-lot/build",
            pilot_bundle_root=(
                "/srv/scratch/sir-convert-a-lot/build/reference/"
                "qwen3-tts-swedish-task101-pilot-bundle"
            ),
            runs_root="/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune",
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            batch_size=1,
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=2,
        ),
        command=["sudo", "-n", "docker", "run", "-d"],
    )
    (source_launch_root / "launch.json").write_text(
        json.dumps(asdict(launch_payload)) + "\n",
        encoding="utf-8",
    )
    (output_root / "latest-launch.json").write_text(
        json.dumps({"launch_root": source_launch_root.as_posix()}) + "\n",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def _fake_prepare_qwen_image(args: argparse.Namespace) -> tuple[bool, str]:
        captured["dockerfile_path"] = args.dockerfile_path
        captured["image"] = args.image
        return False, "sha256:test"

    def _fake_resolve_hf_cache_dir(args: argparse.Namespace) -> MountResolution:
        del args
        return MountResolution(
            canonical_root=Path("/srv/scratch/cache"),
            effective_root=Path("/srv/scratch/cache"),
            used_home_mount=False,
        )

    def _fake_resolve_bind_root(
        canonical_root: Path,
        home_mount: Path,
        *,
        image: str,
        sync_home_into_canonical: bool,
    ) -> MountResolution:
        del home_mount, image, sync_home_into_canonical
        return MountResolution(
            canonical_root=canonical_root,
            effective_root=canonical_root,
            used_home_mount=False,
        )

    def _fake_launch_detached_pilot(
        settings: Task101PilotSettings,
        *,
        repo_root: Path,
        hf_mount: MountResolution,
        scratch_mount: MountResolution,
        launch_id: str,
        container_name: str,
        dockerfile_path: Path | None = None,
        run_root: Path | None = None,
        resume_from_checkpoint: Path | None = None,
    ) -> Task101DetachedLaunch:
        del settings, repo_root, hf_mount, scratch_mount, container_name
        captured["launch_id"] = launch_id
        captured["resume_dockerfile_path"] = dockerfile_path
        captured["run_root"] = run_root
        captured["resume_from_checkpoint"] = resume_from_checkpoint
        return launch_payload

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot.prepare_qwen_image",
        _fake_prepare_qwen_image,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot.resolve_effective_hf_cache_dir",
        _fake_resolve_hf_cache_dir,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot.resolve_effective_bind_root",
        _fake_resolve_bind_root,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot.launch_detached_pilot",
        _fake_launch_detached_pilot,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot._write_json",
        lambda path, payload: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task101_hemma_qwen_pilot._write_latest_pointer",
        lambda output_root, launch_root: None,
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    result = main(["resume", "--output-root", output_root.as_posix(), "--skip-build"])

    assert result == 0
    assert captured["dockerfile_path"] == Path("containers/custom-qwen-finetune/Dockerfile")
    assert captured["resume_dockerfile_path"] == Path("containers/custom-qwen-finetune/Dockerfile")
    assert captured["run_root"] == source_run_root
    assert captured["resume_from_checkpoint"] == checkpoint_path


def test_stop_detached_pilot_calls_docker_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stopping a detached pilot should issue one deterministic docker stop."""
    launch = Task101DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="task101-prev",
        container_name="task101-prev-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root="/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/task101-prev",
        pilot_bundle_root=(
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle"
        ),
        train_jsonl=(
            "/srv/scratch/sir-convert-a-lot/build/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle/manifests/"
            "swedish_pilot_train.prepared.jsonl"
        ),
        eval_jsonl=(
            "/srv/scratch/sir-convert-a-lot/build/reference/"
            "qwen3-tts-swedish-task101-pilot-bundle/manifests/"
            "swedish_checkpoint_dev.prepared.jsonl"
        ),
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
        resumed_from_checkpoint_path=None,
        settings=Task101PilotSettingsSnapshot(
            output_root="/srv/scratch/sir-convert-a-lot/build/verification/task-101",
            image="sir-convert-a-lot-qwen-finetune-hemma:task100",
            hf_cache_dir="/srv/scratch/sir_convert_a_lot/cache/huggingface",
            hf_cache_home_mount="/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
            scratch_build_root="/srv/scratch/sir_convert_a_lot/build",
            scratch_build_home_mount="/home/paunchygent/.data/sir-convert-a-lot/build",
            pilot_bundle_root=(
                "/srv/scratch/sir-convert-a-lot/build/reference/"
                "qwen3-tts-swedish-task101-pilot-bundle"
            ),
            runs_root="/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune",
            model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            batch_size=1,
            lr=2e-5,
            num_epochs=1,
            max_steps=8,
            checkpoint_interval_steps=2,
        ),
        command=["sudo", "-n", "docker", "run", "-d"],
    )
    captured: dict[str, object] = {}

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        captured["args"] = args
        captured["label"] = label
        return "task101-prev-container"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime.docker_checked",
        _fake_docker_checked,
    )

    stopped = stop_detached_pilot(launch)

    assert isinstance(stopped, Task101DetachedStop)
    assert captured["args"] == ["stop", "--time", "300", "task101-prev-container"]
    assert captured["label"] == "docker stop task101 detached pilot"
    assert stopped.container_name == "task101-prev-container"
