"""Tests for canonical detached Qwen training orchestration."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.cli.ml.qwen_train import main
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane import build_parser
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.bundle_contract import (
    ensure_training_bundle_exists,
)
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_LR,
    DEFAULT_MAX_STEPS,
    DEFAULT_MODEL_ID,
    DEFAULT_NUM_EPOCHS,
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    LEGACY_SMALL_BATCH_THROUGHPUT_PROFILE_LABEL,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import (
    build_detached_training_command,
    inspect_detached_training,
    launch_detached_training,
    stop_detached_training,
)
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
    assert args.gradient_accumulation_steps == 4
    assert args.batch_size == 8
    assert args.throughput_profile_label == DEFAULT_THROUGHPUT_PROFILE_LABEL
    assert args.checkpoint_interval_steps == DEFAULT_CHECKPOINT_INTERVAL_STEPS
    assert args.eval_interval_steps == 100
    assert args.durable_checkpoint_retention == DEFAULT_DURABLE_CHECKPOINT_RETENTION
    assert args.durable_checkpoint_min_free_bytes == DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES
    assert args.dataloader_pin_memory is True
    assert args.dataloader_persistent_workers is True
    assert args.non_blocking_transfer is True
    assert args.data_path_proof_mode is False
    assert args.ref_mel_cache_enabled is True
    assert args.torch_profiler_enabled is False
    assert args.rocm_profiler_enabled is False
    assert args.resource_monitor_interval_seconds == 1.0
    assert args.resource_monitor_runtime_kind == "rocm"
    assert args.disable_resource_monitor is False
    assert args.skip_build is False


def test_parser_launch_accepts_explicit_boolean_values() -> None:
    """The training parser should accept explicit boolean values for operator ergonomics."""
    parser = build_parser()

    args = parser.parse_args(
        [
            "launch",
            "--data-path-proof-mode",
            "true",
            "--dataloader-persistent-workers",
            "false",
            "--non-blocking-transfer",
            "no",
        ]
    )

    assert args.data_path_proof_mode is True
    assert args.dataloader_persistent_workers is False
    assert args.non_blocking_transfer is False


def test_parser_resume_accepts_bounded_training_overrides() -> None:
    """Resume should accept explicit num-epochs and max-steps overrides."""
    parser = build_parser()

    args = parser.parse_args(
        [
            "resume",
            "--num-epochs",
            "12",
            "--max-steps",
            "1566",
        ]
    )

    assert args.num_epochs == 12
    assert args.max_steps == 1566


def test_parser_resume_accepts_gradient_accumulation_override() -> None:
    """Resume should accept bounded accumulation overrides for proof runs."""
    parser = build_parser()

    args = parser.parse_args(
        [
            "resume",
            "--gradient-accumulation-steps",
            "2",
        ]
    )

    assert args.gradient_accumulation_steps == 2


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
            "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-pilot-bundle"
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
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
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
        "/app/build/reference/qwen3-tts-swedish-pilot-bundle/manifests/"
        "swedish_pilot_train.prepared.jsonl" in command
    )
    assert (
        "/app/build/reference/qwen3-tts-swedish-pilot-bundle/manifests/"
        "swedish_checkpoint_dev.prepared.jsonl" in command
    )
    assert "--dataloader-pin-memory" in command
    assert "--dataloader-persistent-workers" in command
    assert "--non-blocking-transfer" in command
    assert "--no-data-path-proof-mode" in command
    assert "--throughput-profile-label" in command
    assert DEFAULT_THROUGHPUT_PROFILE_LABEL in command
    assert "--gradient-accumulation-steps" in command
    assert "4" in command
    assert "--eval-interval-steps" in command
    assert "100" in command
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
                "upstream_trainer_uses_eval_manifest": True,
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
        launch_kind="training",
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
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
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
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.inspect_service.docker_checked",
        fake_docker_checked,
    )

    status = inspect_detached_training(launch)

    assert status.running is False
    assert status.exit_code == 0
    assert status.pilot_status_found is True
    assert status.pilot_report_found is True
    assert status.latest_checkpoint_found is True
    assert status.logs_tail == "training log tail"


def test_inspect_detached_training_hides_stale_resumed_run_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running resumed launches should not surface stale pre-launch run-root artifacts."""
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "status.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "updated_at": "2026-03-15T09:56:58Z",
                "current_phase": "failed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "report.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "generated_at": "2026-03-15T09:56:58Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    launch = DetachedLaunch(
        generated_at="2026-03-15T10:21:50Z",
        launch_kind="training",
        launch_id="resume-launch",
        container_name="resume-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=run_root.as_posix(),
        pilot_bundle_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle",
        train_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_pilot_train.prepared.jsonl",
        eval_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_checkpoint_dev.prepared.jsonl",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
        resumed_from_checkpoint_path=(
            "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/"
            "qwen-historical-pilot-20260313t102144z/checkpoints/state-step-00001236"
        ),
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

    def fake_docker_checked(args: list[str], *, label: str) -> str:
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
                            "StartedAt": "2026-03-15T10:21:49.938119681Z",
                            "FinishedAt": "0001-01-01T00:00:00Z",
                        },
                    }
                ]
            )
        if args[0] == "logs":
            return ""
        raise AssertionError(f"Unexpected docker args: {args} ({label})")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.inspect_service.docker_checked",
        fake_docker_checked,
    )

    status = inspect_detached_training(launch)

    assert status.running is True
    assert status.pilot_status_found is False
    assert status.pilot_status is None
    assert status.pilot_report_found is False
    assert status.pilot_report is None


