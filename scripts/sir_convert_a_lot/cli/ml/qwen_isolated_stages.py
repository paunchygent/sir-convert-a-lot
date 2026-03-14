"""Launch detached isolated Qwen preprocessing stages on Hemma.

Purpose:
    Provide the canonical Hemma entrypoint for isolated preprocessing stages so
    public-corpus Qwen preprocessing runs row-processing, finalization, and
    reports in separate fresh containers instead of one long-lived GPU-backed
    process.

Relationships:
    - Uses `ml.qwen.preprocessing.isolated_stages` for detached launch and inspection helpers.
    - Reuses containerized preprocessing settings, image build, and mount resolution.
    - Writes deterministic launch/status artifacts under
      `build/verification/qwen-isolated-stages/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal

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
    _parse_manifest_families,
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
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.isolated_stages import (
    DetachedStageLaunch,
    DetachedStageStatus,
    DetachedStageStop,
    default_container_name,
    default_launch_id,
    inspect_detached_stage,
    launch_detached_stage,
    resolve_next_stage,
    stop_detached_stage,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import PreprocessingStage

DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-isolated-stages")
StageSelector = Literal["auto", "source-selection", "row-processing", "finalization", "reports"]


def _build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for isolated stage orchestration."""
    parser = argparse.ArgumentParser(
        description="Launch detached isolated Qwen preprocessing stages on Hemma."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch one detached isolated stage.")
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    launch.add_argument("--run-id", default=None)
    launch.add_argument("--run-root", type=Path, default=None)
    launch.add_argument(
        "--stage",
        choices=("auto", "source-selection", "row-processing", "finalization", "reports"),
        default="auto",
    )
    launch.add_argument("--finalization-families", default=",".join(DEFAULT_FINALIZATION_FAMILIES))
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
    launch.add_argument("--rixvox-max-rows-per-split", type=int, default=64)
    launch.add_argument(
        "--audio-codes-chunk-size", type=int, default=DEFAULT_AUDIO_CODES_CHUNK_SIZE
    )
    launch.add_argument("--row-worker-count", type=int, default=DEFAULT_ROW_WORKER_COUNT)
    launch.add_argument("--gpu-asr-worker-count", type=int, default=DEFAULT_GPU_ASR_WORKER_COUNT)
    launch.add_argument("--resume-row-processing", action="store_true")
    launch.add_argument("--launch-id", default=None)
    launch.add_argument("--skip-build", action="store_true")

    status = subparsers.add_parser("status", help="Inspect one detached isolated stage launch.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--launch-root", type=Path, default=None)

    stop = subparsers.add_parser("stop", help="Stop one detached isolated stage launch.")
    stop.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    stop.add_argument("--launch-root", type=Path, default=None)
    return parser


def _prepare_output_root(output_root: Path) -> None:
    """Create the deterministic isolated-stage output root when needed."""
    output_root.mkdir(parents=True, exist_ok=True)


def _launch_root(base_output_root: Path, launch_id: str) -> Path:
    """Return the canonical artifact directory for one launch."""
    return base_output_root / launch_id


def _launch_metadata_path(launch_root: Path) -> Path:
    """Return the launch metadata path for one launch root."""
    return launch_root / "launch.json"


def _status_metadata_path(launch_root: Path) -> Path:
    """Return the status metadata path for one launch root."""
    return launch_root / "status.json"


def _status_markdown_path(launch_root: Path) -> Path:
    """Return the markdown status path for one launch root."""
    return launch_root / "status.md"


def _stop_metadata_path(launch_root: Path) -> Path:
    """Return the stop metadata path for one launch root."""
    return launch_root / "stop.json"


def _latest_pointer_path(output_root: Path) -> Path:
    """Return the pointer file that records the latest launch root."""
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


def _status_markdown(status: DetachedStageStatus) -> str:
    """Render one concise markdown summary for a detached isolated stage."""
    lines = [
        "# Detached Qwen Isolated Stage Status",
        "",
        f"- checked_at: `{status.checked_at}`",
        f"- launch_id: `{status.launch_id}`",
        f"- stage: `{status.stage}`",
        f"- container_name: `{status.container_name}`",
        f"- container_id: `{status.container_id}`",
        f"- status: `{status.status}`",
        f"- running: `{status.running}`",
        f"- exit_code: `{status.exit_code}`",
        f"- oom_killed: `{status.oom_killed}`",
        f"- started_at: `{status.started_at}`",
        f"- finished_at: `{status.finished_at}`",
        f"- status_found: `{status.status_found}`",
        f"- report_found: `{status.report_found}`",
        "",
        "## Logs Tail",
        "",
        "```text",
        status.logs_tail,
        "```",
    ]
    if status.stage_status is not None:
        lines.extend(
            [
                "",
                "## Stage Status",
                "",
                "```json",
                json.dumps(status.stage_status, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
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


def _resolve_launch_root(*, output_root: Path, requested_launch_root: Path | None) -> Path:
    """Resolve one launch root from explicit input or the latest pointer."""
    if requested_launch_root is not None:
        return requested_launch_root
    pointer_payload = json.loads(_latest_pointer_path(output_root).read_text(encoding="utf-8"))
    if not isinstance(pointer_payload, dict):
        raise SystemExit("Latest launch pointer was malformed.")
    return Path(_required_str(pointer_payload, "launch_root"))


def _resolve_stage_selector(stage_selector: StageSelector, *, run_root: Path) -> PreprocessingStage:
    """Resolve the effective preprocessing stage for one launch request."""
    if stage_selector == "source-selection":
        return "source-selection"
    if stage_selector == "row-processing":
        return "row-processing"
    if stage_selector == "finalization":
        return "finalization"
    if stage_selector == "reports":
        return "reports"
    resolved = resolve_next_stage(run_root=run_root)
    if resolved is None:
        raise SystemExit(f"Run root `{run_root.as_posix()}` already has a completed report.")
    return resolved


def _required_stage_selector(value: object) -> StageSelector:
    """Narrow one CLI stage-selector value to the canonical literal type."""
    if value == "auto":
        return "auto"
    if value == "source-selection":
        return "source-selection"
    if value == "row-processing":
        return "row-processing"
    if value == "finalization":
        return "finalization"
    if value == "reports":
        return "reports"
    raise SystemExit("Detached isolated-stage CLI received an unknown `--stage` value.")


def _build_settings(
    args: argparse.Namespace,
    *,
    stage: PreprocessingStage,
) -> ContainerizedPreprocessingSettings:
    """Build containerized preprocessing settings for one isolated stage launch."""
    promote_on_success = bool(args.promote_on_success)
    if promote_on_success and stage != "reports":
        raise SystemExit("`--promote-on-success` is only allowed for the reports stage.")
    if bool(args.resume_row_processing) and stage != "row-processing":
        raise SystemExit("`--resume-row-processing` is only valid for the row-processing stage.")
    return ContainerizedPreprocessingSettings(
        output_root=Path(args.output_root),
        runs_root=Path(args.runs_root),
        run_id=None if args.run_id is None else str(args.run_id),
        run_root=None if args.run_root is None else Path(args.run_root),
        promote_on_success=promote_on_success,
        stage=stage,
        finalization_families=_parse_manifest_families(str(args.finalization_families)),
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
        rixvox_splits=tuple(args.rixvox_splits or ("train", "dev", "test")),
        rixvox_max_rows_per_split=args.rixvox_max_rows_per_split,
        audio_codes_chunk_size=int(args.audio_codes_chunk_size),
        row_worker_count=int(args.row_worker_count),
        gpu_asr_worker_count=int(args.gpu_asr_worker_count),
        resume_row_processing=bool(args.resume_row_processing),
    )


def _load_launch(launch_root: Path) -> DetachedStageLaunch:
    """Load one previously recorded detached stage launch payload."""
    payload = json.loads(_launch_metadata_path(launch_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Detached isolated-stage launch metadata was malformed.")
    return DetachedStageLaunch(
        generated_at=_required_str(payload, "generated_at"),
        launch_id=_required_str(payload, "launch_id"),
        stage=_required_stage(payload, "stage"),
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
        raise SystemExit(f"Detached isolated-stage metadata returned malformed `{key}`.")
    return value


def _required_stage(payload: dict[str, object], key: str) -> PreprocessingStage:
    """Return one required stage value from a JSON payload."""
    value = payload.get(key)
    if value == "all":
        return "all"
    if value == "source-selection":
        return "source-selection"
    if value == "row-processing":
        return "row-processing"
    if value == "finalization":
        return "finalization"
    if value == "reports":
        return "reports"
    raise SystemExit(f"Detached isolated-stage metadata returned malformed `{key}`.")


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"Detached isolated-stage metadata returned malformed `{key}`.")
    return list(value)


def main(argv: list[str] | None = None) -> int:
    """Launch or inspect detached isolated Qwen preprocessing stages on Hemma."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)
    _prepare_output_root(output_root)

    if args.command == "launch":
        requested_run_root = (
            Path(args.run_root)
            if args.run_root is not None
            else Path(args.runs_root) / (str(args.run_id) if args.run_id is not None else "")
        )
        if args.run_root is None and args.run_id is None and args.stage != "row-processing":
            effective_run_root = Path(args.runs_root) / "auto"
        else:
            effective_run_root = requested_run_root
        requested_stage = _required_stage_selector(args.stage)
        stage: PreprocessingStage
        if requested_stage == "auto":
            if args.run_root is None and args.run_id is None:
                stage = "source-selection"
            else:
                stage = _resolve_stage_selector("auto", run_root=effective_run_root)
        else:
            stage = _resolve_stage_selector(requested_stage, run_root=effective_run_root)

        settings = _build_settings(args, stage=stage)
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
            label="rocm-smi qwen isolated stage preflight",
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
        launch_id = str(args.launch_id or default_launch_id(stage))
        launch_root = _launch_root(output_root, launch_id)
        container_name = default_container_name(launch_id)
        launch = launch_detached_stage(
            settings,
            repo_root=repo_root,
            hf_mount=hf_mount,
            data_mount=data_mount,
            scratch_mount=scratch_mount,
            launch_id=launch_id,
            container_name=container_name,
        )
        _write_json(_launch_metadata_path(launch_root), asdict(launch))
        _write_json(_latest_pointer_path(output_root), {"launch_root": launch_root.as_posix()})
        print(json.dumps(asdict(launch), indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.command == "status":
        launch_root = _resolve_launch_root(
            output_root=output_root, requested_launch_root=args.launch_root
        )
        launch = _load_launch(launch_root)
        status = inspect_detached_stage(launch)
        _write_json(_status_metadata_path(launch_root), asdict(status))
        _write_markdown(_status_markdown_path(launch_root), _status_markdown(status))
        print(json.dumps(asdict(status), indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.command == "stop":
        launch_root = _resolve_launch_root(
            output_root=output_root, requested_launch_root=args.launch_root
        )
        launch = _load_launch(launch_root)
        stop_result: DetachedStageStop = stop_detached_stage(launch)
        _write_json(_stop_metadata_path(launch_root), asdict(stop_result))
        print(json.dumps(asdict(stop_result), indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    raise SystemExit(f"Unsupported isolated stage command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
