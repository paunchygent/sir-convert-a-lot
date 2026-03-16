"""Docker command construction for detached Qwen training launches.

Purpose:
    Build the deterministic `docker run` argv for detached training and
    diagnostic launches without owning container execution or status parsing.

Relationships:
    - Consumed by detached launch services.
    - Reuses path helpers and CLI flag materialization shared by Qwen training.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    MountResolution,
)
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import boolean_flag
from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings

from .paths import (
    CONTAINER_BUILD_ROOT,
    containerize_scratch_path,
    eval_manifest_path,
    mlflow_artifact_root,
    mlflow_tracking_uri,
    pytorch_profiling_dir,
    rocm_profiling_dir,
    run_root_for_launch,
    tensorboard_logging_dir,
    train_manifest_path,
)


def build_detached_training_command(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    launch_id: str,
    container_name: str,
    launch_root: Path,
    run_root: Path | None = None,
    resume_from_checkpoint: Path | None = None,
    trainer_module: str = "scripts.sir_convert_a_lot.ml.qwen.training.trainer",
    extra_probe_args: list[str] | None = None,
) -> tuple[list[str], Path]:
    """Build the detached Docker command for one training run."""
    effective_run_root = (
        run_root if run_root is not None else run_root_for_launch(settings, launch_id=launch_id)
    )
    container_run_root = containerize_scratch_path(
        effective_run_root,
        scratch_root=settings.scratch_build_root,
    )
    container_train_jsonl = containerize_scratch_path(
        train_manifest_path(settings),
        scratch_root=settings.scratch_build_root,
    )
    container_eval_jsonl = containerize_scratch_path(
        eval_manifest_path(settings),
        scratch_root=settings.scratch_build_root,
    )
    container_launch_metadata_path = containerize_scratch_path(
        launch_root / "launch.json",
        scratch_root=settings.scratch_build_root,
    )
    container_pilot_bundle_root = containerize_scratch_path(
        settings.pilot_bundle_root,
        scratch_root=settings.scratch_build_root,
    )
    container_mlflow_artifact_root = containerize_scratch_path(
        mlflow_artifact_root(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_tensorboard_logging_dir = containerize_scratch_path(
        tensorboard_logging_dir(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_pytorch_profiling_dir = containerize_scratch_path(
        pytorch_profiling_dir(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_rocm_profiling_dir = containerize_scratch_path(
        rocm_profiling_dir(effective_run_root),
        scratch_root=settings.scratch_build_root,
    )
    container_resume_checkpoint = None
    if resume_from_checkpoint is not None:
        container_resume_checkpoint = containerize_scratch_path(
            resume_from_checkpoint,
            scratch_root=settings.scratch_build_root,
        )
    probe_args = [
        "--launch-id",
        launch_id,
        "--launch-metadata-path",
        container_launch_metadata_path,
        "--model-id",
        settings.model_id,
        "--train-jsonl",
        container_train_jsonl,
        "--eval-jsonl",
        container_eval_jsonl,
        "--pilot-bundle-root",
        container_pilot_bundle_root,
        "--train-manifest-family",
        settings.train_manifest_family,
        "--eval-manifest-family",
        settings.eval_manifest_family,
        "--text-embedding-mask-policy",
        settings.text_embedding_mask_policy,
        "--output-dir",
        container_run_root,
        "--tracker-project-name",
        "qwen-training",
        "--mlflow-experiment-name",
        "qwen-training",
        "--mlflow-tracking-uri",
        mlflow_tracking_uri(effective_run_root),
        "--mlflow-artifact-root",
        container_mlflow_artifact_root,
        "--tensorboard-logging-dir",
        container_tensorboard_logging_dir,
        "--tracker-run-name",
        launch_id,
        "--batch-size",
        str(settings.batch_size),
        "--throughput-profile-label",
        settings.throughput_profile_label,
        "--lr",
        str(settings.lr),
        "--num-epochs",
        str(settings.num_epochs),
        "--max-steps",
        str(settings.max_steps),
        "--checkpoint-interval-steps",
        str(settings.checkpoint_interval_steps),
        "--eval-interval-steps",
        str(settings.eval_interval_steps),
        "--durable-checkpoint-retention",
        str(settings.durable_checkpoint_retention),
        "--durable-checkpoint-min-free-bytes",
        str(settings.durable_checkpoint_min_free_bytes),
        "--dataloader-num-workers",
        str(settings.dataloader_num_workers),
        boolean_flag("--dataloader-pin-memory", settings.dataloader_pin_memory),
        boolean_flag(
            "--dataloader-persistent-workers",
            settings.dataloader_persistent_workers,
        ),
        "--dataloader-prefetch-factor",
        str(settings.dataloader_prefetch_factor),
        boolean_flag("--non-blocking-transfer", settings.non_blocking_transfer),
        boolean_flag("--data-path-proof-mode", settings.data_path_proof_mode),
        "--heartbeat-interval-optimizer-steps",
        str(settings.heartbeat_interval_optimizer_steps),
        "--finite-loss-max-consecutive-steps",
        str(settings.finite_loss_max_consecutive_steps),
        boolean_flag("--ref-mel-cache-enabled", settings.ref_mel_cache_enabled),
        "--ref-mel-cache-max-items",
        str(settings.ref_mel_cache_max_items),
        boolean_flag("--torch-profiler-enabled", settings.torch_profiler_enabled),
        "--torch-profiler-wait-steps",
        str(settings.torch_profiler_wait_steps),
        "--torch-profiler-warmup-steps",
        str(settings.torch_profiler_warmup_steps),
        "--torch-profiler-active-steps",
        str(settings.torch_profiler_active_steps),
        "--torch-profiler-repeat",
        str(settings.torch_profiler_repeat),
        boolean_flag("--torch-profiler-record-shapes", settings.torch_profiler_record_shapes),
        boolean_flag("--torch-profiler-profile-memory", settings.torch_profiler_profile_memory),
        boolean_flag("--torch-profiler-with-stack", settings.torch_profiler_with_stack),
        "--torch-profiler-trace-dir",
        container_pytorch_profiling_dir,
    ]
    if extra_probe_args is not None:
        probe_args.extend(extra_probe_args)
    command = [
        "run",
        "-d",
        "--name",
        container_name,
        "--label",
        "sir_convert_a_lot.domain=qwen-training",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
        "--ipc=host",
        "--cap-add=SYS_PTRACE",
        "--security-opt",
        "seccomp=unconfined",
        "-e",
        "HF_HUB_DISABLE_XET=1",
        "-e",
        f"HF_HOME={CONTAINER_HF_HOME}",
        "-e",
        f"HUGGINGFACE_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
        "-e",
        f"TORCH_HOME={CONTAINER_TORCH_HOME}",
        "-v",
        f"{repo_root.as_posix()}:/app",
        "-v",
        f"{scratch_mount.effective_root.as_posix()}:{CONTAINER_BUILD_ROOT.as_posix()}",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
        "--workdir",
        "/app",
        "--entrypoint",
        "python",
        settings.image,
    ]
    if settings.rocm_profiler_enabled:
        command.extend(
            [
                "-m",
                "scripts.sir_convert_a_lot.ml.qwen.training.trainer_rocprof_wrapper",
                "--rocprof-output-dir",
                container_rocm_profiling_dir,
                "--rocprof-trace-name",
                launch_id,
                "--",
                *probe_args,
            ]
        )
    else:
        command.extend(["-m", trainer_module, *probe_args])
    if container_resume_checkpoint is not None:
        command.extend(["--resume-from-checkpoint", container_resume_checkpoint])
    return command, effective_run_root
