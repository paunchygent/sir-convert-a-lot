"""Public CLI entrypoint for detached Qwen training on Hemma.

Purpose:
    Provide the canonical detached Hemma entrypoint for launching, resuming,
    inspecting, and stopping bounded Qwen training runs.

Relationships:
    - Uses `ml.qwen.training.orchestrator` for detached Docker launch and
      status inspection.
    - Consumes deterministic training bundles from `ml.qwen.training.bundles`.
    - Reuses shared image-build and cache-mount helpers from `ml.qwen.common`.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, replace
from pathlib import Path
from typing import Literal

from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_inputs import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
)
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.ml.qwen.common.storage import DEFAULT_SCRATCH_BUILD_ROOT
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import iter_jsonl_objects
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    bundle_manifest_path,
    bundle_report_path,
    load_training_bundle_summary,
)
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import add_boolean_argument
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    launch_metadata_path,
    launch_root,
    load_latest_checkpoint,
    load_launch,
    render_status_markdown,
    resolve_launch_root,
    status_markdown_path,
    status_metadata_path,
    stop_metadata_path,
    validate_resume_checkpoint_path,
    write_json,
    write_latest_pointer,
    write_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    DetachedLaunch,
    TrainingSettings,
    settings_from_snapshot,
)
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import (
    DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    launch_resource_monitor,
)
from scripts.sir_convert_a_lot.ml.qwen.training.orchestrator import (
    default_container_name,
    default_launch_id,
    inspect_detached_training,
    launch_detached_training,
    stop_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    resolve_throughput_batch_policy,
)

DEFAULT_OUTPUT_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "verification/qwen3-tts-swedish-hemma-training"
DEFAULT_RUNS_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "runs/qwen3-tts-swedish-finetune"
DEFAULT_SCRATCH_BUILD_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/build")
DEFAULT_DOCKERFILE_PATH = Path("containers/qwen-finetune-hemma/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:latest"
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DEFAULT_PILOT_BUNDLE_ROOT = (
    DEFAULT_SCRATCH_BUILD_ROOT / "reference/qwen3-tts-swedish-task101-pilot-bundle"
)
DEFAULT_HEMMA_HF_CACHE_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH"
DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT"
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_TRAIN_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_EVAL_MANIFEST_FAMILY = "swedish_checkpoint_dev"
DEFAULT_BATCH_SIZE = 8
DEFAULT_LR = 2e-5
DEFAULT_NUM_EPOCHS = 1
DEFAULT_MAX_STEPS = 8
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 100
DEFAULT_DURABLE_CHECKPOINT_RETENTION = 2
DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES = 16 * 1024**3
DEFAULT_DATALOADER_NUM_WORKERS = 4
DEFAULT_DATALOADER_PIN_MEMORY = True
DEFAULT_DATALOADER_PERSISTENT_WORKERS = True
DEFAULT_DATALOADER_PREFETCH_FACTOR = 4
DEFAULT_NON_BLOCKING_TRANSFER = True
DEFAULT_DATA_PATH_PROOF_MODE = False
DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS = 20
DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS = 3
DEFAULT_REF_MEL_CACHE_ENABLED = True
DEFAULT_REF_MEL_CACHE_MAX_ITEMS = 2048
DEFAULT_TORCH_PROFILER_ENABLED = False
DEFAULT_TORCH_PROFILER_WAIT_STEPS = 1
DEFAULT_TORCH_PROFILER_WARMUP_STEPS = 1
DEFAULT_TORCH_PROFILER_ACTIVE_STEPS = 4
DEFAULT_TORCH_PROFILER_REPEAT = 1
DEFAULT_TORCH_PROFILER_RECORD_SHAPES = True
DEFAULT_TORCH_PROFILER_PROFILE_MEMORY = True
DEFAULT_TORCH_PROFILER_WITH_STACK = False
DEFAULT_ROCM_PROFILER_ENABLED = False
TrainingCommand = Literal["launch", "resume", "status", "stop"]


def default_hf_cache_dir() -> Path:
    """Resolve the canonical Hemma Hugging Face cache path for training."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE
    return Path(configured_path.strip())