def test_inspect_detached_training_hides_stale_resumed_run_artifacts_after_stop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stopped resumed launches should also suppress stale pre-launch reports."""
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "status.json").write_text(
        json.dumps(
            {
                "status": "running",
                "updated_at": "2026-03-15T10:31:24Z",
                "current_phase": "checkpoint-save",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "report.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "generated_at": "2026-03-15T09:56:58Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    launch = DetachedLaunch(
        generated_at="2026-03-15T10:21:50Z",
        launch_kind="training",
        launch_id="resume-launch",
        container_name="resume-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        run_root=run_root.as_posix(),
        pilot_bundle_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle",
        train_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_pilot_train.prepared.jsonl",
        eval_jsonl="/srv/scratch/sir-convert-a-lot/build/reference/qwen-bundle/manifests/swedish_checkpoint_dev.prepared.jsonl",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        dockerfile_path=DEFAULT_DOCKERFILE_PATH.as_posix(),
        resumed_from_checkpoint_path=(
            "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune/"
            "qwen-historical-pilot-20260313t102144z/checkpoints/state-step-00001236"
        ),
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

    def fake_docker_checked(args: list[str], *, label: str) -> str:
        if args[0] == "inspect":
            return json.dumps(
                [
                    {
                        "Id": "container-id",
                        "State": {
                            "Status": "exited",
                            "Running": False,
                            "ExitCode": 137,
                            "OOMKilled": False,
                            "StartedAt": "2026-03-15T10:21:49.938119681Z",
                            "FinishedAt": "2026-03-15T10:33:12Z",
                        },
                    }
                ]
            )
        if args[0] == "logs":
            return "Received stop request; saving one final durable checkpoint before exit."
        raise AssertionError(f"Unexpected docker args: {args} ({label})")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.inspect_service.docker_checked",
        fake_docker_checked,
    )

    status = inspect_detached_training(launch)

    assert status.running is False
    assert status.pilot_status_found is True
    assert status.pilot_report_found is False
    assert status.pilot_report is None


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

    with pytest.raises(SystemExit, match="Available manifest families under the bundle root: none"):
        ensure_training_bundle_exists(
            bundle_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
        )


def test_ensure_training_bundle_exists_reports_available_manifest_families(
    tmp_path: Path,
) -> None:
    """Launch failures should report which manifest families actually exist."""
    bundle_root = tmp_path / "bundle"
    manifests_dir = bundle_root / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / "swedish_pilot_train.prepared.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="swedish_pilot_train"):
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


def test_ensure_training_bundle_exists_accepts_legacy_bundle_without_report(tmp_path: Path) -> None:
    """Launch should accept retained bundles that predate persisted ref-mel reports."""
    bundle_root = tmp_path / "bundle"
    manifests_dir = bundle_root / "manifests"
    audio_dir = bundle_root / "audio_24k" / "rixvox" / "train" / "speaker-a"
    refs_dir = bundle_root / "refs" / "swedish_pilot_train" / "speaker-a"
    eval_refs_dir = bundle_root / "refs" / "swedish_checkpoint_dev" / "speaker-a"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)
    eval_refs_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "train.wav").write_bytes(b"audio")
    (refs_dir / "ref.wav").write_bytes(b"ref")
    (eval_refs_dir / "ref.wav").write_bytes(b"ref")
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
                "ref_audio": "refs/swedish_checkpoint_dev/speaker-a/ref.wav",
                "source_split": "dev",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    ensure_training_bundle_exists(
        bundle_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
    )


def test_ensure_training_bundle_exists_rejects_rebuilt_bundle_missing_precomputed_ref_metadata(
    tmp_path: Path,
) -> None:
    """Rebuilt bundles should fail closed when prepared rows omit persisted ref-input fields."""
    bundle_root = tmp_path / "bundle"
    manifests_dir = bundle_root / "manifests"
    reports_dir = bundle_root / "reports"
    audio_dir = bundle_root / "audio_24k" / "rixvox" / "train" / "speaker-a"
    refs_dir = bundle_root / "refs" / "swedish_pilot_train" / "speaker-a"
    eval_refs_dir = bundle_root / "refs" / "swedish_checkpoint_dev" / "speaker-a"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)
    eval_refs_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "train.wav").write_bytes(b"audio")
    (refs_dir / "ref.wav").write_bytes(b"ref")
    (eval_refs_dir / "ref.wav").write_bytes(b"ref")
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
                "ref_audio": "refs/swedish_checkpoint_dev/speaker-a/ref.wav",
                "source_split": "dev",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (reports_dir / "training_bundle_report.json").write_text(
        json.dumps(
            {
                "source_root": bundle_root.as_posix(),
                "output_root": bundle_root.as_posix(),
                "train_manifest_family": "swedish_pilot_train",
                "eval_manifest_family": "swedish_checkpoint_dev",
                "tokenizer_model": "Qwen/Qwen3-TTS-Tokenizer-12Hz",
                "retained_row_count": 2,
                "conflict_row_count": 0,
                "manifest_row_counts": {
                    "swedish_pilot_train": 1,
                    "swedish_checkpoint_dev": 1,
                },
                "speaker_counts": {
                    "swedish_pilot_train": 1,
                    "swedish_checkpoint_dev": 1,
                },
                "owned_row_keys_path": (reports_dir / "owned.jsonl").as_posix(),
                "conflict_row_keys_path": (reports_dir / "conflict.jsonl").as_posix(),
                "repo_head": "test-head",
                "generated_at": "2026-03-14T00:00:00Z",
                "finalization_batch_row_count": 512,
                "total_batch_count": 1,
                "batch_plan_path": (reports_dir / "training_bundle_plan.json").as_posix(),
                "events_path": (reports_dir / "training_bundle_events.jsonl").as_posix(),
                "status_path": (reports_dir / "training_bundle_status.json").as_posix(),
                "precomputed_reference_input": {
                    "kind": "ref_mel",
                    "version": "qwen_reference_mel_v1",
                    "source_field": "ref_audio",
                    "artifact_root": "precomputed/ref_mel",
                    "artifact_count": 2,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="precomputed_ref_input_path"):
        ensure_training_bundle_exists(
            bundle_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
        )


def test_launch_detached_training_accepts_legacy_bundle_without_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detached launch metadata should omit precomputed-ref payload for retained bundles."""
    settings = TrainingSettings(
        output_root=tmp_path / "verification",
        image="sir-convert-a-lot-qwen-finetune-hemma:historical-control",
        hf_cache_dir=tmp_path / "cache/hf",
        hf_cache_home_mount=tmp_path / "home/cache/hf",
        scratch_build_root=tmp_path / "build",
        scratch_build_home_mount=tmp_path / "home/build",
        pilot_bundle_root=tmp_path / "bundle",
        runs_root=tmp_path / "runs",
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        batch_size=8,
        throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        lr=2e-5,
        num_epochs=1,
        max_steps=8,
        checkpoint_interval_steps=2,
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.launch_service.build_detached_training_command",
        lambda *args, **kwargs: (["run", "-d"], tmp_path / "runs/launch"),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.launch_service.docker_checked",
        lambda args, *, label: "container-id\n",
    )

    launch = launch_detached_training(
        settings,
        repo_root=tmp_path / "repo",
        hf_mount=MountResolution(
            canonical_root=settings.hf_cache_dir,
            effective_root=settings.hf_cache_home_mount,
            used_home_mount=True,
        ),
        scratch_mount=MountResolution(
            canonical_root=settings.scratch_build_root,
            effective_root=settings.scratch_build_home_mount,
            used_home_mount=True,
        ),
        launch_id="legacy-launch",
        container_name="legacy-container",
        launch_root=tmp_path / "verification/legacy-launch",
    )

    assert launch.container_id == "container-id"
    assert launch.bundle_precomputed_reference_input is None


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
        launch_kind="training",
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
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
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

    def fake_prepare_runtime_dependencies(
        *,
        settings: TrainingSettings,
        dockerfile_path: Path,
        skip_build: bool,
    ) -> tuple[bool, str, MountResolution, MountResolution]:
        del settings, skip_build
        captured["dockerfile_path"] = dockerfile_path
        return (
            False,
            "sha256:test",
            MountResolution(
                canonical_root=Path("/srv/scratch/cache"),
                effective_root=Path("/srv/scratch/cache"),
                used_home_mount=False,
            ),
            MountResolution(
                canonical_root=Path("/srv/scratch/sir-convert-a-lot/build"),
                effective_root=Path("/srv/scratch/sir-convert-a-lot/build"),
                used_home_mount=False,
            ),
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
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.prepare_runtime_dependencies",
        fake_prepare_runtime_dependencies,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.ensure_training_bundle_exists",
        lambda bundle_root, *, train_manifest_family, eval_manifest_family: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.launch_detached_training",
        fake_launch_detached_training,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.write_json",
        lambda path, payload: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.write_latest_pointer",
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


def test_resume_legacy_launch_uses_bundle_override_and_small_batch_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should accept a retained launch snapshot and redirect to a replacement bundle."""
    output_root = tmp_path / "verification"
    source_launch_root = tmp_path / "legacy-source"
    source_run_root = tmp_path / "runs/qwen-prev"
    checkpoint_path = source_run_root / "checkpoints/state-step-00001236"
    replacement_bundle_root = tmp_path / "replacement-bundle"
    legacy_output_root = (
        "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-pilot"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    source_launch_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    replacement_bundle_root.mkdir(parents=True, exist_ok=True)
    (source_run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )
    legacy_launch_payload = {
        "generated_at": "2026-03-13T10:21:45Z",
        "launch_id": "qwen-historical-pilot-20260313t102144z",
        "container_name": "qwen-historical-pilot-20260313t102144z-container",
        "container_id": "container-id",
        "repo_root": "/home/paunchygent/apps/sir-convert-a-lot",
        "run_root": source_run_root.as_posix(),
        "pilot_bundle_root": (tmp_path / "missing-bundle").as_posix(),
        "train_jsonl": (tmp_path / "missing-bundle/manifests/train.jsonl").as_posix(),
        "eval_jsonl": (tmp_path / "missing-bundle/manifests/eval.jsonl").as_posix(),
        "train_manifest_family": "swedish_pilot_train",
        "eval_manifest_family": "swedish_checkpoint_dev",
        "dockerfile_path": "containers/qwen-finetune-hemma/Dockerfile",
        "resumed_from_checkpoint_path": None,
        "settings": {
            "output_root": legacy_output_root,
            "image": "sir-convert-a-lot-qwen-finetune-hemma:historical-control",
            "hf_cache_dir": "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            "hf_cache_home_mount": "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
            "scratch_build_root": "/srv/scratch/sir-convert-a-lot/build",
            "scratch_build_home_mount": "/home/paunchygent/.data/sir-convert-a-lot/build",
            "pilot_bundle_root": (tmp_path / "missing-bundle").as_posix(),
            "runs_root": "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune",
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "train_manifest_family": "swedish_pilot_train",
            "eval_manifest_family": "swedish_checkpoint_dev",
            "batch_size": 1,
            "lr": 2e-5,
            "num_epochs": 1000,
            "max_steps": 1000000,
            "checkpoint_interval_steps": 2,
            "durable_checkpoint_retention": 2,
            "durable_checkpoint_min_free_bytes": 16 * 1024**3,
        },
        "command": ["sudo", "-n", "docker", "run", "-d"],
    }
    (source_launch_root / "launch.json").write_text(
        json.dumps(legacy_launch_payload) + "\n",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.ensure_training_bundle_exists",
        lambda bundle_root, *, train_manifest_family, eval_manifest_family: captured.update(
            {
                "bundle_root": bundle_root,
                "train_manifest_family": train_manifest_family,
                "eval_manifest_family": eval_manifest_family,
            }
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.prepare_runtime_dependencies",
        lambda *, settings, dockerfile_path, skip_build: (
            False,
            "sha256:test",
            MountResolution(
                canonical_root=Path("/srv/scratch/cache"),
                effective_root=Path("/srv/scratch/cache"),
                used_home_mount=False,
            ),
            MountResolution(
                canonical_root=Path("/srv/scratch/sir-convert-a-lot/build"),
                effective_root=Path("/srv/scratch/sir-convert-a-lot/build"),
                used_home_mount=False,
            ),
        ),
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
        del (
            repo_root,
            hf_mount,
            scratch_mount,
            launch_id,
            container_name,
            launch_root,
            dockerfile_path,
        )
        captured["settings"] = settings
        captured["run_root"] = run_root
        captured["resume_from_checkpoint"] = resume_from_checkpoint
        return DetachedLaunch(
            generated_at="2026-03-15T10:00:00Z",
            launch_kind="training",
            launch_id="resume-launch",
            container_name="resume-container",
            container_id="container-id",
            repo_root="/home/paunchygent/apps/sir-convert-a-lot",
            run_root=source_run_root.as_posix(),
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
            resumed_from_checkpoint_path=resume_from_checkpoint.as_posix()
            if resume_from_checkpoint
            else None,
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
            command=["sudo", "-n", "docker", "run", "-d"],
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.launch_detached_training",
        fake_launch_detached_training,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.write_json",
        lambda path, payload: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.write_latest_pointer",
        lambda output_root, launch_root: None,
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    result = main(
        [
            "resume",
            "--output-root",
            output_root.as_posix(),
            "--launch-root",
            source_launch_root.as_posix(),
            "--pilot-bundle-root",
            replacement_bundle_root.as_posix(),
            "--skip-build",
            "--disable-resource-monitor",
        ]
    )

    assert result == 0
    settings = captured["settings"]
    assert isinstance(settings, TrainingSettings)
    assert settings.pilot_bundle_root == replacement_bundle_root
    assert settings.throughput_profile_label == LEGACY_SMALL_BATCH_THROUGHPUT_PROFILE_LABEL
    assert captured["bundle_root"] == replacement_bundle_root
    assert captured["run_root"] == source_run_root
    assert captured["resume_from_checkpoint"] == checkpoint_path


def test_resume_accepts_explicit_control_posture_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should let operators move a recovered lane onto a bounded 500/100/3 pilot."""
    output_root = tmp_path / "verification"
    source_launch_root = tmp_path / "legacy-source"
    source_run_root = tmp_path / "runs/qwen-prev"
    checkpoint_path = source_run_root / "checkpoints/state-step-00001238"
    replacement_bundle_root = tmp_path / "replacement-bundle"
    legacy_output_root = (
        "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-pilot"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    source_launch_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    replacement_bundle_root.mkdir(parents=True, exist_ok=True)
    (source_run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )
    legacy_launch_payload = {
        "generated_at": "2026-03-13T10:21:45Z",
        "launch_id": "qwen-historical-pilot-20260313t102144z",
        "container_name": "qwen-historical-pilot-20260313t102144z-container",
        "container_id": "container-id",
        "repo_root": "/home/paunchygent/apps/sir-convert-a-lot",
        "run_root": source_run_root.as_posix(),
        "pilot_bundle_root": (tmp_path / "missing-bundle").as_posix(),
        "train_jsonl": (tmp_path / "missing-bundle/manifests/train.jsonl").as_posix(),
        "eval_jsonl": (tmp_path / "missing-bundle/manifests/eval.jsonl").as_posix(),
        "train_manifest_family": "swedish_pilot_train",
        "eval_manifest_family": "swedish_checkpoint_dev",
        "dockerfile_path": "containers/qwen-finetune-hemma/Dockerfile",
        "resumed_from_checkpoint_path": None,
        "settings": {
            "output_root": legacy_output_root,
            "image": "sir-convert-a-lot-qwen-finetune-hemma:historical-control",
            "hf_cache_dir": "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            "hf_cache_home_mount": "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
            "scratch_build_root": "/srv/scratch/sir-convert-a-lot/build",
            "scratch_build_home_mount": "/home/paunchygent/.data/sir-convert-a-lot/build",
            "pilot_bundle_root": (tmp_path / "missing-bundle").as_posix(),
            "runs_root": "/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-finetune",
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "train_manifest_family": "swedish_pilot_train",
            "eval_manifest_family": "swedish_checkpoint_dev",
            "batch_size": 1,
            "lr": 2e-5,
            "num_epochs": 1000,
            "max_steps": 1000000,
            "checkpoint_interval_steps": 2,
            "durable_checkpoint_retention": 2,
            "durable_checkpoint_min_free_bytes": 16 * 1024**3,
        },
        "command": ["sudo", "-n", "docker", "run", "-d"],
    }
    (source_launch_root / "launch.json").write_text(
        json.dumps(legacy_launch_payload) + "\n",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.ensure_training_bundle_exists",
        lambda bundle_root, *, train_manifest_family, eval_manifest_family: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.prepare_runtime_dependencies",
        lambda *, settings, dockerfile_path, skip_build: (
            False,
            "sha256:test",
            MountResolution(
                canonical_root=Path("/srv/scratch/cache"),
                effective_root=Path("/srv/scratch/cache"),
                used_home_mount=False,
            ),
            MountResolution(
                canonical_root=Path("/srv/scratch/sir-convert-a-lot/build"),
                effective_root=Path("/srv/scratch/sir-convert-a-lot/build"),
                used_home_mount=False,
            ),
        ),
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
        del (
            repo_root,
            hf_mount,
            scratch_mount,
            launch_id,
            container_name,
            launch_root,
            dockerfile_path,
            run_root,
            resume_from_checkpoint,
        )
        captured["settings"] = settings
        return DetachedLaunch(
            generated_at="2026-03-15T10:00:00Z",
            launch_kind="training",
            launch_id="resume-launch",
            container_name="resume-container",
            container_id="container-id",
            repo_root="/home/paunchygent/apps/sir-convert-a-lot",
            run_root=source_run_root.as_posix(),
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
            resumed_from_checkpoint_path=checkpoint_path.as_posix(),
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
            command=["sudo", "-n", "docker", "run", "-d"],
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.launch_detached_training",
        fake_launch_detached_training,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.write_json",
        lambda path, payload: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.control_plane.resume_use_case.write_latest_pointer",
        lambda output_root, launch_root: None,
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    result = main(
        [
            "resume",
            "--output-root",
            output_root.as_posix(),
            "--launch-root",
            source_launch_root.as_posix(),
            "--pilot-bundle-root",
            replacement_bundle_root.as_posix(),
            "--num-epochs",
            "12",
            "--max-steps",
            "1566",
            "--checkpoint-interval-steps",
            "500",
            "--eval-interval-steps",
            "100",
            "--durable-checkpoint-retention",
            "3",
            "--skip-build",
            "--disable-resource-monitor",
        ]
    )

    assert result == 0
    settings = captured["settings"]
    assert isinstance(settings, TrainingSettings)
    assert settings.pilot_bundle_root == replacement_bundle_root
    assert settings.num_epochs == 12
    assert settings.max_steps == 1566
    assert settings.checkpoint_interval_steps == 500
    assert settings.eval_interval_steps == 100
    assert settings.durable_checkpoint_retention == 3


def test_resume_fails_closed_when_legacy_source_bundle_root_is_missing(tmp_path: Path) -> None:
    """Resume should fail before launch when the effective source bundle root is gone."""
    output_root = tmp_path / "verification"
    source_launch_root = output_root / "qwen-prev"
    source_run_root = tmp_path / "runs/qwen-prev"
    checkpoint_path = source_run_root / "checkpoints/state-step-00001236"
    output_root.mkdir(parents=True, exist_ok=True)
    source_launch_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    (source_run_root / "latest_checkpoint.json").write_text(
        json.dumps({"checkpoint_path": checkpoint_path.as_posix()}) + "\n",
        encoding="utf-8",
    )
    legacy_launch_payload = {
        "generated_at": "2026-03-13T10:21:45Z",
        "launch_id": "qwen-historical-pilot-20260313t102144z",
        "container_name": "qwen-historical-pilot-20260313t102144z-container",
        "container_id": "container-id",
        "repo_root": "/home/paunchygent/apps/sir-convert-a-lot",
        "run_root": source_run_root.as_posix(),
        "pilot_bundle_root": (tmp_path / "missing-bundle").as_posix(),
        "train_jsonl": (tmp_path / "missing-bundle/manifests/train.jsonl").as_posix(),
        "eval_jsonl": (tmp_path / "missing-bundle/manifests/eval.jsonl").as_posix(),
        "train_manifest_family": "swedish_pilot_train",
        "eval_manifest_family": "swedish_checkpoint_dev",
        "dockerfile_path": "containers/qwen-finetune-hemma/Dockerfile",
        "resumed_from_checkpoint_path": None,
        "settings": {
            "output_root": output_root.as_posix(),
            "image": "sir-convert-a-lot-qwen-finetune-hemma:historical-control",
            "hf_cache_dir": "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            "hf_cache_home_mount": "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
            "scratch_build_root": tmp_path.as_posix(),
            "scratch_build_home_mount": tmp_path.as_posix(),
            "pilot_bundle_root": (tmp_path / "missing-bundle").as_posix(),
            "runs_root": (tmp_path / "runs").as_posix(),
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "train_manifest_family": "swedish_pilot_train",
            "eval_manifest_family": "swedish_checkpoint_dev",
            "batch_size": 1,
            "lr": 2e-5,
            "num_epochs": 1000,
            "max_steps": 1000000,
            "checkpoint_interval_steps": 2,
            "durable_checkpoint_retention": 2,
            "durable_checkpoint_min_free_bytes": 16 * 1024**3,
        },
        "command": ["sudo", "-n", "docker", "run", "-d"],
    }
    (source_launch_root / "launch.json").write_text(
        json.dumps(legacy_launch_payload) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        SystemExit,
        match="Qwen training could not find the required training-bundle artifacts",
    ):
        main(
            [
                "resume",
                "--output-root",
                output_root.as_posix(),
                "--launch-root",
                source_launch_root.as_posix(),
                "--disable-resource-monitor",
                "--skip-build",
            ]
        )


def test_stop_detached_training_calls_docker_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stopping a detached launch should issue one deterministic docker stop."""
    launch = DetachedLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_kind="training",
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
            eval_interval_steps=100,
            durable_checkpoint_retention=3,
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
        "scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.stop_service.docker_checked",
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
