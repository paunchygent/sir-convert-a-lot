"""Tests for canonical detached Qwen training orchestration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.cli.ml.qwen_train import (
    DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_LR,
    DEFAULT_MAX_STEPS,
    DEFAULT_MODEL_ID,
    DEFAULT_NUM_EPOCHS,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    build_parser,
    ensure_training_bundle_exists,
    main,
)
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    load_latest_checkpoint,
    resolve_launch_root,
    validate_resume_checkpoint_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    DetachedStop,
    TrainingSettings,
    TrainingSettingsSnapshot,
)
from scripts.sir_convert_a_lot.ml.qwen.training.orchestrator import (
    build_detached_training_command,
    inspect_detached_training,
    stop_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
)


def test_parser_launch_defaults() -> None:
    """The training runner should expose deterministic bounded defaults."""
    parser = build_parser()
    args = parser.parse_args(["launch"])

    assert args.model_id == DEFAULT_MODEL_ID
    assert args.train_manifest_family == DEFAULT_TRAIN_MANIFEST_FAMILY
    assert args.eval_manifest_family == DEFAULT_EVAL_MANIFEST_FAMILY
    assert args.lr == DEFAULT_LR
    assert args.num_epochs == DEFAULT_NUM_EPOCHS
    assert args.max_steps == DEFAULT_MAX_STEPS
    assert args.batch_size == 8
    assert args.throughput_profile_label == DEFAULT_THROUGHPUT_PROFILE_LABEL
    assert args.checkpoint_interval_steps == DEFAULT_CHECKPOINT_INTERVAL_STEPS
    assert args.durable_checkpoint_retention == DEFAULT_DURABLE_CHECKPOINT_RETENTION
    assert args.durable_checkpoint_min_free_bytes == DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES
    assert args.dataloader_pin_memory is True
    assert args.dataloader_persistent_workers is True
    assert args.non_blocking_transfer is True
    assert args.ref_mel_cache_enabled is True
    assert args.torch_profiler_enabled is False
    assert args.rocm_profiler_enabled is False
    assert args.resource_monitor_interval_seconds == 1.0
    assert args.resource_monitor_runtime_kind == "rocm"
    assert args.disable_resource_monitor is False
    assert args.skip_build is False


def test_build_detached_training_command_uses_rocm_mounts_and_prepared_manifest() -> None:
    """The detached training command should target prepared bundle manifests."""
    settings = TrainingSettings(
        output_root=Path("/srv/scratch/sir-convert-a-lot/build/verification/qwen-training"),
        image="sir-convert-a-lot-qwen-finetune-hemma:latest",
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
        batch_size=8,
        throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        lr=2e-5,
        num_epochs=1,
        max_steps=8,
        checkpoint_interval_steps=2,
        durable_checkpoint_retention=2,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
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

    command, run_root = build_detached_training_command(
        settings,
        repo_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
        hf_mount=hf_mount,
        scratch_mount=scratch_mount,
        launch_id="qwen-20260309t120000z",
        container_name="qwen-20260309t120000z-container",
        launch_root=Path(
            "/srv/scratch/sir-convert-a-lot/build/verification/qwen-training/qwen-20260309t120000z"
        ),
    )

    assert run_root.as_posix().endswith("/qwen-20260309t120000z")
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
    assert "--dataloader-pin-memory" in command
    assert "--dataloader-persistent-workers" in command
    assert "--non-blocking-transfer" in command
    assert "--throughput-profile-label" in command
    assert DEFAULT_THROUGHPUT_PROFILE_LABEL in command
    assert "--ref-mel-cache-enabled" in command
    assert "--no-torch-profiler-enabled" in command
    assert "true" not in command
    assert "false" not in command


def test_inspect_detached_training_reads_container_status_and_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The detached training status view should combine Docker and training outputs."""
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
                "training_summary": {
                    "optimizer_steps_completed": 8,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    launch = DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="qwen-20260309t120000z",
        container_name="qwen-20260309t120000z-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=run_root.as_posix(),
        pilot_bundle_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle",
        train_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_pilot_train.prepared.jsonl",
        eval_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_checkpoint_dev.prepared.jsonl",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
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
            checkpoint_interval_steps=2,
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        ),
        command=["sudo", "-n", "docker", "run", "-d"],
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
        "scripts.sir_convert_a_lot.ml.qwen.training.orchestrator.docker_checked",
        fake_docker_checked,
    )

    status = inspect_detached_training(launch)

    assert status.running is False
    assert status.exit_code == 0
    assert status.pilot_status_found is True
    assert status.pilot_report_found is True
    assert status.latest_checkpoint_found is True
    assert status.logs_tail == "training log tail"


def test_resolve_launch_root_uses_latest_pointer(tmp_path: Path) -> None:
    """Status inspection should reuse the latest recorded launch when present."""
    output_root = tmp_path / "verification"
    current_launch_root = output_root / "qwen-20260309t120000z"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "latest-launch.json").write_text(
        json.dumps({"launch_root": current_launch_root.as_posix()}) + "\n",
        encoding="utf-8",
    )

    assert resolve_launch_root(output_root, None) == current_launch_root


def test_ensure_training_bundle_exists_validates_required_artifacts(tmp_path: Path) -> None:
    """Launch should fail fast when the deterministic training bundle is incomplete."""
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SystemExit, match="required training-bundle artifacts"):
        ensure_training_bundle_exists(
            bundle_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
        )


