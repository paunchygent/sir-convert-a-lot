"""Run the Task 100 Qwen fine-tuning image smoke command on Hemma.

Purpose:
    Build the dedicated Qwen fine-tuning image with BuildKit, verify that it
    can mount the canonical Hugging Face cache on Hemma, and run one
    in-container probe against the `Qwen/Qwen3-TTS-12Hz-1.7B-Base` Hub id.

Relationships:
    - Intended to run on Hemma via `pdm run run-hemma -- pdm run task-100-smoke`.
    - Uses the Task 100 training image under `containers/qwen-finetune-hemma/`.
    - Writes deterministic evidence under
      `build/verification/task-100-qwen-finetune-smoke/`.
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
    SmokeProbeResult,
    Task100SmokeSettings,
    ensure_image_present,
    resolve_effective_hf_cache_dir,
    run_checked,
    run_smoke_probe,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-100-qwen-finetune-smoke")
DEFAULT_DOCKERFILE_PATH = Path("containers/qwen-finetune-hemma/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:task100"
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DEFAULT_HEMMA_HF_CACHE_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH"
DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT"
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")


@dataclass(frozen=True)
class Task100SmokeReport:
    """Deterministic report contract for the Task 100 smoke run."""

    generated_at: str
    image: str
    image_id: str
    build_performed: bool
    model_id: str
    hf_cache_dir: str
    effective_hf_cache_dir: str
    used_home_mount: bool
    smoke_probe_command: list[str]
    smoke_probe_result: SmokeProbeResult
    rocm_smi_before: str
    rocminfo: str


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_hf_cache_dir() -> Path:
    """Resolve the canonical Hemma Hugging Face cache path for Task 100."""
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


def _parse_args(argv: list[str] | None) -> Task100SmokeSettings:
    """Parse CLI arguments into normalized Task 100 smoke settings."""
    parser = argparse.ArgumentParser(description="Run the Task 100 Qwen fine-tune smoke on Hemma.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--hf-cache-dir",
        type=Path,
        default=_default_hf_cache_dir(),
    )
    parser.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=_default_hf_cache_home_mount(),
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` when the image already exists locally.",
    )
    args = parser.parse_args(argv)
    return Task100SmokeSettings(
        output_root=Path(args.output_root),
        dockerfile_path=Path(args.dockerfile_path),
        image=str(args.image),
        model_id=str(args.model_id),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        build_image=not bool(args.skip_build),
    )


def _prepare_output_root(output_root: Path) -> tuple[Path, Path, Path]:
    """Create a clean deterministic output tree for the current smoke run."""
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
    report: Task100SmokeReport,
    *,
    hf_mount: MountResolution,
) -> str:
    """Render one concise Markdown summary for the Task 100 smoke run."""
    command_text = " ".join(report.smoke_probe_command)
    return (
        "# Task 100 Qwen Fine-Tune Smoke Report\n\n"
        f"- Generated at: `{report.generated_at}`\n"
        f"- Image: `{report.image}`\n"
        f"- Image id: `{report.image_id}`\n"
        f"- Build performed: `{report.build_performed}`\n"
        f"- Model id: `{report.model_id}`\n"
        f"- Canonical HF cache: `{report.hf_cache_dir}`\n"
        f"- Effective HF cache mount: `{report.effective_hf_cache_dir}`\n"
        f"- Used home-backed bind mount: `{report.used_home_mount}`\n"
        f"- Probe command: `{command_text}`\n"
        f"- Resolved model path: `{report.smoke_probe_result.resolved_model_path}`\n"
        f"- Resolved config path: `{report.smoke_probe_result.resolved_config_path}`\n"
        f"- Resolved `tts_model_type`: `{report.smoke_probe_result.tts_model_type}`\n"
        f"- Torch version: `{report.smoke_probe_result.torch_version}`\n"
        f"- Torchaudio version: `{report.smoke_probe_result.torchaudio_version}`\n"
        f"- `torch.cuda.is_available()`: `{report.smoke_probe_result.torch_cuda_available}`\n"
        f"- CUDA device count: `{report.smoke_probe_result.torch_cuda_device_count}`\n"
        f"- ROCm HIP version: `{report.smoke_probe_result.torch_hip_version}`\n"
        f"- `flash_attn` importable: `{report.smoke_probe_result.flash_attn_importable}`\n"
        f"- `flash_attn` version: `{report.smoke_probe_result.flash_attn_version}`\n"
        f"- Flash-attn model init ok: `{report.smoke_probe_result.flash_attn_model_load_ok}`\n"
        "\n## Dependency Versions\n\n"
        + "\n".join(
            f"- `{name}`: `{version}`"
            for name, version in sorted(report.smoke_probe_result.dependency_versions.items())
        )
        + "\n\n## Cache Mount\n\n"
        f"- Canonical root: `{hf_mount.canonical_root}`\n"
        f"- Effective root: `{hf_mount.effective_root}`\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Run the Task 100 smoke command and write deterministic evidence."""
    settings = _parse_args(argv)
    report_json_path, report_md_path, failure_path = _prepare_output_root(settings.output_root)
    enforce_generated_output_path(report_json_path, label="report_json_path")
    enforce_generated_output_path(report_md_path, label="report_md_path")
    enforce_generated_output_path(failure_path, label="failure_path")

    try:
        rocm_smi_before = run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi task100 preflight",
        )
        rocminfo_output = run_checked(["rocminfo"], label="rocminfo task100 preflight")
        build_performed, image_id = ensure_image_present(settings)
        hf_mount = resolve_effective_hf_cache_dir(settings)
        smoke_probe_result, smoke_probe_command = run_smoke_probe(settings, hf_mount=hf_mount)
        report = Task100SmokeReport(
            generated_at=_utc_now_iso(),
            image=settings.image,
            image_id=image_id,
            build_performed=build_performed,
            model_id=settings.model_id,
            hf_cache_dir=settings.hf_cache_dir.as_posix(),
            effective_hf_cache_dir=hf_mount.effective_root.as_posix(),
            used_home_mount=hf_mount.used_home_mount,
            smoke_probe_command=smoke_probe_command,
            smoke_probe_result=smoke_probe_result,
            rocm_smi_before=rocm_smi_before,
            rocminfo=rocminfo_output,
        )
        _write_json(report_json_path, asdict(report))
        report_md_path.write_text(
            _build_report_markdown(report, hf_mount=hf_mount) + "\n",
            encoding="utf-8",
        )
        return 0
    except SystemExit as exc:
        failure_path.write_text(str(exc) + "\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
