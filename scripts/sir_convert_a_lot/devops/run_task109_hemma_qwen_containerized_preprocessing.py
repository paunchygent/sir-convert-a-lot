"""Run Task 109 containerized public-corpus preprocessing on Hemma.

Purpose:
    Provide the canonical wrapper-driven Hemma entrypoint that runs the staged
    public-corpus Qwen preprocessing lane inside the dedicated Qwen container
    runtime instead of the Hemma host virtualenv.

Relationships:
    - Uses `task109_qwen_containerized_preprocessing_runtime.py`.
    - Reuses Task 100 image-build and mount-resolution helpers.
    - Writes deterministic remediation evidence under
      `build/verification/task-109-qwen-containerized-preprocessing/`.
"""

from __future__ import annotations

import argparse
import json
import os
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    MountResolution,
    ensure_image_present,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    default_data_root,
    ensure_data_disk_path,
)
from scripts.sir_convert_a_lot.devops.task109_qwen_containerized_preprocessing_runtime import (
    ContainerizedPreprocessingRun,
    Task109ContainerizedPreprocessingSettings,
    run_containerized_preprocessing,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-109-qwen-containerized-preprocessing")
DEFAULT_DOCKERFILE_PATH = Path("containers/qwen-finetune-hemma/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:task100"
DEFAULT_HEMMA_HF_CACHE_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH"
DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT"
DEFAULT_HEMMA_DATA_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_QWEN_CORPUS_DATA_HOME_MOUNT"
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_DATA_ROOT_HOME_MOUNT = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"
)
DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT = 8


@dataclass(frozen=True)
class Task109ContainerizedReport:
    """Deterministic report contract for Task 109 remediation runs."""

    generated_at: str
    image: str
    image_id: str
    build_performed: bool
    repo_root: str
    hf_cache_dir: str
    effective_hf_cache_dir: str
    used_hf_home_mount: bool
    data_root: str
    effective_data_root: str
    used_data_home_mount: bool
    fleurs_max_rows_per_split: int
    command: list[str]
    preprocessing_report: dict[str, object]
    rocm_smi_before: str


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_hf_cache_dir() -> Path:
    """Resolve the canonical Hemma Hugging Face cache path for Task 109."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE
    return Path(configured_path.strip())


def _default_hf_cache_home_mount() -> Path:
    """Resolve the fallback home-backed Hugging Face cache mount path."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE_HOME_MOUNT
    return Path(configured_path.strip())


def _default_data_root_home_mount() -> Path:
    """Resolve the fallback home-backed DATA-root mount path."""
    configured_path = os.environ.get(DEFAULT_HEMMA_DATA_HOME_MOUNT_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_DATA_ROOT_HOME_MOUNT
    return Path(configured_path.strip())


def _parse_args(argv: list[str] | None) -> Task109ContainerizedPreprocessingSettings:
    """Parse CLI arguments into normalized Task 109 settings."""
    parser = argparse.ArgumentParser(
        description="Run Task 109 containerized Qwen public-corpus preprocessing on Hemma."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--hf-cache-dir", type=Path, default=_default_hf_cache_dir())
    parser.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=_default_hf_cache_home_mount(),
    )
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument(
        "--data-root-home-mount",
        type=Path,
        default=_default_data_root_home_mount(),
    )
    parser.add_argument(
        "--fleurs-max-rows-per-split",
        type=int,
        default=DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT,
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` when the image already exists locally.",
    )
    args = parser.parse_args(argv)
    return Task109ContainerizedPreprocessingSettings(
        output_root=Path(args.output_root),
        dockerfile_path=Path(args.dockerfile_path),
        image=str(args.image),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        data_root=Path(args.data_root),
        data_root_home_mount=Path(args.data_root_home_mount),
        build_image=not bool(args.skip_build),
        fleurs_max_rows_per_split=int(args.fleurs_max_rows_per_split),
    )


def _prepare_output_root(output_root: Path) -> tuple[Path, Path, Path]:
    """Create a clean deterministic output tree for the current Task 109 run."""
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    failure_path = output_root / "failure.txt"
    for generated_path in (report_json_path, report_md_path, failure_path):
        with suppress(FileNotFoundError):
            generated_path.unlink()
    return report_json_path, report_md_path, failure_path


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload with stable formatting."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_report_markdown(
    report: Task109ContainerizedReport,
    *,
    hf_mount: MountResolution,
    data_mount: MountResolution,
) -> str:
    """Render one concise Markdown summary for the Task 109 run."""
    command_text = " ".join(report.command)
    inner_report = report.preprocessing_report
    return (
        "# Task 109 Containerized Qwen Public-Corpus Preprocessing Report\n\n"
        f"- Generated at: `{report.generated_at}`\n"
        f"- Image: `{report.image}`\n"
        f"- Image id: `{report.image_id}`\n"
        f"- Build performed: `{report.build_performed}`\n"
        f"- Repo root: `{report.repo_root}`\n"
        f"- HF cache canonical root: `{report.hf_cache_dir}`\n"
        f"- HF cache effective root: `{report.effective_hf_cache_dir}`\n"
        f"- Used HF home-backed bind mount: `{report.used_hf_home_mount}`\n"
        f"- DATA canonical root: `{report.data_root}`\n"
        f"- DATA effective root: `{report.effective_data_root}`\n"
        f"- Used DATA home-backed bind mount: `{report.used_data_home_mount}`\n"
        f"- FLEURS max rows per split: `{report.fleurs_max_rows_per_split}`\n"
        f"- Command: `{command_text}`\n"
        f"- Inner output root: `{inner_report['output_root']}`\n"
        f"- Inventory rows: `{inner_report['inventory_rows']}`\n"
        f"- Curated rows: `{inner_report['curated_rows']}`\n"
        f"- Admitted rows: `{inner_report['admitted_rows']}`\n"
        f"- Prepared rows: `{inner_report['prepared_rows']}`\n"
        "\n## Mounts\n\n"
        f"- HF canonical root: `{hf_mount.canonical_root}`\n"
        f"- HF effective root: `{hf_mount.effective_root}`\n"
        f"- DATA canonical root: `{data_mount.canonical_root}`\n"
        f"- DATA effective root: `{data_mount.effective_root}`\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Run Task 109 containerized preprocessing and write deterministic evidence."""
    settings = _parse_args(argv)
    report_json_path, report_md_path, failure_path = _prepare_output_root(settings.output_root)
    enforce_generated_output_path(report_json_path, label="report_json_path")
    enforce_generated_output_path(report_md_path, label="report_md_path")
    enforce_generated_output_path(failure_path, label="failure_path")
    ensure_data_disk_path(settings.data_root, label="data_root")
    ensure_data_disk_path(settings.hf_cache_dir, label="hf_cache_dir")

    try:
        rocm_smi_before = run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi task109 preflight",
        )
        repo_root = Path.cwd().resolve()
        build_performed, image_id = ensure_image_present(settings)
        hf_mount = resolve_effective_hf_cache_dir(settings)
        data_mount = resolve_effective_bind_root(
            settings.data_root,
            settings.data_root_home_mount,
            image=settings.image,
            sync_home_into_canonical=False,
        )
        preprocessing_run: ContainerizedPreprocessingRun = run_containerized_preprocessing(
            settings,
            repo_root=repo_root,
            hf_mount=hf_mount,
            data_mount=data_mount,
        )
        report = Task109ContainerizedReport(
            generated_at=_utc_now_iso(),
            image=settings.image,
            image_id=image_id,
            build_performed=build_performed,
            repo_root=repo_root.as_posix(),
            hf_cache_dir=settings.hf_cache_dir.as_posix(),
            effective_hf_cache_dir=hf_mount.effective_root.as_posix(),
            used_hf_home_mount=hf_mount.used_home_mount,
            data_root=settings.data_root.as_posix(),
            effective_data_root=data_mount.effective_root.as_posix(),
            used_data_home_mount=data_mount.used_home_mount,
            fleurs_max_rows_per_split=settings.fleurs_max_rows_per_split,
            command=preprocessing_run.command,
            preprocessing_report=asdict(preprocessing_run.preprocessing_report),
            rocm_smi_before=rocm_smi_before,
        )
        _write_json(report_json_path, asdict(report))
        report_md_path.write_text(
            _build_report_markdown(report, hf_mount=hf_mount, data_mount=data_mount) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except SystemExit as exc:
        failure_path.write_text(str(exc) + "\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
