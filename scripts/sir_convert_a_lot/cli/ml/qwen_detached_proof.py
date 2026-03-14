"""Launch and inspect the detached Qwen preprocessing proof on Hemma.

Purpose:
    Provide the committed detached execution surface for the bounded
    public-corpus preprocessing proof so long-running Hemma preprocessing does
    not depend on the local client session remaining attached.

Relationships:
    - Wraps `ml.qwen.preprocessing.detached_proof`.
    - Reuses the canonical containerized preprocessing settings and shared image helpers.
    - Writes deterministic launch/status artifacts under
      `build/verification/qwen-detached-proof/`.
"""

from __future__ import annotations

import argparse
import json
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.cli.ml.qwen_containerized_preprocessing import (
    DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    DEFAULT_DATA_ROOT_HOME_MOUNT,
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_FINALIZATION_FAMILIES,
    DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT,
    DEFAULT_GPU_ASR_WORKER_COUNT,
    DEFAULT_HF_CACHE,
    DEFAULT_HF_CACHE_HOME_MOUNT,
    DEFAULT_IMAGE,
    DEFAULT_ROW_WORKER_COUNT,
    DEFAULT_RUNS_ROOT,
    DEFAULT_SCRATCH_BUILD,
    DEFAULT_SCRATCH_BUILD_HOME_MOUNT,
)
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    ensure_image_present,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.acquisition import (
    default_data_root,
    ensure_bulk_data_storage_path,
    ensure_data_disk_path,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.containerized import (
    ContainerizedPreprocessingSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.detached_proof import (
    DetachedProofLaunch,
    DetachedProofStatus,
    default_container_name,
    inspect_detached_proof,
    launch_detached_proof,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-detached-proof")
DEFAULT_CONTAINER_NAME_PREFIX = "qwen-proof"
DEFAULT_RIXVOX_SPLITS = ("train", "dev", "test")
DEFAULT_RIXVOX_MAX_ROWS_PER_SPLIT = 64


def _parse_shared_settings(args: argparse.Namespace) -> ContainerizedPreprocessingSettings:
    """Convert parsed CLI args into canonical containerized preprocessing settings."""
    return ContainerizedPreprocessingSettings(
        output_root=Path(args.output_root),
        runs_root=Path(args.runs_root),
        run_id=None if args.run_id is None else str(args.run_id),
        run_root=None if args.run_root is None else Path(args.run_root),
        promote_on_success=bool(args.promote_on_success),
        stage="all",
        finalization_families=DEFAULT_FINALIZATION_FAMILIES,
        dockerfile_path=Path(args.dockerfile_path),
        image=str(args.image),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        scratch_build_root=Path(args.scratch_build_root),
        scratch_build_home_mount=Path(args.scratch_build_home_mount),
        data_root=Path(args.data_root),
        data_root_home_mount=Path(args.data_root_home_mount),
        build_image=not bool(args.skip_build),
        fleurs_max_rows_per_split=int(args.fleurs_max_rows_per_split),
        rixvox_splits=tuple(args.rixvox_splits or DEFAULT_RIXVOX_SPLITS),
        rixvox_max_rows_per_split=args.rixvox_max_rows_per_split,
        audio_codes_chunk_size=int(args.audio_codes_chunk_size),
        row_worker_count=int(args.row_worker_count),
        gpu_asr_worker_count=int(args.gpu_asr_worker_count),
        resume_row_processing=False,
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for detached proof workflows."""
    parser = argparse.ArgumentParser(
        description="Launch and inspect the detached Qwen preprocessing proof on Hemma."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch one detached proof container.")
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    launch.add_argument("--run-id", default=None)
    launch.add_argument("--run-root", type=Path, default=None)
    launch.add_argument("--promote-on-success", action="store_true")
    launch.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    launch.add_argument("--image", default=DEFAULT_IMAGE)
    launch.add_argument("--hf-cache-dir", type=Path, default=DEFAULT_HF_CACHE)
    launch.add_argument("--hf-cache-home-mount", type=Path, default=DEFAULT_HF_CACHE_HOME_MOUNT)
    launch.add_argument("--scratch-build-root", type=Path, default=DEFAULT_SCRATCH_BUILD)
    launch.add_argument(
        "--scratch-build-home-mount",
        type=Path,
        default=DEFAULT_SCRATCH_BUILD_HOME_MOUNT,
    )
    launch.add_argument("--data-root", type=Path, default=default_data_root())
    launch.add_argument("--data-root-home-mount", type=Path, default=DEFAULT_DATA_ROOT_HOME_MOUNT)
    launch.add_argument(
        "--fleurs-max-rows-per-split", type=int, default=DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT
    )
    launch.add_argument(
        "--rixvox-split",
        action="append",
        dest="rixvox_splits",
        choices=["train", "dev", "test"],
        default=None,
    )
    launch.add_argument(
        "--rixvox-max-rows-per-split", type=int, default=DEFAULT_RIXVOX_MAX_ROWS_PER_SPLIT
    )
    launch.add_argument(
        "--audio-codes-chunk-size", type=int, default=DEFAULT_AUDIO_CODES_CHUNK_SIZE
    )
    launch.add_argument("--row-worker-count", type=int, default=DEFAULT_ROW_WORKER_COUNT)
    launch.add_argument("--gpu-asr-worker-count", type=int, default=DEFAULT_GPU_ASR_WORKER_COUNT)
    launch.add_argument("--container-name-prefix", default=DEFAULT_CONTAINER_NAME_PREFIX)
    launch.add_argument("--skip-build", action="store_true")

    status = subparsers.add_parser("status", help="Inspect one detached proof container.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--container-name", default=None)
    return parser


def _prepare_output_root(output_root: Path) -> None:
    """Create the deterministic detached-proof output root when needed."""
    output_root.mkdir(parents=True, exist_ok=True)


def _launch_metadata_path(output_root: Path) -> Path:
    """Return the canonical launch metadata path."""
    return output_root / "launch.json"


def _status_metadata_path(output_root: Path) -> Path:
    """Return the canonical status metadata path."""
    return output_root / "status.json"


def _status_markdown_path(output_root: Path) -> Path:
    """Return the canonical status markdown path."""
    return output_root / "status.md"


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload with stable formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one Markdown artifact deterministically."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _status_markdown(status: DetachedProofStatus) -> str:
    """Render one concise Markdown summary for the detached proof."""
    lines = [
        "# Detached Qwen Proof Status",
        "",
        f"- checked_at: `{status.checked_at}`",
        f"- container_name: `{status.container_name}`",
        f"- container_id: `{status.container_id}`",
        f"- status: `{status.status}`",
        f"- running: `{status.running}`",
        f"- exit_code: `{status.exit_code}`",
        f"- oom_killed: `{status.oom_killed}`",
        f"- started_at: `{status.started_at}`",
        f"- finished_at: `{status.finished_at}`",
        f"- report_found: `{status.report_found}`",
        "",
        "## Logs Tail",
        "",
        "```text",
        status.logs_tail,
        "```",
    ]
    if status.report is not None:
        lines.extend(
            [
                "",
                "## Report",
                "",
                "```json",
                json.dumps(status.report, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    return "\n".join(lines)


def _load_launch(output_root: Path) -> DetachedProofLaunch:
    """Load one previously recorded detached-proof launch payload."""
    payload = json.loads(_launch_metadata_path(output_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Detached proof launch metadata was malformed.")
    return DetachedProofLaunch(
        generated_at=_required_str(payload, "generated_at"),
        container_name=_required_str(payload, "container_name"),
        container_id=_required_str(payload, "container_id"),
        repo_root=_required_str(payload, "repo_root"),
        run_root=_required_str(payload, "run_root"),
        promoted_root=_required_str(payload, "promoted_root"),
        command=_required_str_list(payload, "command"),
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Detached proof metadata returned malformed `{key}`.")
    return value


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"Detached proof metadata returned malformed `{key}`.")
    return list(value)


def main(argv: list[str] | None = None) -> int:
    """Launch or inspect the detached bounded preprocessing proof on Hemma."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)
    _prepare_output_root(output_root)

    if args.command == "launch":
        settings = _parse_shared_settings(args)
        ensure_bulk_data_storage_path(settings.data_root, label="data_root")
        ensure_data_disk_path(settings.hf_cache_dir, label="hf_cache_dir")
        if not settings.scratch_build_root.as_posix().startswith("/srv/scratch/"):
            raise SystemExit(
                "scratch_build_root must live on Hemma's SSD scratch tier, got "
                f"`{settings.scratch_build_root.as_posix()}`."
            )
        settings.scratch_build_root.mkdir(parents=True, exist_ok=True)
        repo_root = Path.cwd().resolve()
        run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi qwen detached proof preflight",
        )
        ensure_image_present(settings)
        hf_mount = resolve_effective_hf_cache_dir(settings)
        scratch_mount = resolve_effective_bind_root(
            settings.scratch_build_root,
            settings.scratch_build_home_mount,
            image=settings.image,
            sync_home_into_canonical=False,
        )
        data_mount = resolve_effective_bind_root(
            settings.data_root,
            settings.data_root_home_mount,
            image=settings.image,
            sync_home_into_canonical=False,
        )
        container_name = default_container_name(str(args.container_name_prefix))
        launch = launch_detached_proof(
            settings,
            repo_root=repo_root,
            hf_mount=hf_mount,
            data_mount=data_mount,
            scratch_mount=scratch_mount,
            container_name=container_name,
        )
        _write_json(_launch_metadata_path(output_root), asdict(launch))
        print(json.dumps(asdict(launch), indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.command == "status":
        launch = _load_launch(output_root)
        if args.container_name is not None:
            launch = DetachedProofLaunch(
                generated_at=launch.generated_at,
                container_name=str(args.container_name),
                container_id=launch.container_id,
                repo_root=launch.repo_root,
                run_root=launch.run_root,
                promoted_root=launch.promoted_root,
                command=launch.command,
            )
        status = inspect_detached_proof(launch)
        with suppress(FileNotFoundError):
            _status_metadata_path(output_root).unlink()
        _write_json(_status_metadata_path(output_root), asdict(status))
        _write_markdown(_status_markdown_path(output_root), _status_markdown(status))
        print(json.dumps(asdict(status), indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    raise SystemExit(f"Unsupported detached proof command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