def test_ensure_training_bundle_exists_rejects_missing_manifest_assets(tmp_path: Path) -> None:
    """Launch should fail fast when manifests reference missing bundle assets."""
    bundle_root = tmp_path / "bundle"
    manifests_dir = bundle_root / "manifests"
    reports_dir = bundle_root / "reports"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "training_bundle_report.json").write_text("{}\n", encoding="utf-8")
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
        json.dumps({**prepared_row, "source_split": "dev"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="bundle integrity check failed"):
        ensure_training_bundle_exists(
            bundle_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
        )


def test_resume_uses_launch_metadata_dockerfile_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should reuse the original launch dockerfile path."""
    output_root = tmp_path / "verification"
    source_launch_root = output_root / "qwen-prev"
    source_run_root = tmp_path / "runs/qwen-prev"
    checkpoint_path = source_run_root / "checkpoints/state-step-00000008"
    output_root.mkdir(parents=True, exist_ok=True)
    source_launch_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    (source_run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )
    launch_payload = DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="qwen-prev",
        container_name="qwen-prev-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=source_run_root.as_posix(),
        pilot_bundle_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle",
        train_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_pilot_train.prepared.jsonl",
        eval_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_checkpoint_dev.prepared.jsonl",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path="containers/custom-qwen-finetune/Dockerfile",
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
            checkpoint_interval_steps=2,
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
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

    def fake_prepare_qwen_image(args: argparse.Namespace) -> tuple[bool, str]:
        captured["dockerfile_path"] = args.dockerfile_path
        return False, "sha256:test"

    def fake_resolve_hf_cache_dir(args: argparse.Namespace) -> MountResolution:
        del args
        return MountResolution(
            canonical_root=Path("/srv/scratch/cache"),
            effective_root=Path("/srv/scratch/cache"),
            used_home_mount=False,
        )

    def fake_resolve_bind_root(
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
    ) -> DetachedLaunch:
        del settings, repo_root, hf_mount, scratch_mount, container_name, launch_root
        captured["resume_dockerfile_path"] = dockerfile_path
        captured["run_root"] = run_root
        captured["resume_from_checkpoint"] = resume_from_checkpoint
        return launch_payload

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_train.prepare_qwen_image",
        fake_prepare_qwen_image,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_train.resolve_effective_hf_cache_dir",
        fake_resolve_hf_cache_dir,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_train.resolve_effective_bind_root",
        fake_resolve_bind_root,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_train.launch_detached_training",
        fake_launch_detached_training,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_train.write_json",
        lambda path, payload: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_train.write_latest_pointer",
        lambda output_root, launch_root: None,
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    result = main(
        [
            "resume",
            "--output-root",
            output_root.as_posix(),
            "--skip-build",
            "--disable-resource-monitor",
        ]
    )

    assert result == 0
    assert captured["dockerfile_path"] == Path("containers/custom-qwen-finetune/Dockerfile")
    assert captured["resume_dockerfile_path"] == Path("containers/custom-qwen-finetune/Dockerfile")
    assert captured["run_root"] == source_run_root
    assert captured["resume_from_checkpoint"] == checkpoint_path


def test_stop_detached_training_calls_docker_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stopping a detached launch should issue one deterministic docker stop."""
    launch = DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="qwen-prev",
        container_name="qwen-prev-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root="/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/qwen-prev",
        pilot_bundle_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle",
        train_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_pilot_train.prepared.jsonl",
        eval_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_checkpoint_dev.prepared.jsonl",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
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
            checkpoint_interval_steps=2,
            durable_checkpoint_retention=2,
            durable_checkpoint_min_free_bytes=16 * 1024**3,
        ),
        command=["sudo", "-n", "docker", "run", "-d"],
    )
    captured: dict[str, object] = {}

    def fake_docker_checked(args: list[str], *, label: str) -> str:
        captured["args"] = args
        captured["label"] = label
        return "qwen-prev-container"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.orchestrator.docker_checked",
        fake_docker_checked,
    )

    stopped = stop_detached_training(launch)

    assert isinstance(stopped, DetachedStop)
    assert captured["args"] == ["stop", "--time", "300", "qwen-prev-container"]
    assert captured["label"] == "docker stop qwen detached training"
    assert stopped.container_name == "qwen-prev-container"


def test_resume_checkpoint_path_rejects_cross_run_mismatch(tmp_path: Path) -> None:
    """Explicit resume checkpoints must belong to the selected source run root."""
    source_run_root = tmp_path / "run-a"
    other_run_checkpoint = tmp_path / "run-b/checkpoints/state-step-00000008"
    source_run_root.mkdir(parents=True, exist_ok=True)
    other_run_checkpoint.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SystemExit, match="must belong to the selected source launch run root"):
        validate_resume_checkpoint_path(source_run_root, other_run_checkpoint)


def test_load_latest_checkpoint_pointer(tmp_path: Path) -> None:
    """Resume latest should resolve the run-root latest-checkpoint pointer."""
    run_root = tmp_path / "run"
    checkpoint_path = run_root / "checkpoints/state-step-00000008"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )

    assert load_latest_checkpoint(run_root) == checkpoint_path
