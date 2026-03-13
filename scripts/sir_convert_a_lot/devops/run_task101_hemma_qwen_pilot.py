"""Launch and inspect the detached Task 101 Qwen Hemma pilot.

Purpose:
    Provide the canonical detached Hemma entrypoint for the first bounded
    Swedish Qwen3-TTS pilot fine-tune so the training lane can continue from
    one deterministic pilot bundle without depending on the client session.

Relationships:
    - Uses `task101_qwen_pilot_runtime.py` for detached Docker launch and
      status inspection.
    - Consumes the deterministic pilot bundle built by
      `task101_qwen_pilot_bundle.py`.
    - Reuses the shared Task 100 image-build and cache-mount helpers.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from scripts.sir_convert_a_lot.devops import task101_qwen_pilot_metadata as metadata
from scripts.sir_convert_a_lot.devops.run_task109_hemma_qwen_containerized_preprocessing import (
    DEFAULT_HF_CACHE,
    DEFAULT_HF_CACHE_HOME_MOUNT,
)
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle import (
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_PILOT_BUNDLE_ROOT,
    task101_pilot_bundle_manifest_path,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_validation import (
    validate_task101_pilot_bundle_paths,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_metadata import (
    _launch_metadata_path,
    _launch_root,
    _load_latest_checkpoint,
    _resolve_launch_root,
    _status_markdown,
    _status_markdown_path,
    _status_metadata_path,
    _stop_metadata_path,
    _validate_resume_checkpoint_path,
    _write_json,
    _write_latest_pointer,
    _write_markdown,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime import (
    inspect_detached_pilot,
    launch_detached_pilot,
    stop_detached_pilot,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime_contract import (
    Task101DetachedLaunch,
    Task101PilotSettings,
    default_container_name,
    default_launch_id,
    settings_from_snapshot,
)
from scripts.sir_convert_a_lot.devops.task112_hemma_storage_runtime import (
    DEFAULT_SCRATCH_BUILD_ROOT,
)

DEFAULT_OUTPUT_ROOT = (
    DEFAULT_SCRATCH_BUILD_ROOT / "verification/task-101-qwen3-tts-swedish-hemma-pilot"
)
DEFAULT_RUNS_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "runs/qwen3-tts-swedish-finetune"
DEFAULT_SCRATCH_BUILD_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/build")
DEFAULT_DOCKERFILE_PATH = Path("containers/qwen-finetune-hemma/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:task100"
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DEFAULT_TRAIN_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_BATCH_SIZE = 1
DEFAULT_LR = 2e-5
DEFAULT_NUM_EPOCHS = 1
DEFAULT_MAX_STEPS = 8
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 2
DEFAULT_DURABLE_CHECKPOINT_RETENTION = 2
DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES = 16 * 1024**3
LaunchCommand = Literal["launch", "resume", "status", "stop"]


def _default_hf_cache_dir() -> Path:
    """Resolve the canonical Hemma Hugging Face cache path for Task 101."""
    configured_path = os.environ.get("SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH")
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE
    return Path(configured_path.strip())


def _default_hf_cache_home_mount() -> Path:
    """Resolve the fallback home-backed Hugging Face cache mount path."""
    configured_path = os.environ.get("SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT")
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE_HOME_MOUNT
    return Path(configured_path.strip())


def _build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for the detached Task 101 pilot."""
    parser = argparse.ArgumentParser(
        description="Launch or inspect the detached Task 101 Qwen pilot."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch the detached pilot training run.")
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    launch.add_argument("--pilot-bundle-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)
    launch.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    launch.add_argument("--image", default=DEFAULT_IMAGE)
    launch.add_argument("--hf-cache-dir", type=Path, default=_default_hf_cache_dir())
    launch.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=_default_hf_cache_home_mount(),
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
        "--durable-checkpoint-retention",
        type=int,
        default=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    )
    launch.add_argument(
        "--durable-checkpoint-min-free-bytes",
        type=int,
        default=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    )
    launch.add_argument("--launch-id", default=None)
    launch.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    resume = subparsers.add_parser(
        "resume",
        help="Resume the detached pilot from the latest durable checkpoint.",
    )
    resume.add_argument("resume_mode", nargs="?", choices=["latest"], default="latest")
    resume.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    resume.add_argument("--launch-root", type=Path, default=None)
    resume.add_argument("--checkpoint-path", type=Path, default=None)
    resume.add_argument("--launch-id", default=None)
    resume.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    status = subparsers.add_parser("status", help="Inspect one detached pilot launch.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--launch-root", type=Path, default=None)

    stop = subparsers.add_parser("stop", help="Stop one detached pilot launch intentionally.")
    stop.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    stop.add_argument("--launch-root", type=Path, default=None)

    return parser


def _load_launch(launch_root: Path) -> Task101DetachedLaunch:
    """Load one previously recorded detached pilot launch payload."""
    return metadata._load_launch(
        launch_root,
        default_durable_checkpoint_retention=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
        default_durable_checkpoint_min_free_bytes=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    )


def _ensure_pilot_bundle_exists(
    pilot_bundle_root: Path,
    *,
    train_manifest_family: str,
    eval_manifest_family: str,
) -> None:
    """Fail fast when the deterministic pilot bundle is incomplete."""
    missing_paths = [
        path
        for path in (
            task101_pilot_bundle_manifest_path(pilot_bundle_root, train_manifest_family),
            task101_pilot_bundle_manifest_path(pilot_bundle_root, eval_manifest_family),
            pilot_bundle_root / "reports" / "task101_pilot_bundle_report.json",
        )
        if not path.exists()
    ]
    if missing_paths:
        rendered_paths = ", ".join(path.as_posix() for path in missing_paths)
        raise SystemExit(
            f"Task 101 pilot could not find the required pilot-bundle artifacts: {rendered_paths}."
        )
    try:
        validate_task101_pilot_bundle_paths(
            pilot_bundle_root,
            (train_manifest_family, eval_manifest_family),
        )
    except ValueError as exc:
        raise SystemExit(
            f"Task 101 pilot bundle integrity check failed before launch.\n{exc}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    """Launch or inspect the detached Task 101 pilot on Hemma."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "launch":
        output_root = Path(args.output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        rocm_smi_before = run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi task101 preflight",
        )
        settings = Task101PilotSettings(
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
            batch_size=int(args.batch_size),
            lr=float(args.lr),
            num_epochs=int(args.num_epochs),
            max_steps=int(args.max_steps),
            checkpoint_interval_steps=int(args.checkpoint_interval_steps),
            durable_checkpoint_retention=int(args.durable_checkpoint_retention),
            durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
        )
        _ensure_pilot_bundle_exists(
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
        launch_id = str(args.launch_id or default_launch_id())
        launch_root = _launch_root(output_root, launch_id)
        launch_root.mkdir(parents=True, exist_ok=True)
        launch = launch_detached_pilot(
            settings,
            repo_root=Path.cwd(),
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            launch_id=launch_id,
            container_name=default_container_name(launch_id),
            launch_root=launch_root,
            dockerfile_path=Path(args.dockerfile_path),
        )
        _write_json(
            _launch_metadata_path(launch_root),
            {
                **asdict(launch),
                "image_id": image_id,
                "build_performed": build_performed,
                "rocm_smi_before": rocm_smi_before,
            },
        )
        _write_latest_pointer(output_root, launch_root)
        print(json.dumps(asdict(launch), indent=2, ensure_ascii=False))
        return 0

    if args.command == "resume":
        output_root = Path(args.output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        source_launch_root = _resolve_launch_root(output_root, args.launch_root)
        source_launch = _load_launch(source_launch_root)
        settings = settings_from_snapshot(source_launch.settings)
        build_performed, image_id = prepare_qwen_image(
            argparse.Namespace(
                dockerfile_path=Path(source_launch.dockerfile_path or DEFAULT_DOCKERFILE_PATH),
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
            else _load_latest_checkpoint(source_run_root)
        )
        resume_checkpoint_path = _validate_resume_checkpoint_path(
            source_run_root,
            resume_checkpoint_candidate,
        )
        launch_id = str(args.launch_id or default_launch_id())
        launch_root = _launch_root(output_root, launch_id)
        launch_root.mkdir(parents=True, exist_ok=True)
        launch = launch_detached_pilot(
            settings,
            repo_root=Path.cwd(),
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            launch_id=launch_id,
            container_name=default_container_name(launch_id),
            launch_root=launch_root,
            dockerfile_path=Path(source_launch.dockerfile_path or DEFAULT_DOCKERFILE_PATH),
            run_root=source_run_root,
            resume_from_checkpoint=resume_checkpoint_path,
        )
        _write_json(
            _launch_metadata_path(launch_root),
            {
                **asdict(launch),
                "image_id": image_id,
                "build_performed": build_performed,
                "source_launch_root": source_launch_root.as_posix(),
            },
        )
        _write_latest_pointer(output_root, launch_root)
        print(json.dumps(asdict(launch), indent=2, ensure_ascii=False))
        return 0

    if args.command == "stop":
        launch_root = _resolve_launch_root(Path(args.output_root), args.launch_root)
        launch = _load_launch(launch_root)
        stopped = stop_detached_pilot(launch)
        _write_json(_stop_metadata_path(launch_root), asdict(stopped))
        print(json.dumps(asdict(stopped), indent=2, ensure_ascii=False))
        return 0

    launch_root = _resolve_launch_root(Path(args.output_root), args.launch_root)
    launch = _load_launch(launch_root)
    status = inspect_detached_pilot(launch)
    _write_json(_status_metadata_path(launch_root), asdict(status))
    _write_markdown(_status_markdown_path(launch_root), _status_markdown(status))
    print(json.dumps(asdict(status), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