def default_hf_cache_home_mount() -> Path:
    """Resolve the fallback home-backed Hugging Face cache mount path."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE_HOME_MOUNT
    return Path(configured_path.strip())


def build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for detached Qwen training."""
    parser = argparse.ArgumentParser(description="Launch or inspect detached Qwen training.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch the detached training run.")
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    launch.add_argument("--pilot-bundle-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)
    launch.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    launch.add_argument("--image", default=DEFAULT_IMAGE)
    launch.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    launch.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=default_hf_cache_home_mount(),
    )
    launch.add_argument("--scratch-build-root", type=Path, default=DEFAULT_SCRATCH_BUILD_ROOT)
    launch.add_argument(
        "--scratch-build-home-mount",
        type=Path,
        default=DEFAULT_SCRATCH_BUILD_HOME_MOUNT,
    )
    launch.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    launch.add_argument("--train-manifest-family", default=DEFAULT_TRAIN_MANIFEST_FAMILY)
    launch.add_argument("--eval-manifest-family", default=DEFAULT_EVAL_MANIFEST_FAMILY)
    launch.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    launch.add_argument(
        "--throughput-profile-label",
        default=DEFAULT_THROUGHPUT_PROFILE_LABEL,
    )
    launch.add_argument("--lr", type=float, default=DEFAULT_LR)
    launch.add_argument("--num-epochs", type=int, default=DEFAULT_NUM_EPOCHS)
    launch.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    launch.add_argument(
        "--checkpoint-interval-steps",
        type=int,
        default=DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    )
    launch.add_argument(
        "--durable-checkpoint-retention",
        type=int,
        default=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    )
    launch.add_argument(
        "--durable-checkpoint-min-free-bytes",
        type=int,
        default=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    )
    launch.add_argument(
        "--dataloader-num-workers",
        type=int,
        default=DEFAULT_DATALOADER_NUM_WORKERS,
    )
    add_boolean_argument(
        launch,
        "--dataloader-pin-memory",
        default=DEFAULT_DATALOADER_PIN_MEMORY,
    )
    add_boolean_argument(
        launch,
        "--dataloader-persistent-workers",
        default=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    )
    launch.add_argument(
        "--dataloader-prefetch-factor",
        type=int,
        default=DEFAULT_DATALOADER_PREFETCH_FACTOR,
    )
    add_boolean_argument(
        launch,
        "--non-blocking-transfer",
        default=DEFAULT_NON_BLOCKING_TRANSFER,
    )
    add_boolean_argument(
        launch,
        "--data-path-proof-mode",
        default=DEFAULT_DATA_PATH_PROOF_MODE,
    )
    launch.add_argument(
        "--heartbeat-interval-optimizer-steps",
        type=int,
        default=DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
    )
    launch.add_argument(
        "--finite-loss-max-consecutive-steps",
        type=int,
        default=DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    )
    add_boolean_argument(
        launch,
        "--ref-mel-cache-enabled",
        default=DEFAULT_REF_MEL_CACHE_ENABLED,
    )
    launch.add_argument(
        "--ref-mel-cache-max-items",
        type=int,
        default=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    )
    add_boolean_argument(
        launch,
        "--torch-profiler-enabled",
        default=DEFAULT_TORCH_PROFILER_ENABLED,
    )
    launch.add_argument(
        "--torch-profiler-wait-steps",
        type=int,
        default=DEFAULT_TORCH_PROFILER_WAIT_STEPS,
    )
    launch.add_argument(
        "--torch-profiler-warmup-steps",
        type=int,
        default=DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
    )
    launch.add_argument(
        "--torch-profiler-active-steps",
        type=int,
        default=DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
    )
    launch.add_argument(
        "--torch-profiler-repeat",
        type=int,
        default=DEFAULT_TORCH_PROFILER_REPEAT,
    )
    add_boolean_argument(
        launch,
        "--torch-profiler-record-shapes",
        default=DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    )
    add_boolean_argument(
        launch,
        "--torch-profiler-profile-memory",
        default=DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    )
    add_boolean_argument(
        launch,
        "--torch-profiler-with-stack",
        default=DEFAULT_TORCH_PROFILER_WITH_STACK,
    )
    add_boolean_argument(
        launch,
        "--rocm-profiler-enabled",
        default=DEFAULT_ROCM_PROFILER_ENABLED,
    )
    launch.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    launch.add_argument(
        "--resource-monitor-runtime-kind",
        choices=("rocm", "cuda", "none"),
        default=DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    )
    launch.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    launch.add_argument(
        "--disable-resource-monitor",
        action="store_true",
        help="Disable the detached resource-monitor companion launch.",
    )
    launch.add_argument("--launch-id", default=None)
    launch.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    resume = subparsers.add_parser("resume", help="Resume from the latest durable checkpoint.")
    resume.add_argument("resume_mode", nargs="?", choices=["latest"], default="latest")
    resume.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    resume.add_argument("--launch-root", type=Path, default=None)
    resume.add_argument("--checkpoint-path", type=Path, default=None)
    resume.add_argument("--launch-id", default=None)
    resume.add_argument(
        "--resource-monitor-interval-seconds",
        type=float,
        default=DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS,
    )
    resume.add_argument(
        "--resource-monitor-runtime-kind",
        choices=("rocm", "cuda", "none"),
        default=DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND,
    )
    resume.add_argument("--resource-monitor-duration-seconds", type=float, default=None)
    resume.add_argument(
        "--disable-resource-monitor",
        action="store_true",
        help="Disable the detached resource-monitor companion launch.",
    )
    resume.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    status = subparsers.add_parser("status", help="Inspect one detached training launch.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--launch-root", type=Path, default=None)

    stop = subparsers.add_parser("stop", help="Stop one detached training launch intentionally.")
    stop.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    stop.add_argument("--launch-root", type=Path, default=None)

    return parser


