"""Launch and inspect the detached Task 101 Qwen Hemma pilot.

Purpose:
    Provide the canonical detached Hemma entrypoint for the first bounded
    Swedish Qwen3-TTS pilot fine-tune so the training lane can continue from
    the completed preprocessing corpus without depending on the client session.

Relationships:
    - Uses `task101_qwen_pilot_runtime.py` for detached Docker launch and
      status inspection.
    - Reuses the shared Task 100 image-build and cache-mount helpers.
    - Consumes the promoted Task 103 corpus view produced by `T108/T114`.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.run_task109_hemma_qwen_containerized_preprocessing import (
    DEFAULT_HF_CACHE,
    DEFAULT_HF_CACHE_HOME_MOUNT,
)
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    ensure_image_present,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime import (
    Task101DetachedLaunch,
    Task101DetachedStatus,
    Task101PilotSettings,
    default_container_name,
    default_launch_id,
    inspect_detached_pilot,
    launch_detached_pilot,
)
from scripts.sir_convert_a_lot.devops.task112_hemma_storage_runtime import (
    DEFAULT_SCRATCH_BUILD_ROOT,
)

DEFAULT_OUTPUT_ROOT = (
    DEFAULT_SCRATCH_BUILD_ROOT / "verification/task-101-qwen3-tts-swedish-hemma-pilot"
)
DEFAULT_RUNS_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "runs/qwen3-tts-swedish-finetune"
DEFAULT_PROMOTED_CORPUS_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "reference/qwen3-tts-swedish-corpus"
DEFAULT_SCRATCH_BUILD_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/build")
DEFAULT_DOCKERFILE_PATH = Path("containers/qwen-finetune-hemma/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:task100"
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DEFAULT_TRAIN_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_BATCH_SIZE = 1
DEFAULT_LR = 2e-5
DEFAULT_NUM_EPOCHS = 1
DEFAULT_MAX_STEPS = 8
LaunchCommand = Literal["launch", "status"]


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
    launch.add_argument("--promoted-corpus-root", type=Path, default=DEFAULT_PROMOTED_CORPUS_ROOT)
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
    launch.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    launch.add_argument("--lr", type=float, default=DEFAULT_LR)
    launch.add_argument("--num-epochs", type=int, default=DEFAULT_NUM_EPOCHS)
    launch.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    launch.add_argument("--launch-id", default=None)
    launch.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` if the image already exists.",
    )

    status = subparsers.add_parser("status", help="Inspect one detached pilot launch.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--launch-root", type=Path, default=None)

    return parser


def _launch_root(output_root: Path, launch_id: str) -> Path:
    """Return the canonical verification root for one launch."""
    return output_root / launch_id


def _launch_metadata_path(launch_root: Path) -> Path:
    """Return the launch metadata path for one detached pilot."""
    return launch_root / "launch.json"


def _status_metadata_path(launch_root: Path) -> Path:
    """Return the status metadata path for one detached pilot."""
    return launch_root / "status.json"


def _status_markdown_path(launch_root: Path) -> Path:
    """Return the markdown status path for one detached pilot."""
    return launch_root / "status.md"


def _latest_pointer_path(output_root: Path) -> Path:
    """Return the pointer file that records the latest pilot launch root."""
    return output_root / "latest-launch.json"


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _status_markdown(status: Task101DetachedStatus) -> str:
    """Render one concise markdown summary for the detached pilot."""
    lines = [
        "# Task 101 Detached Qwen Pilot Status",
        "",
        f"- checked_at: `{status.checked_at}`",
        f"- launch_id: `{status.launch_id}`",
        f"- container_name: `{status.container_name}`",
        f"- container_id: `{status.container_id}`",
        f"- status: `{status.status}`",
        f"- running: `{status.running}`",
        f"- exit_code: `{status.exit_code}`",
        f"- oom_killed: `{status.oom_killed}`",
        f"- started_at: `{status.started_at}`",
        f"- finished_at: `{status.finished_at}`",
        f"- pilot_status_found: `{status.pilot_status_found}`",
        f"- pilot_report_found: `{status.pilot_report_found}`",
        "",
        "## Logs Tail",
        "",
        "```text",
        status.logs_tail,
        "```",
    ]
    if status.pilot_status is not None:
        lines.extend(
            [
                "",
                "## Pilot Status",
                "",
                "```json",
                json.dumps(status.pilot_status, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    if status.pilot_report is not None:
        lines.extend(
            [
                "",
                "## Pilot Report",
                "",
                "```json",
                json.dumps(status.pilot_report, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    return "\n".join(lines)


def _write_latest_pointer(output_root: Path, launch_root: Path) -> None:
    """Record the latest detached pilot launch root for status inspection."""
    _write_json(
        _latest_pointer_path(output_root),
        {"launch_root": launch_root.as_posix()},
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return value


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return list(value)


def _load_launch(launch_root: Path) -> Task101DetachedLaunch:
    """Load one previously recorded detached pilot launch payload."""
    payload = json.loads(_launch_metadata_path(launch_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Detached Task 101 launch metadata was malformed.")
    return Task101DetachedLaunch(
        generated_at=_required_str(payload, "generated_at"),
        launch_id=_required_str(payload, "launch_id"),
        container_name=_required_str(payload, "container_name"),
        container_id=_required_str(payload, "container_id"),
        repo_root=_required_str(payload, "repo_root"),
        run_root=_required_str(payload, "run_root"),
        promoted_corpus_root=_required_str(payload, "promoted_corpus_root"),
        train_manifest_family=_required_str(payload, "train_manifest_family"),
        command=_required_str_list(payload, "command"),
    )


def _resolve_launch_root(output_root: Path, launch_root: Path | None) -> Path:
    """Resolve the launch root for status inspection."""
    if launch_root is not None:
        return launch_root
    pointer_path = _latest_pointer_path(output_root)
    if not pointer_path.exists():
        raise SystemExit(
            "Task 101 status requires `--launch-root` until a launch has recorded "
            "the latest detached pilot pointer."
        )
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Task 101 latest-launch metadata was malformed.")
    return Path(_required_str(payload, "launch_root"))


def _ensure_train_manifest_exists(promoted_corpus_root: Path, manifest_family: str) -> None:
    """Fail fast when the promoted preprocessing corpus lacks the selected family."""
    manifest_path = promoted_corpus_root / "manifests" / f"{manifest_family}.prepared.jsonl"
    if not manifest_path.exists():
        raise SystemExit(
            f"Task 101 pilot could not find the prepared manifest `{manifest_path.as_posix()}`."
        )


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
            promoted_corpus_root=Path(args.promoted_corpus_root),
            runs_root=Path(args.runs_root),
            model_id=str(args.model_id),
            train_manifest_family=str(args.train_manifest_family),
            batch_size=int(args.batch_size),
            lr=float(args.lr),
            num_epochs=int(args.num_epochs),
            max_steps=int(args.max_steps),
        )
        _ensure_train_manifest_exists(
            settings.promoted_corpus_root,
            settings.train_manifest_family,
        )
        build_performed, image_id = ensure_image_present(
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

    launch_root = _resolve_launch_root(Path(args.output_root), args.launch_root)
    launch = _load_launch(launch_root)
    status = inspect_detached_pilot(launch)
    _write_json(_status_metadata_path(launch_root), asdict(status))
    _write_markdown(_status_markdown_path(launch_root), _status_markdown(status))
    print(json.dumps(asdict(status), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
