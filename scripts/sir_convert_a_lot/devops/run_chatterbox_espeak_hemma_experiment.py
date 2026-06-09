"""Run the Chatterbox eSpeak experiment Chatterbox eSpeak experiment on Hemma.

Purpose:
    Build the bounded eSpeak helper image, generate one phonemized Swedish text
    artifact, run baseline-vs-phonemized Chatterbox lanes on Hemma, and write a
    deterministic experiment summary.

Relationships:
    - Reuses the existing Chatterbox benchmark runner for the actual Chatterbox
      synthesis lanes.
    - Keeps eSpeak preprocessing outside the Chatterbox sidecar contract.
    - Intended to be invoked on Hemma through the local Chatterbox eSpeak experiment orchestrator.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops import run_chatterbox_hemma_benchmark
from scripts.sir_convert_a_lot.devops.openvoice_benchmark_runtime import docker_checked

LOGGER = logging.getLogger(__name__)
DEFAULT_OUTPUT_ROOT = Path("build/verification/chatterbox-espeak-hemma")
DEFAULT_HELPER_DOCKERFILE = Path("containers/textprep-espeak-phonemizer/Dockerfile")
DEFAULT_HELPER_IMAGE = "sir-convert-a-lot/textprep-espeak-chatterbox-espeak:local"
DEFAULT_REFERENCE_AUDIO = Path(
    "build/verification/openvoice-v2-hemma/inputs/teacher_reference_voice.m4a"
)
DEFAULT_PROBE_TEXT = (
    "Hej. Det här är ett rent svenskt prov. Vi testar om modellen kan klona en "
    "lärarröst och läsa svensk text tydligt, naturligt och utan störande "
    "artefakter."
)


@dataclass(frozen=True)
class ExperimentSettings:
    """Normalized CLI settings for the Chatterbox eSpeak experiment Hemma experiment."""

    output_root: Path
    helper_dockerfile: Path
    helper_image: str
    reference_audio_path: Path
    probe_text: str
    espeak_language: str
    preserve_punctuation: bool
    build_helper_image: bool
    build_chatterbox_image: bool


@dataclass(frozen=True)
class LaneSummary:
    """One summarized lane outcome for the Chatterbox eSpeak experiment report."""

    lane_id: str
    output_root: str
    synthesized_ok: bool | None
    output_path: str | None
    duration_seconds: float | None
    sha256: str | None
    peak_vram_used_bytes: int | None
    exaggeration: float | None
    cfg_weight: float | None


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_args(argv: list[str]) -> ExperimentSettings:
    """Parse CLI arguments into normalized Chatterbox eSpeak experiment settings."""
    parser = argparse.ArgumentParser(
        description="Run the Chatterbox eSpeak experiment Hemma eSpeak experiment."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--helper-dockerfile", type=Path, default=DEFAULT_HELPER_DOCKERFILE)
    parser.add_argument("--helper-image", default=DEFAULT_HELPER_IMAGE)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--probe-text", default=DEFAULT_PROBE_TEXT)
    parser.add_argument("--espeak-language", default="sv")
    parser.add_argument("--preserve-punctuation", action="store_true", default=True)
    parser.add_argument(
        "--no-preserve-punctuation", dest="preserve_punctuation", action="store_false"
    )
    parser.add_argument("--skip-helper-build", action="store_true")
    parser.add_argument("--build-benchmark-image", action="store_true")
    args = parser.parse_args(argv)
    return ExperimentSettings(
        output_root=Path(args.output_root),
        helper_dockerfile=Path(args.helper_dockerfile),
        helper_image=str(args.helper_image),
        reference_audio_path=Path(args.reference_audio),
        probe_text=str(args.probe_text),
        espeak_language=str(args.espeak_language),
        preserve_punctuation=bool(args.preserve_punctuation),
        build_helper_image=not bool(args.skip_helper_build),
        build_chatterbox_image=bool(args.build_benchmark_image),
    )


def _prepare_output_root(output_root: Path) -> dict[str, Path]:
    """Create a clean deterministic output tree for Chatterbox eSpeak experiment."""
    output_root.mkdir(parents=True, exist_ok=True)
    inputs_dir = output_root / "inputs"
    baseline_dir = output_root / "baseline"
    espeak_dir = output_root / "espeak_sv"
    for directory in (inputs_dir, baseline_dir, espeak_dir):
        directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "inputs_dir": inputs_dir,
        "baseline_dir": baseline_dir,
        "espeak_dir": espeak_dir,
        "report_json": output_root / "report.json",
        "report_md": output_root / "report.md",
        "original_text": inputs_dir / "probe_text_original.txt",
        "phoneme_text": inputs_dir / "probe_text_espeak_sv.txt",
        "phoneme_metadata": inputs_dir / "espeak_metadata.json",
    }
    for path in (
        paths["report_json"],
        paths["report_md"],
        paths["original_text"],
        paths["phoneme_text"],
        paths["phoneme_metadata"],
    ):
        with suppress(FileNotFoundError):
            path.unlink()
    return paths


def _ensure_helper_image(settings: ExperimentSettings) -> tuple[bool, str]:
    """Build the helper image with BuildKit when needed and return the image id."""
    image_present = True
    try:
        image_id = docker_checked(
            ["image", "inspect", settings.helper_image, "--format", "{{.Id}}"],
            label="docker image inspect chatterbox-espeak helper",
        )
    except SystemExit:
        image_present = False
        image_id = ""
    build_performed = settings.build_helper_image or not image_present
    if build_performed:
        docker_checked(
            ["buildx", "version"], label="docker buildx version chatterbox-espeak helper"
        )
        docker_checked(
            [
                "buildx",
                "build",
                "--load",
                "-t",
                settings.helper_image,
                "-f",
                settings.helper_dockerfile.resolve().as_posix(),
                ".",
            ],
            label="docker buildx build chatterbox-espeak helper image",
        )
        image_id = docker_checked(
            ["image", "inspect", settings.helper_image, "--format", "{{.Id}}"],
            label="docker image inspect chatterbox-espeak helper after build",
        )
    return build_performed, image_id.strip()


def _run_phonemizer(
    settings: ExperimentSettings,
    *,
    input_text_path: Path,
    output_text_path: Path,
    metadata_path: Path,
) -> None:
    """Run the dedicated helper container to generate one phonemized text artifact."""
    mount_root = input_text_path.parent.resolve()
    command = [
        "run",
        "--rm",
        "-v",
        f"{mount_root.as_posix()}:/workspace",
        settings.helper_image,
        "--input-file",
        f"/workspace/{input_text_path.name}",
        "--output-file",
        f"/workspace/{output_text_path.name}",
        "--metadata-file",
        f"/workspace/{metadata_path.name}",
        "--language",
        settings.espeak_language,
    ]
    if settings.preserve_punctuation:
        command.append("--preserve-punctuation")
    else:
        command.append("--no-preserve-punctuation")
    docker_checked(command, label="docker run chatterbox-espeak helper")


def _run_chatterbox_benchmark_lane(
    *,
    lane_output_root: Path,
    reference_audio_path: Path,
    probe_text_file: Path,
    exaggeration: float,
    cfg_weight: float,
    build_chatterbox_image: bool,
) -> int:
    """Execute one Chatterbox benchmark lane in-process on Hemma."""
    argv = [
        "--output-root",
        lane_output_root.as_posix(),
        "--reference-audio",
        reference_audio_path.as_posix(),
        "--probe-text-file",
        probe_text_file.as_posix(),
        "--exaggeration",
        str(exaggeration),
        "--cfg-weight",
        str(cfg_weight),
    ]
    if not build_chatterbox_image:
        argv.append("--skip-build")
    return run_chatterbox_hemma_benchmark.main(argv)


def _load_lane_summary(lane_id: str, output_root: Path) -> LaneSummary:
    """Load one Chatterbox benchmark report into the Chatterbox eSpeak experiment summary shape."""
    report_path = output_root / "report.json"
    if not report_path.exists():
        return LaneSummary(
            lane_id=lane_id,
            output_root=output_root.as_posix(),
            synthesized_ok=None,
            output_path=None,
            duration_seconds=None,
            sha256=None,
            peak_vram_used_bytes=None,
            exaggeration=None,
            cfg_weight=None,
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    clone_probe = payload.get("swedish_clone_probe") or {}
    return LaneSummary(
        lane_id=lane_id,
        output_root=output_root.as_posix(),
        synthesized_ok=clone_probe.get("ok"),
        output_path=clone_probe.get("output_path"),
        duration_seconds=clone_probe.get("duration_seconds"),
        sha256=clone_probe.get("sha256"),
        peak_vram_used_bytes=clone_probe.get("peak_vram_used_bytes"),
        exaggeration=payload.get("exaggeration"),
        cfg_weight=payload.get("cfg_weight"),
    )


def _write_summary(
    *,
    output_root: Path,
    settings: ExperimentSettings,
    helper_build_performed: bool,
    helper_image_id: str,
    baseline: LaneSummary,
    espeak_lane: LaneSummary,
    phoneme_metadata_path: Path,
) -> None:
    """Write one deterministic Chatterbox eSpeak experiment summary bundle."""
    payload = {
        "benchmark_id": "chatterbox-espeak-hemma",
        "generated_at": _utc_now_iso(),
        "helper_image": settings.helper_image,
        "helper_image_id": helper_image_id,
        "helper_build_performed": helper_build_performed,
        "reference_audio_path": settings.reference_audio_path.as_posix(),
        "probe_text": settings.probe_text,
        "phoneme_text_path": (output_root / "inputs" / "probe_text_espeak_sv.txt").as_posix(),
        "phoneme_metadata_path": phoneme_metadata_path.as_posix(),
        "baseline": asdict(baseline),
        "espeak_lane": asdict(espeak_lane),
    }
    (output_root / "report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = "\n".join(
        [
            "# Chatterbox eSpeak experiment Chatterbox eSpeak Experiment",
            "",
            f"- helper_image: `{settings.helper_image}`",
            f"- helper_image_id: `{helper_image_id}`",
            f"- reference_audio_path: `{settings.reference_audio_path.as_posix()}`",
            f"- phoneme_metadata_path: `{phoneme_metadata_path.as_posix()}`",
            "",
            "## Baseline",
            f"- synthesized_ok: `{baseline.synthesized_ok}`",
            f"- output_path: `{baseline.output_path}`",
            f"- duration_seconds: `{baseline.duration_seconds}`",
            f"- peak_vram_used_bytes: `{baseline.peak_vram_used_bytes}`",
            "",
            "## eSpeak Lane",
            f"- synthesized_ok: `{espeak_lane.synthesized_ok}`",
            f"- output_path: `{espeak_lane.output_path}`",
            f"- duration_seconds: `{espeak_lane.duration_seconds}`",
            f"- peak_vram_used_bytes: `{espeak_lane.peak_vram_used_bytes}`",
        ]
    )
    (output_root / "report.md").write_text(markdown + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the Chatterbox eSpeak experiment Hemma experiment and write deterministic evidence."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    enforce_generated_output_path(settings.output_root, label="output_root")
    paths = _prepare_output_root(settings.output_root)
    paths["original_text"].write_text(settings.probe_text + "\n", encoding="utf-8")
    helper_build_performed, helper_image_id = _ensure_helper_image(settings)
    LOGGER.info("Generating phonemized Swedish text via helper container")
    _run_phonemizer(
        settings,
        input_text_path=paths["original_text"],
        output_text_path=paths["phoneme_text"],
        metadata_path=paths["phoneme_metadata"],
    )
    LOGGER.info("Running baseline text-input lane")
    baseline_returncode = _run_chatterbox_benchmark_lane(
        lane_output_root=paths["baseline_dir"],
        reference_audio_path=settings.reference_audio_path,
        probe_text_file=paths["original_text"],
        exaggeration=0.5,
        cfg_weight=0.5,
        build_chatterbox_image=settings.build_chatterbox_image,
    )
    LOGGER.info("Running eSpeak-preprocessed lane")
    espeak_returncode = _run_chatterbox_benchmark_lane(
        lane_output_root=paths["espeak_dir"],
        reference_audio_path=settings.reference_audio_path,
        probe_text_file=paths["phoneme_text"],
        exaggeration=0.5,
        cfg_weight=0.5,
        build_chatterbox_image=False,
    )
    baseline = _load_lane_summary("baseline", paths["baseline_dir"])
    espeak_lane = _load_lane_summary("espeak_sv", paths["espeak_dir"])
    _write_summary(
        output_root=settings.output_root,
        settings=settings,
        helper_build_performed=helper_build_performed,
        helper_image_id=helper_image_id,
        baseline=baseline,
        espeak_lane=espeak_lane,
        phoneme_metadata_path=paths["phoneme_metadata"],
    )
    if baseline_returncode != 0 or espeak_returncode != 0:
        LOGGER.error(
            "Chatterbox eSpeak experiment completed with failing lanes: baseline=%s espeak=%s",
            baseline_returncode,
            espeak_returncode,
        )
        return 1
    LOGGER.info("Chatterbox eSpeak experiment completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