def load_training_launch(launch_root_path: Path) -> DetachedLaunch:
    """Load one previously recorded detached training launch payload."""
    return load_launch(
        launch_root_path,
        default_durable_checkpoint_retention=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
        default_durable_checkpoint_min_free_bytes=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
        default_dataloader_num_workers=DEFAULT_DATALOADER_NUM_WORKERS,
        default_dataloader_pin_memory=DEFAULT_DATALOADER_PIN_MEMORY,
        default_dataloader_persistent_workers=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
        default_dataloader_prefetch_factor=DEFAULT_DATALOADER_PREFETCH_FACTOR,
        default_non_blocking_transfer=DEFAULT_NON_BLOCKING_TRANSFER,
        default_data_path_proof_mode=DEFAULT_DATA_PATH_PROOF_MODE,
        default_heartbeat_interval_optimizer_steps=DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
        default_finite_loss_max_consecutive_steps=DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
        default_ref_mel_cache_enabled=DEFAULT_REF_MEL_CACHE_ENABLED,
        default_ref_mel_cache_max_items=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
        default_torch_profiler_enabled=DEFAULT_TORCH_PROFILER_ENABLED,
        default_torch_profiler_wait_steps=DEFAULT_TORCH_PROFILER_WAIT_STEPS,
        default_torch_profiler_warmup_steps=DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
        default_torch_profiler_active_steps=DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
        default_torch_profiler_repeat=DEFAULT_TORCH_PROFILER_REPEAT,
        default_torch_profiler_record_shapes=DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
        default_torch_profiler_profile_memory=DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
        default_torch_profiler_with_stack=DEFAULT_TORCH_PROFILER_WITH_STACK,
        default_rocm_profiler_enabled=DEFAULT_ROCM_PROFILER_ENABLED,
    )


def ensure_training_bundle_exists(
    bundle_root: Path,
    *,
    train_manifest_family: str,
    eval_manifest_family: str,
) -> None:
    """Fail fast when the deterministic training bundle is incomplete."""
    missing_paths = [
        path
        for path in (
            bundle_manifest_path(bundle_root, train_manifest_family),
            bundle_manifest_path(bundle_root, eval_manifest_family),
        )
        if not path.exists()
    ]
    if missing_paths:
        rendered_paths = ", ".join(path.as_posix() for path in missing_paths)
        raise SystemExit(
            "Qwen training could not find the required training-bundle artifacts: "
            f"{rendered_paths}."
        )
    try:
        validate_training_bundle_paths(
            bundle_root,
            (train_manifest_family, eval_manifest_family),
        )
    except ValueError as exc:
        raise SystemExit(
            f"Qwen training bundle integrity check failed before launch.\n{exc}"
        ) from exc
    bundle_report = bundle_report_path(bundle_root)
    if not bundle_report.exists():
        return
    try:
        bundle_summary = load_training_bundle_summary(bundle_root)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(
            f"Qwen training bundle integrity check failed before launch.\n{exc}"
        ) from exc
    if bundle_summary.precomputed_reference_input.kind != "ref_mel":
        raise SystemExit(
            "Qwen training bundle integrity check failed before launch.\n"
            "Unsupported bundle precomputed reference-input kind; expected `ref_mel`."
        )
    if bundle_summary.precomputed_reference_input.artifact_count <= 0:
        raise SystemExit(
            "Qwen training bundle integrity check failed before launch.\n"
            "Training bundle did not report any persisted precomputed reference inputs."
        )
    try:
        validate_training_bundle_paths(
            bundle_root,
            (train_manifest_family, eval_manifest_family),
            require_precomputed_ref_inputs=True,
        )
    except ValueError as exc:
        raise SystemExit(
            f"Qwen training bundle integrity check failed before launch.\n{exc}"
        ) from exc


