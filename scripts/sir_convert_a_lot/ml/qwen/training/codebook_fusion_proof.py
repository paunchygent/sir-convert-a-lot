"""Host-side Hemma proof runner for Qwen codebook-fusion proof codebook-fusion decisions.

Purpose:
    Reuse the governed Qwen ROCm image/build/smoke posture, execute the
    in-container codebook-fusion probe, and persist deterministic proof
    artifacts for the Qwen fallback proof lane hot-path decision.

Relationships:
    - Reuses `ml.qwen.common.runtime` for image, Docker, and smoke execution.
    - Executes `codebook_fusion_probe.py` inside the Qwen training image.
    - Exposed through the public `qwen-codebook-fusion-proof` CLI entrypoint.
"""

from __future__ import annotations

import argparse
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    SmokeProbeResult,
    SmokeSettings,
    docker_checked,
    parse_json_object_from_mixed_stdout,
    prepare_qwen_image,
    resolve_effective_hf_cache_dir,
    run_checked,
    run_smoke_probe,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso, write_json
from scripts.sir_convert_a_lot.ml.qwen.training.smoke import (
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_IMAGE,
    DEFAULT_MODEL_ID,
    default_hf_cache_dir,
    default_hf_cache_home_mount,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-codebook-fusion-proof")


@dataclass(frozen=True)
class CodebookFusionProofSettings(SmokeSettings):
    """Configuration for one host-side codebook-fusion proof run."""

    batch_size: int
    sequence_length: int
    codebook_count: int
    embedding_dim: int
    benchmark_iterations: int
    warmup_iterations: int
    dtype_names: tuple[str, ...]
    seeds: tuple[int, ...]
    build_image: bool


@dataclass(frozen=True)
class CodebookFusionProofReport:
    """Deterministic report contract for one Qwen codebook-fusion proof proof run."""

    generated_at: str
    image: str
    image_id: str
    build_performed: bool
    model_id: str
    hf_cache_dir: str
    effective_hf_cache_dir: str
    used_home_mount: bool
    smoke_probe_result: SmokeProbeResult
    smoke_probe_command: list[str]
    probe_command: list[str]
    probe_result: dict[str, object]
    rocm_smi_before: str
    rocminfo: str


def _parse_dtype_names(raw_value: str) -> tuple[str, ...]:
    """Parse one comma-delimited list of probe dtypes."""
    names = [item.strip().lower() for item in raw_value.split(",") if item.strip() != ""]
    if len(names) == 0:
        raise argparse.ArgumentTypeError("Expected at least one dtype name.")
    canonical_names: list[str] = []
    for name in names:
        if name in {"bf16", "bfloat16"}:
            canonical_name = "bfloat16"
        elif name in {"fp16", "float16"}:
            canonical_name = "float16"
        else:
            raise argparse.ArgumentTypeError(
                "Supported dtypes are `bfloat16`/`bf16` and `float16`/`fp16`."
            )
        if canonical_name not in canonical_names:
            canonical_names.append(canonical_name)
    return tuple(canonical_names)


def _parse_seeds(raw_value: str) -> tuple[int, ...]:
    """Parse one comma-delimited seed list."""
    seeds = [item.strip() for item in raw_value.split(",") if item.strip() != ""]
    if len(seeds) == 0:
        raise argparse.ArgumentTypeError("Expected at least one integer seed.")
    return tuple(int(seed) for seed in seeds)


def parse_args(argv: list[str] | None) -> CodebookFusionProofSettings:
    """Parse CLI arguments into normalized proof settings."""
    parser = argparse.ArgumentParser(
        description="Run the Qwen codebook-fusion proof codebook-fusion proof on Hemma."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    parser.add_argument("--hf-cache-home-mount", type=Path, default=default_hf_cache_home_mount())
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--sequence-length", type=int, default=508)
    parser.add_argument("--codebook-count", type=int, default=15)
    parser.add_argument("--embedding-dim", type=int, default=2048)
    parser.add_argument("--benchmark-iterations", type=int, default=25)
    parser.add_argument("--warmup-iterations", type=int, default=10)
    parser.add_argument("--dtypes", type=_parse_dtype_names, default=("bfloat16", "float16"))
    parser.add_argument("--seeds", type=_parse_seeds, default=(0, 1, 2))
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `docker buildx build` when the image already exists locally on Hemma.",
    )
    args = parser.parse_args(argv)
    return CodebookFusionProofSettings(
        output_root=Path(args.output_root),
        dockerfile_path=Path(args.dockerfile_path),
        image=str(args.image),
        model_id=str(args.model_id),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        batch_size=int(args.batch_size),
        sequence_length=int(args.sequence_length),
        codebook_count=int(args.codebook_count),
        embedding_dim=int(args.embedding_dim),
        benchmark_iterations=int(args.benchmark_iterations),
        warmup_iterations=int(args.warmup_iterations),
        dtype_names=args.dtypes,
        seeds=args.seeds,
        build_image=not bool(args.skip_build),
    )


def prepare_output_root(output_root: Path) -> tuple[Path, Path, Path]:
    """Create a clean deterministic output tree for the current proof run."""
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    failure_path = output_root / "failure.txt"
    for generated_path in (report_json_path, report_md_path, failure_path):
        with suppress(FileNotFoundError):
            generated_path.unlink()
    return report_json_path, report_md_path, failure_path


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def build_codebook_fusion_probe_command(
    settings: CodebookFusionProofSettings,
    *,
    hf_mount: MountResolution,
) -> list[str]:
    """Build the Docker command that runs the in-container codebook-fusion probe."""
    return [
        "run",
        "--rm",
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
        "-e",
        f"SIR_QWEN_TRAINING_HF_CACHE_HOST_ROOT={hf_mount.canonical_root.as_posix()}",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
        "--entrypoint",
        "python",
        settings.image,
        "-m",
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_probe",
        "--batch-size",
        str(settings.batch_size),
        "--sequence-length",
        str(settings.sequence_length),
        "--codebook-count",
        str(settings.codebook_count),
        "--embedding-dim",
        str(settings.embedding_dim),
        "--benchmark-iterations",
        str(settings.benchmark_iterations),
        "--warmup-iterations",
        str(settings.warmup_iterations),
        "--dtypes",
        ",".join(settings.dtype_names),
        "--seeds",
        ",".join(str(seed) for seed in settings.seeds),
    ]


def run_codebook_fusion_probe(
    settings: CodebookFusionProofSettings,
    *,
    hf_mount: MountResolution,
) -> tuple[dict[str, object], list[str]]:
    """Run the in-container codebook-fusion probe and parse its JSON payload."""
    command = build_codebook_fusion_probe_command(settings, hf_mount=hf_mount)
    output = docker_checked(command, label="docker run qwen codebook fusion probe")
    payload = parse_json_object_from_mixed_stdout(output)
    return payload, ["sudo", "-n", "docker", *command]


def build_report_markdown(report: CodebookFusionProofReport) -> str:
    """Render one concise markdown summary for the Qwen codebook-fusion proof proof."""
    lines = [
        "# Qwen Codebook Fusion Proof",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Image: `{report.image}`",
        f"- Image id: `{report.image_id}`",
        f"- Build performed: `{report.build_performed}`",
        f"- Model id: `{report.model_id}`",
        f"- Canonical HF cache: `{report.hf_cache_dir}`",
        f"- Effective HF cache mount: `{report.effective_hf_cache_dir}`",
        f"- Used home-backed bind mount: `{report.used_home_mount}`",
        f"- Smoke command: `{' '.join(report.smoke_probe_command)}`",
        f"- Probe command: `{' '.join(report.probe_command)}`",
        f"- Runtime available: `{report.smoke_probe_result.torch_cuda_available}`",
        f"- Device count: `{report.smoke_probe_result.torch_cuda_device_count}`",
        f"- ROCm HIP version: `{report.smoke_probe_result.torch_hip_version}`",
    ]
    dtype_summaries = report.probe_result.get("dtype_summaries")
    if isinstance(dtype_summaries, list):
        lines.append("")
        lines.append("## Dtype Summaries")
        lines.append("")
        for summary in dtype_summaries:
            if not isinstance(summary, dict):
                continue
            dtype_name = summary.get("dtype")
            naive_runtime = summary.get("naive_mean_runtime_ms")
            candidate_runtime = summary.get("candidate_mean_runtime_ms")
            candidate_ratio = summary.get("candidate_runtime_ratio_vs_naive")
            naive_error = summary.get("naive_worst_max_abs_error")
            candidate_error = summary.get("candidate_worst_max_abs_error")
            candidate_better = summary.get("candidate_error_better_or_equal_all_seeds")
            lines.extend(
                [
                    f"- dtype: `{dtype_name}`",
                    f"  - naive_mean_runtime_ms: `{naive_runtime}`",
                    f"  - candidate_mean_runtime_ms: `{candidate_runtime}`",
                    f"  - candidate_runtime_ratio_vs_naive: `{candidate_ratio}`",
                    f"  - naive_worst_max_abs_error: `{naive_error}`",
                    f"  - candidate_worst_max_abs_error: `{candidate_error}`",
                    f"  - candidate_error_better_or_equal_all_seeds: `{candidate_better}`",
                ]
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the Qwen codebook-fusion proof proof and write deterministic artifacts."""
    settings = parse_args(argv)
    report_json_path, report_md_path, failure_path = prepare_output_root(settings.output_root)
    enforce_generated_output_path(report_json_path, label="report_json_path")
    enforce_generated_output_path(report_md_path, label="report_md_path")
    enforce_generated_output_path(failure_path, label="failure_path")

    try:
        rocm_smi_before = run_checked(
            ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showpids"],
            label="rocm-smi codebook fusion proof preflight",
        )
        rocminfo_output = run_checked(
            ["rocminfo"],
            label="rocminfo codebook fusion proof preflight",
        )
        build_performed, image_id = prepare_qwen_image(settings)
        hf_mount = resolve_effective_hf_cache_dir(settings)
        smoke_probe_result, smoke_probe_command = run_smoke_probe(settings, hf_mount=hf_mount)
        probe_result, probe_command = run_codebook_fusion_probe(settings, hf_mount=hf_mount)
        report = CodebookFusionProofReport(
            generated_at=utc_now_iso(),
            image=settings.image,
            image_id=image_id,
            build_performed=build_performed,
            model_id=settings.model_id,
            hf_cache_dir=settings.hf_cache_dir.as_posix(),
            effective_hf_cache_dir=hf_mount.effective_root.as_posix(),
            used_home_mount=hf_mount.used_home_mount,
            smoke_probe_result=smoke_probe_result,
            smoke_probe_command=smoke_probe_command,
            probe_command=probe_command,
            probe_result=probe_result,
            rocm_smi_before=rocm_smi_before,
            rocminfo=rocminfo_output,
        )
        write_json(report_json_path, asdict(report))
        write_markdown(report_md_path, build_report_markdown(report))
        return 0
    except SystemExit as exc:
        failure_path.write_text(str(exc) + "\n", encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
