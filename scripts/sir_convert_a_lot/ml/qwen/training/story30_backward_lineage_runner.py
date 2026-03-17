"""Host-side Hemma proof runner for the Story 30 backward-lineage probe.

Purpose:
    Materialize the exact fresh-start row-pair mini-bundle, execute the
    in-container backward-lineage probe on the governed Qwen ROCm runtime, and
    persist deterministic report artifacts for T212.

Relationships:
    - Reuses `ml.qwen.common.runtime` for image and HF-cache setup.
    - Executes `backward_lineage_probe.py` inside the Qwen training image.
    - Used by the detached T212 worker and the public proof surface.
"""

from __future__ import annotations

import argparse
import shutil
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    docker_checked,
    parse_json_object_from_mixed_stdout,
    prepare_qwen_image,
    resolve_effective_hf_cache_dir,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso, write_json
from scripts.sir_convert_a_lot.ml.qwen.training.smoke import (
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_IMAGE,
    DEFAULT_MODEL_ID,
    default_hf_cache_dir,
    default_hf_cache_home_mount,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_bundle import (
    BackwardLineageMiniBundle,
    materialize_backward_lineage_bundle,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-story30-backward-lineage-proof")
DEFAULT_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_SOURCE_LINES = (13, 4)


@dataclass(frozen=True)
class BackwardLineageProofSettings:
    """Configuration for one host-side backward-lineage proof run."""

    output_root: Path
    dockerfile_path: Path
    image: str
    model_id: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    source_bundle_root: Path
    manifest_family: str
    source_lines: tuple[int, int]
    text_embedding_mask_policy: str
    build_image: bool


@dataclass(frozen=True)
class BackwardLineageProofReport:
    """Deterministic report contract for one T212 backward-lineage proof."""

    generated_at: str
    image: str
    image_id: str
    build_performed: bool
    model_id: str
    source_bundle_root: str
    mini_bundle: dict[str, object]
    hf_cache_dir: str
    effective_hf_cache_dir: str
    used_home_mount: bool
    probe_command: list[str]
    probe_result: dict[str, object]


@dataclass(frozen=True)
class _RunnerImageSettings:
    """Concrete image settings payload for the host-side backward-lineage runner."""

    dockerfile_path: Path
    image: str
    build_image: bool


@dataclass(frozen=True)
class _RunnerCacheSettings:
    """Concrete HF cache settings payload for the host-side backward-lineage runner."""

    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path


def parse_args(argv: list[str] | None) -> BackwardLineageProofSettings:
    """Parse CLI args into normalized backward-lineage proof settings."""
    parser = argparse.ArgumentParser(description="Run the Story 30 backward-lineage proof.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    parser.add_argument("--hf-cache-home-mount", type=Path, default=default_hf_cache_home_mount())
    parser.add_argument("--source-bundle-root", type=Path, required=True)
    parser.add_argument("--manifest-family", default=DEFAULT_MANIFEST_FAMILY)
    parser.add_argument(
        "--source-lines", default=",".join(str(value) for value in DEFAULT_SOURCE_LINES)
    )
    parser.add_argument("--text-embedding-mask-policy", default="text_span_only")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)
    return BackwardLineageProofSettings(
        output_root=Path(args.output_root),
        dockerfile_path=Path(args.dockerfile_path),
        image=str(args.image),
        model_id=str(args.model_id),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        source_bundle_root=Path(args.source_bundle_root),
        manifest_family=str(args.manifest_family),
        source_lines=_parse_source_lines(str(args.source_lines)),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        build_image=not bool(args.skip_build),
    )


def _parse_source_lines(raw_value: str) -> tuple[int, int]:
    """Parse the canonical two-row source-line tuple."""
    pieces = [piece.strip() for piece in raw_value.split(",") if piece.strip() != ""]
    if len(pieces) != 2:
        raise SystemExit("Backward-lineage proof requires exactly two source lines.")
    return int(pieces[0]), int(pieces[1])


def prepare_output_root(output_root: Path) -> tuple[Path, Path, Path]:
    """Create a clean deterministic output tree for the current proof run."""
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    failure_path = output_root / "failure.txt"
    for generated_path in (report_json_path, report_md_path, failure_path):
        with suppress(FileNotFoundError):
            generated_path.unlink()
    shutil.rmtree(_mini_bundle_root(output_root), ignore_errors=True)
    return report_json_path, report_md_path, failure_path


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _image_settings(settings: BackwardLineageProofSettings) -> _RunnerImageSettings:
    """Build the shared image settings payload for the proof runtime."""
    return _RunnerImageSettings(
        dockerfile_path=settings.dockerfile_path,
        image=settings.image,
        build_image=settings.build_image,
    )


def _hf_mount(settings: BackwardLineageProofSettings) -> MountResolution:
    """Resolve the Docker-visible HF cache mount for the probe runtime."""
    return resolve_effective_hf_cache_dir(
        _RunnerCacheSettings(
            image=settings.image,
            hf_cache_dir=settings.hf_cache_dir,
            hf_cache_home_mount=settings.hf_cache_home_mount,
        )
    )


def _mini_bundle_root(output_root: Path) -> Path:
    """Return the canonical mini-bundle root for one proof run."""
    return output_root / "mini-bundle"


def build_probe_command(
    settings: BackwardLineageProofSettings,
    *,
    hf_mount: MountResolution,
    mini_bundle: BackwardLineageMiniBundle,
) -> list[str]:
    """Build the Docker command that runs the in-container backward-lineage probe."""
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
        "-v",
        f"{mini_bundle.bundle_root}:/probe/bundle:ro",
        "--entrypoint",
        "python",
        settings.image,
        "-m",
        "scripts.sir_convert_a_lot.ml.qwen.training.backward_lineage_probe",
        "--model-id",
        settings.model_id,
        "--train-jsonl",
        "/probe/bundle/manifests/sweden_unused".replace(
            "sweden_unused", f"{mini_bundle.manifest_family}.prepared.jsonl"
        ),
        "--text-embedding-mask-policy",
        settings.text_embedding_mask_policy,
        "--source-lines",
        ",".join(str(line) for line in settings.source_lines),
    ]


def run_backward_lineage_probe(
    settings: BackwardLineageProofSettings,
    *,
    hf_mount: MountResolution,
    mini_bundle: BackwardLineageMiniBundle,
) -> tuple[dict[str, object], list[str]]:
    """Run the in-container backward-lineage probe and parse its JSON payload."""
    command = build_probe_command(settings, hf_mount=hf_mount, mini_bundle=mini_bundle)
    output = docker_checked(command, label="docker run qwen backward-lineage probe")
    payload = parse_json_object_from_mixed_stdout(output)
    return payload, ["sudo", "-n", "docker", *command]


def build_report_markdown(report: BackwardLineageProofReport) -> str:
    """Render one concise markdown summary for the T212 backward-lineage proof."""
    lines = [
        "# Story 30 Backward-Lineage Proof",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Image: `{report.image}`",
        f"- Image id: `{report.image_id}`",
        f"- Build performed: `{report.build_performed}`",
        f"- Model id: `{report.model_id}`",
        f"- Source bundle root: `{report.source_bundle_root}`",
        f"- Canonical HF cache: `{report.hf_cache_dir}`",
        f"- Effective HF cache mount: `{report.effective_hf_cache_dir}`",
        f"- Used home-backed bind mount: `{report.used_home_mount}`",
        f"- Probe command: `{' '.join(report.probe_command)}`",
        "",
        "## Mini Bundle",
        "",
        f"- Manifest: `{report.mini_bundle['manifest_path']}`",
        f"- Source lines: `{report.mini_bundle['selected_source_lines']}`",
    ]
    branch_summaries = report.probe_result.get("branch_summaries")
    if isinstance(branch_summaries, list):
        lines.extend(["", "## Branch Summaries", ""])
        for summary in branch_summaries:
            if not isinstance(summary, dict):
                continue
            lines.append(
                "- "
                f"`{summary.get('loss_kind')}`: pair=`{summary.get('pair_has_non_finite')}` "
                f"first_row=`{summary.get('first_row_has_non_finite')}` "
                f"second_row=`{summary.get('second_row_has_non_finite')}` "
                f"interaction=`{summary.get('interaction_mode')}`"
            )
    return "\n".join(lines)


def run_proof(settings: BackwardLineageProofSettings) -> BackwardLineageProofReport:
    """Run the full host-side backward-lineage proof and return its report."""
    prepare_output_root(settings.output_root)
    build_performed, image_id = prepare_qwen_image(_image_settings(settings))
    hf_mount = _hf_mount(settings)
    mini_bundle = materialize_backward_lineage_bundle(
        source_bundle_root=settings.source_bundle_root,
        target_bundle_root=_mini_bundle_root(settings.output_root),
        manifest_family=settings.manifest_family,
        selected_source_lines=settings.source_lines,
    )
    probe_result, probe_command = run_backward_lineage_probe(
        settings,
        hf_mount=hf_mount,
        mini_bundle=mini_bundle,
    )
    return BackwardLineageProofReport(
        generated_at=utc_now_iso(),
        image=settings.image,
        image_id=image_id,
        build_performed=build_performed,
        model_id=settings.model_id,
        source_bundle_root=settings.source_bundle_root.as_posix(),
        mini_bundle=asdict(mini_bundle),
        hf_cache_dir=settings.hf_cache_dir.as_posix(),
        effective_hf_cache_dir=hf_mount.effective_root.as_posix(),
        used_home_mount=hf_mount.used_home_mount,
        probe_command=probe_command,
        probe_result=probe_result,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the host-side T212 proof and persist deterministic report artifacts."""
    settings = parse_args(argv)
    report_json_path, report_md_path, failure_path = prepare_output_root(settings.output_root)
    try:
        report = run_proof(settings)
    except Exception as exc:
        failure_path.write_text(
            f"Story 30 backward-lineage proof failed: {exc}\n", encoding="utf-8"
        )
        raise
    write_json(report_json_path, asdict(report))
    write_markdown(report_md_path, build_report_markdown(report))
    print(asdict(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