def validate_training_bundle_paths(
    bundle_root: Path,
    families: tuple[str, str],
    *,
    require_precomputed_ref_inputs: bool = False,
) -> None:
    """Validate that prepared manifests reference existing local bundle assets."""
    for manifest_family in families:
        manifest_path = bundle_manifest_path(bundle_root, manifest_family)
        for row in iter_jsonl_objects(manifest_path):
            if not isinstance(row, dict):
                raise ValueError(
                    f"Prepared manifest row in `{manifest_path}` was not a JSON object."
                )
            for key in ("audio", "ref_audio"):
                _validate_bundle_row_path(bundle_root, manifest_path, row, key, required=True)
            _validate_bundle_row_path(
                bundle_root,
                manifest_path,
                row,
                "precomputed_ref_input_path",
                required=require_precomputed_ref_inputs,
            )
            if require_precomputed_ref_inputs:
                _validate_precomputed_ref_input_contract(manifest_path, row)


def _validate_bundle_row_path(
    bundle_root: Path,
    manifest_path: Path,
    row: dict[str, object],
    key: str,
    *,
    required: bool,
) -> None:
    """Validate one required or optional manifest-relative bundle path field."""
    raw_value = row.get(key)
    if raw_value is None:
        if required:
            raise ValueError(f"Prepared manifest row in `{manifest_path}` lacked `{key}`.")
        return
    raw_paths = _row_path_values(raw_value, key=key, manifest_path=manifest_path)
    for raw_path in raw_paths:
        resolved_path = (bundle_root / raw_path).resolve()
        try:
            resolved_path.relative_to(bundle_root.resolve())
        except ValueError as exc:
            raise ValueError(
                f"Prepared manifest `{key}` escaped the bundle root: {raw_path}"
            ) from exc
        if not resolved_path.exists():
            raise ValueError(
                f"Prepared manifest `{key}` path did not exist: {resolved_path.as_posix()}"
            )


def _row_path_values(
    raw_value: object,
    *,
    key: str,
    manifest_path: Path,
) -> list[str]:
    """Normalize one manifest row path field into concrete string paths."""
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, list):
        values: list[str] = []
        for item in raw_value:
            if not isinstance(item, str):
                raise ValueError(
                    f"Prepared manifest row in `{manifest_path}` had non-string `{key}` entries."
                )
            values.append(item)
        if len(values) == 0:
            raise ValueError(f"Prepared manifest row in `{manifest_path}` had empty `{key}`.")
        return values
    raise ValueError(
        f"Prepared manifest row in `{manifest_path}` had unsupported `{key}` value type."
    )


def _validate_precomputed_ref_input_contract(
    manifest_path: Path,
    row: dict[str, object],
) -> None:
    """Validate the canonical persisted ref-input metadata on one prepared row."""
    kind = row.get("precomputed_ref_input_kind")
    version = row.get("precomputed_ref_input_version")
    source_audio = row.get("precomputed_ref_input_source_audio")
    if kind != PRECOMPUTED_REF_INPUT_KIND:
        raise ValueError(
            f"Prepared manifest row in `{manifest_path}` lacked required "
            f"`precomputed_ref_input_kind={PRECOMPUTED_REF_INPUT_KIND}`."
        )
    if version != PRECOMPUTED_REF_INPUT_VERSION:
        raise ValueError(
            "Prepared manifest row in "
            f"`{manifest_path}` lacked required "
            f"`precomputed_ref_input_version={PRECOMPUTED_REF_INPUT_VERSION}`."
        )
    if not isinstance(source_audio, str) or source_audio.strip() == "":
        raise ValueError(
            f"Prepared manifest row in `{manifest_path}` lacked "
            "`precomputed_ref_input_source_audio`."
        )


