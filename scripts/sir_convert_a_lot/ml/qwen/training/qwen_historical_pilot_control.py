"""Dedicated historical-control surface for the Qwen pilot training rerun.

Purpose:
    Recreate the documented historical Qwen pilot training launch contract closely enough
    to answer the original-recipe plus token-fix question without silently
    drifting back to the later RCA or benchmark launch posture.

Relationships:
    - Uses `qwen_historical_pilot_control_runtime.py` for the dedicated detached
      Docker launch that mounts the surviving historical bundle directly.
    - Reuses shared detached-training metadata and inspection helpers so the
      resulting launch behaves like the rest of the Qwen lane.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import run_checked
from scripts.sir_convert_a_lot.ml.qwen.common.storage import DEFAULT_SCRATCH_BUILD_ROOT
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.acquisition import (
    ensure_bulk_data_storage_path,
    ensure_data_disk_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_DATALOADER_NUM_WORKERS,
    DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    DEFAULT_DATALOADER_PIN_MEMORY,
    DEFAULT_DATALOADER_PREFETCH_FACTOR,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
    DEFAULT_NON_BLOCKING_TRANSFER,
    DEFAULT_REF_MEL_CACHE_ENABLED,
    DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    DEFAULT_RUNS_ROOT,
    DEFAULT_SCRATCH_BUILD_HOME_MOUNT,
    default_hf_cache_dir,
    default_hf_cache_home_mount,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.inspect_service import (
    inspect_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.stop_service import (
    stop_detached_training,
)
from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    resolve_gradient_accumulation_steps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    latest_pointer_path,
    launch_metadata_path,
    launch_root,
    load_launch,
    render_status_markdown,
    status_markdown_path,
    status_metadata_path,
    stop_metadata_path,
    write_json,
    write_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch, TrainingSettings
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control_contract_diff import (
    DOCUMENTED_HISTORICAL_BUNDLE_ROOT,
    DOCUMENTED_HISTORICAL_EVAL_ROWS,
    DOCUMENTED_HISTORICAL_TRAIN_ROWS,
    build_contract_diff_payload,
    render_contract_diff_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control_runtime import (
    launch_detached_historical_control,
    prepare_runtime_dependencies,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
)
from scripts.sir_convert_a_lot.ml.qwen.training.trainer_runtime_support import count_jsonl_rows

DEFAULT_COMMAND_NAME = "qwen-historical-pilot-control"
DEFAULT_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen-historical-pilot-control"
)
DEFAULT_HISTORICAL_BUNDLE_ROOT = Path(
    "/srv/storage/sir-convert-a-lot/backups/reference/qwen3-tts-swedish-pilot-bundle-20260312h"
)
DEFAULT_HISTORICAL_BUNDLE_HOME_MOUNT = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/reference/qwen3-tts-swedish-pilot-bundle-20260312h"
)
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:historical-control"
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DEFAULT_TRAIN_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_EVAL_MANIFEST_FAMILY = "swedish_checkpoint_dev"
DEFAULT_BATCH_SIZE = 1
DEFAULT_LR = 2e-5
DEFAULT_NUM_EPOCHS = 1000
DEFAULT_MAX_STEPS = 64
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 2
DEFAULT_EVAL_INTERVAL_STEPS = 1_000_000
DEFAULT_DURABLE_CHECKPOINT_RETENTION = 2
DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES = 16 * 1024**3
DEFAULT_THROUGHPUT_PROFILE_LABEL = "hemma-throughput-balanced-v1"


def build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for the historical control lane."""
    parser = argparse.ArgumentParser(
        description="Launch or inspect the historical Qwen pilot training control lane."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch the detached historical control.")
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    launch.add_argument(
        "--historical-bundle-root", type=Path, default=DEFAULT_HISTORICAL_BUNDLE_ROOT
    )
    launch.add_argument(
        "--historical-bundle-home-mount",
        type=Path,
        default=DEFAULT_HISTORICAL_BUNDLE_HOME_MOUNT,
    )
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
    launch.add_argument("--lr", type=float, default=DEFAULT_LR)
    launch.add_argument("--num-epochs", type=int, default=DEFAULT_NUM_EPOCHS)
    launch.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    launch.add_argument(
        "--checkpoint-interval-steps",
        type=int,
        default=DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    )
    launch.add_argument(
        "--eval-interval-steps",
        type=int,
        default=DEFAULT_EVAL_INTERVAL_STEPS,
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
        "--throughput-profile-label",
        default=DEFAULT_THROUGHPUT_PROFILE_LABEL,
    )
    launch.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    )
    launch.add_argument("--launch-id", default=None)

    for command_name, help_text in (
        ("status", "Inspect one detached historical-control launch."),
        ("stop", "Stop one detached historical-control launch intentionally."),
    ):
        command_parser = subparsers.add_parser(command_name, help=help_text)
        command_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
        command_parser.add_argument("--launch-root", type=Path, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Launch, inspect, or stop the committed historical control lane."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "launch":
        launch_id = str(args.launch_id or _default_launch_id())
        current_launch_root = launch_root(Path(args.output_root), launch_id)
        current_launch_root.mkdir(parents=True, exist_ok=False)
        settings = _build_settings_from_args(args)
        _validate_launch_environment(
            settings, historical_bundle_root=Path(args.historical_bundle_root)
        )
        train_rows, eval_rows = _validate_historical_bundle(
            Path(args.historical_bundle_root),
            train_manifest_family=settings.train_manifest_family,
            eval_manifest_family=settings.eval_manifest_family,
        )
        run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi historical control preflight",
        )
        build_performed, image_id, hf_mount, scratch_mount, bundle_mount = (
            prepare_runtime_dependencies(
                settings=settings,
                dockerfile_path=Path(args.dockerfile_path),
                build_image=False,
                historical_bundle_root=Path(args.historical_bundle_root),
                historical_bundle_home_mount=Path(args.historical_bundle_home_mount),
            )
        )
        contract_payload = build_contract_diff_payload(
            launch_id=launch_id,
            settings=settings,
            build_performed=build_performed,
            image_id=image_id,
            historical_bundle_root=Path(args.historical_bundle_root),
            historical_bundle_home_mount=Path(args.historical_bundle_home_mount),
            bundle_mount=bundle_mount,
            train_rows=train_rows,
            eval_rows=eval_rows,
            model_id=DEFAULT_MODEL_ID,
            documented_batch_size=DEFAULT_BATCH_SIZE,
            documented_lr=DEFAULT_LR,
            documented_num_epochs=DEFAULT_NUM_EPOCHS,
            documented_checkpoint_interval_steps=DEFAULT_CHECKPOINT_INTERVAL_STEPS,
            documented_durable_checkpoint_retention=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
            documented_durable_checkpoint_min_free_bytes=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
            image=DEFAULT_IMAGE,
            train_manifest_family=DEFAULT_TRAIN_MANIFEST_FAMILY,
            eval_manifest_family=DEFAULT_EVAL_MANIFEST_FAMILY,
        )
        write_json(current_launch_root / "contract-diff.json", contract_payload)
        write_markdown(
            current_launch_root / "contract-diff.md",
            render_contract_diff_markdown(contract_payload),
        )
        launch = launch_detached_historical_control(
            settings,
            repo_root=Path.cwd().resolve(),
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            bundle_mount=bundle_mount,
            launch_id=launch_id,
            container_name=f"{launch_id}-container",
            launch_root=current_launch_root,
            dockerfile_path=Path(args.dockerfile_path),
            documented_bundle_root=DOCUMENTED_HISTORICAL_BUNDLE_ROOT,
            historical_bundle_home_mount=Path(args.historical_bundle_home_mount),
        )
        write_json(launch_metadata_path(current_launch_root), asdict(launch))
        write_json(
            latest_pointer_path(Path(args.output_root)),
            {"launch_root": current_launch_root.as_posix()},
        )
        print(
            json.dumps(
                {"launch": asdict(launch), "contract_diff": contract_payload},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    current_launch_root = _resolve_launch_root(
        output_root=Path(args.output_root),
        requested_launch_root=args.launch_root,
    )
    launch = _load_launch(current_launch_root)
    if args.command == "status":
        status = inspect_detached_training(launch)
        write_json(status_metadata_path(current_launch_root), asdict(status))
        write_markdown(status_markdown_path(current_launch_root), render_status_markdown(status))
        print(json.dumps(asdict(status), indent=2, ensure_ascii=False))
        return 0
    stop_result = stop_detached_training(launch)
    write_json(stop_metadata_path(current_launch_root), asdict(stop_result))
    print(json.dumps(asdict(stop_result), indent=2, ensure_ascii=False))
    return 0


def _build_settings_from_args(args: argparse.Namespace) -> TrainingSettings:
    """Build the bounded historical-control training settings from parsed CLI arguments."""
    return TrainingSettings(
        output_root=Path(args.output_root),
        image=str(args.image),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        scratch_build_root=Path(args.scratch_build_root),
        scratch_build_home_mount=Path(args.scratch_build_home_mount),
        pilot_bundle_root=Path(args.historical_bundle_root),
        runs_root=Path(args.runs_root),
        model_id=str(args.model_id),
        train_manifest_family=str(args.train_manifest_family),
        eval_manifest_family=str(args.eval_manifest_family),
        batch_size=int(args.batch_size),
        throughput_profile_label=str(args.throughput_profile_label),
        lr=float(args.lr),
        num_epochs=int(args.num_epochs),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        eval_interval_steps=int(args.eval_interval_steps),
        durable_checkpoint_retention=int(args.durable_checkpoint_retention),
        durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
        gradient_accumulation_steps=resolve_gradient_accumulation_steps(
            int(args.gradient_accumulation_steps),
            default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
        ),
        dataloader_num_workers=DEFAULT_DATALOADER_NUM_WORKERS,
        dataloader_pin_memory=DEFAULT_DATALOADER_PIN_MEMORY,
        dataloader_persistent_workers=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
        dataloader_prefetch_factor=DEFAULT_DATALOADER_PREFETCH_FACTOR,
        non_blocking_transfer=DEFAULT_NON_BLOCKING_TRANSFER,
        heartbeat_interval_optimizer_steps=DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
        finite_loss_max_consecutive_steps=DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
        ref_mel_cache_enabled=DEFAULT_REF_MEL_CACHE_ENABLED,
        ref_mel_cache_max_items=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
        text_embedding_assembly_mode=FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE,
        text_embedding_mask_policy=TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
    )


def _validate_launch_environment(
    settings: TrainingSettings, *, historical_bundle_root: Path
) -> None:
    """Fail fast when historical-control paths drift off the intended Hemma storage tiers."""
    ensure_bulk_data_storage_path(historical_bundle_root, label="historical_bundle_root")
    ensure_data_disk_path(settings.hf_cache_dir, label="hf_cache_dir")
    if not settings.scratch_build_root.as_posix().startswith("/srv/scratch/"):
        raise SystemExit(
            "scratch_build_root must live on Hemma's SSD scratch tier, got "
            f"`{settings.scratch_build_root.as_posix()}`."
        )
    settings.scratch_build_root.mkdir(parents=True, exist_ok=True)


def _validate_historical_bundle(
    historical_bundle_root: Path,
    *,
    train_manifest_family: str,
    eval_manifest_family: str,
) -> tuple[int, int]:
    """Require the surviving historical bundle layout and documented row counts."""
    train_manifest = (
        historical_bundle_root / "manifests" / f"{train_manifest_family}.prepared.jsonl"
    )
    eval_manifest = historical_bundle_root / "manifests" / f"{eval_manifest_family}.prepared.jsonl"
    if not train_manifest.is_file() or not eval_manifest.is_file():
        raise SystemExit(
            "Historical control could not find the required historical manifests under "
            f"`{historical_bundle_root.as_posix()}`."
        )
    train_rows = count_jsonl_rows(train_manifest)
    eval_rows = count_jsonl_rows(eval_manifest)
    if (
        train_rows != DOCUMENTED_HISTORICAL_TRAIN_ROWS
        or eval_rows != DOCUMENTED_HISTORICAL_EVAL_ROWS
    ):
        raise SystemExit(
            "Historical bundle row counts drifted from the documented Qwen contract: "
            f"train_rows={train_rows} expected_train_rows={DOCUMENTED_HISTORICAL_TRAIN_ROWS} "
            f"eval_rows={eval_rows} expected_eval_rows={DOCUMENTED_HISTORICAL_EVAL_ROWS}."
        )
    return train_rows, eval_rows


def _resolve_launch_root(*, output_root: Path, requested_launch_root: Path | None) -> Path:
    """Resolve the selected launch root, falling back to the latest pointer."""
    if requested_launch_root is not None:
        return requested_launch_root
    pointer_path = latest_pointer_path(output_root)
    if not pointer_path.is_file():
        raise SystemExit(
            "Historical-control status/stop requires --launch-root or a latest-launch pointer."
        )
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Historical-control latest-launch metadata was malformed.")
    launch_root_value = payload.get("launch_root")
    if not isinstance(launch_root_value, str):
        raise SystemExit("Historical-control latest-launch metadata lacked `launch_root`.")
    return Path(launch_root_value)


def _load_launch(current_launch_root: Path) -> DetachedLaunch:
    """Load one previously recorded detached launch payload for historical control."""
    return load_launch(
        current_launch_root,
        default_throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        default_legacy_small_batch_throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        default_durable_checkpoint_retention=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
        default_durable_checkpoint_min_free_bytes=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
        default_dataloader_num_workers=DEFAULT_DATALOADER_NUM_WORKERS,
        default_dataloader_pin_memory=DEFAULT_DATALOADER_PIN_MEMORY,
        default_dataloader_persistent_workers=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
        default_dataloader_prefetch_factor=DEFAULT_DATALOADER_PREFETCH_FACTOR,
        default_non_blocking_transfer=DEFAULT_NON_BLOCKING_TRANSFER,
        default_data_path_proof_mode=False,
        default_heartbeat_interval_optimizer_steps=DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
        default_eval_interval_steps=DEFAULT_EVAL_INTERVAL_STEPS,
        default_finite_loss_max_consecutive_steps=DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
        default_ref_mel_cache_enabled=DEFAULT_REF_MEL_CACHE_ENABLED,
        default_ref_mel_cache_max_items=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
        default_torch_profiler_enabled=False,
        default_torch_profiler_wait_steps=1,
        default_torch_profiler_warmup_steps=1,
        default_torch_profiler_active_steps=4,
        default_torch_profiler_repeat=1,
        default_torch_profiler_record_shapes=True,
        default_torch_profiler_profile_memory=True,
        default_torch_profiler_with_stack=False,
        default_rocm_profiler_enabled=False,
    )


def _default_launch_id() -> str:
    """Return the canonical launch id for one historical-control run."""
    from datetime import UTC, datetime

    return f"qwen-historical-control-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"