def build_settings_from_args(args: argparse.Namespace) -> TrainingSettings:
    """Build one normalized training settings object from parsed launch args."""
    throughput_batch_policy = resolve_throughput_batch_policy(
        profile_label=str(args.throughput_profile_label),
        max_batch_size=int(args.batch_size),
    )
    return TrainingSettings(
        output_root=Path(args.output_root),
        image=str(args.image),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        scratch_build_root=Path(args.scratch_build_root),
        scratch_build_home_mount=Path(args.scratch_build_home_mount),
        pilot_bundle_root=Path(args.pilot_bundle_root),
        runs_root=Path(args.runs_root),
        model_id=str(args.model_id),
        train_manifest_family=str(args.train_manifest_family),
        eval_manifest_family=str(args.eval_manifest_family),
        batch_size=throughput_batch_policy.max_batch_size,
        throughput_profile_label=throughput_batch_policy.profile_label,
        lr=float(args.lr),
        num_epochs=int(args.num_epochs),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        durable_checkpoint_retention=int(args.durable_checkpoint_retention),
        durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
        dataloader_num_workers=int(args.dataloader_num_workers),
        dataloader_pin_memory=bool(args.dataloader_pin_memory),
        dataloader_persistent_workers=bool(args.dataloader_persistent_workers),
        dataloader_prefetch_factor=int(args.dataloader_prefetch_factor),
        non_blocking_transfer=bool(args.non_blocking_transfer),
        data_path_proof_mode=bool(args.data_path_proof_mode),
        heartbeat_interval_optimizer_steps=int(args.heartbeat_interval_optimizer_steps),
        finite_loss_max_consecutive_steps=int(args.finite_loss_max_consecutive_steps),
        ref_mel_cache_enabled=bool(args.ref_mel_cache_enabled),
        ref_mel_cache_max_items=int(args.ref_mel_cache_max_items),
        torch_profiler_enabled=bool(args.torch_profiler_enabled),
        torch_profiler_wait_steps=int(args.torch_profiler_wait_steps),
        torch_profiler_warmup_steps=int(args.torch_profiler_warmup_steps),
        torch_profiler_active_steps=int(args.torch_profiler_active_steps),
        torch_profiler_repeat=int(args.torch_profiler_repeat),
        torch_profiler_record_shapes=bool(args.torch_profiler_record_shapes),
        torch_profiler_profile_memory=bool(args.torch_profiler_profile_memory),
        torch_profiler_with_stack=bool(args.torch_profiler_with_stack),
        rocm_profiler_enabled=bool(args.rocm_profiler_enabled),
    )


def main(argv: list[str] | None = None) -> int:
    """Launch or inspect detached Qwen training on Hemma."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "launch":
        output_root = Path(args.output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        rocm_smi_before = run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi qwen training preflight",
        )
        settings = build_settings_from_args(args)
        ensure_training_bundle_exists(
            settings.pilot_bundle_root,
            train_manifest_family=settings.train_manifest_family,
            eval_manifest_family=settings.eval_manifest_family,
        )
        build_performed, image_id = prepare_qwen_image(
            argparse.Namespace(
                dockerfile_path=Path(args.dockerfile_path),
                image=str(args.image),
                build_image=not bool(args.skip_build),
            )
        )
        hf_mount = resolve_effective_hf_cache_dir(
            argparse.Namespace(
                image=str(args.image),
                hf_cache_dir=Path(args.hf_cache_dir),
                hf_cache_home_mount=Path(args.hf_cache_home_mount),
            )
        )
        scratch_mount = resolve_effective_bind_root(
            settings.scratch_build_root,
            settings.scratch_build_home_mount,
            image=settings.image,
            sync_home_into_canonical=False,
        )
        current_launch_id = str(args.launch_id or default_launch_id())
        current_launch_root = launch_root(output_root, current_launch_id)
        current_launch_root.mkdir(parents=True, exist_ok=True)
        launch = launch_detached_training(
            settings,
            repo_root=Path.cwd(),
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            launch_id=current_launch_id,
            container_name=default_container_name(current_launch_id),
            launch_root=current_launch_root,
            dockerfile_path=Path(args.dockerfile_path),
        )
        resource_monitor = None
        if not bool(args.disable_resource_monitor):
            resource_monitor = launch_resource_monitor(
                training_launch_id=current_launch_id,
                training_launch_root=current_launch_root,
                runtime_kind=args.resource_monitor_runtime_kind,
                interval_seconds=float(args.resource_monitor_interval_seconds),
                duration_seconds=(
                    None
                    if args.resource_monitor_duration_seconds is None
                    else float(args.resource_monitor_duration_seconds)
                ),
            )
            launch = replace(launch, resource_monitor=resource_monitor)
        write_json(
            launch_metadata_path(current_launch_root),
            {
                **asdict(launch),
                "image_id": image_id,
                "build_performed": build_performed,
                "rocm_smi_before": rocm_smi_before,
            },
        )
        write_latest_pointer(output_root, current_launch_root)
        print(json.dumps(asdict(launch), indent=2, ensure_ascii=False))
        return 0

    if args.command == "resume":
        output_root = Path(args.output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        source_launch_root = resolve_launch_root(output_root, args.launch_root)
        source_launch = load_training_launch(source_launch_root)
        settings = settings_from_snapshot(source_launch.settings)
        dockerfile_path = Path(source_launch.dockerfile_path or DEFAULT_DOCKERFILE_PATH)
        build_performed, image_id = prepare_qwen_image(
            argparse.Namespace(
                dockerfile_path=dockerfile_path,
                image=settings.image,
                build_image=not bool(args.skip_build),
            )
        )
        hf_mount = resolve_effective_hf_cache_dir(
            argparse.Namespace(
                image=settings.image,
                hf_cache_dir=settings.hf_cache_dir,
                hf_cache_home_mount=settings.hf_cache_home_mount,
            )
        )
        scratch_mount = resolve_effective_bind_root(
            settings.scratch_build_root,
            settings.scratch_build_home_mount,
            image=settings.image,
            sync_home_into_canonical=False,
        )
        source_run_root = Path(source_launch.run_root)
        resume_checkpoint_candidate = (
            Path(args.checkpoint_path)
            if args.checkpoint_path is not None
            else load_latest_checkpoint(source_run_root)
        )
        resume_checkpoint_path = validate_resume_checkpoint_path(
            source_run_root,
            resume_checkpoint_candidate,
        )
        current_launch_id = str(args.launch_id or default_launch_id())
        current_launch_root = launch_root(output_root, current_launch_id)
        current_launch_root.mkdir(parents=True, exist_ok=True)
        launch = launch_detached_training(
            settings,
            repo_root=Path.cwd(),
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            launch_id=current_launch_id,
            container_name=default_container_name(current_launch_id),
            launch_root=current_launch_root,
            dockerfile_path=dockerfile_path,
            run_root=source_run_root,
            resume_from_checkpoint=resume_checkpoint_path,
        )
        resource_monitor = None
        if not bool(args.disable_resource_monitor):
            resource_monitor = launch_resource_monitor(
                training_launch_id=current_launch_id,
                training_launch_root=current_launch_root,
                runtime_kind=args.resource_monitor_runtime_kind,
                interval_seconds=float(args.resource_monitor_interval_seconds),
                duration_seconds=(
                    None
                    if args.resource_monitor_duration_seconds is None
                    else float(args.resource_monitor_duration_seconds)
                ),
            )
            launch = replace(launch, resource_monitor=resource_monitor)
        write_json(
            launch_metadata_path(current_launch_root),
            {
                **asdict(launch),
                "image_id": image_id,
                "build_performed": build_performed,
                "source_launch_root": source_launch_root.as_posix(),
            },
        )
        write_latest_pointer(output_root, current_launch_root)
        print(json.dumps(asdict(launch), indent=2, ensure_ascii=False))
        return 0

    if args.command == "stop":
        current_launch_root = resolve_launch_root(Path(args.output_root), args.launch_root)
        launch = load_training_launch(current_launch_root)
        stopped = stop_detached_training(launch)
        write_json(stop_metadata_path(current_launch_root), asdict(stopped))
        print(json.dumps(asdict(stopped), indent=2, ensure_ascii=False))
        return 0

    current_launch_root = resolve_launch_root(Path(args.output_root), args.launch_root)
    launch = load_training_launch(current_launch_root)
    status = inspect_detached_training(launch)
    write_json(status_metadata_path(current_launch_root), asdict(status))
    write_markdown(status_markdown_path(current_launch_root), render_status_markdown(status))
    print(json.dumps(asdict(status), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
