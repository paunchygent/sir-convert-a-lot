"""Run the Task 91 Chatterbox speech-aware stitching experiment on Hemma.

Purpose:
    Compare the existing segmented Chatterbox stitcher against the new
    speech-aware stitcher on Hemma and write deterministic evidence for both
    segmented lanes.

Relationships:
    - Reuses the committed Task 86 benchmark runner for both synthesis lanes.
    - Proves the Task 91 speech-aware stitching layer through the same
      ADR-0007 sidecar contract used by the existing Chatterbox benchmark.
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
from scripts.sir_convert_a_lot.devops import run_task86_hemma_chatterbox_benchmark

LOGGER = logging.getLogger(__name__)
DEFAULT_OUTPUT_ROOT = Path("build/verification/task-91-chatterbox-speech-aware-stitching-hemma")
DEFAULT_REFERENCE_AUDIO = Path(
    "build/verification/task-81-openvoice-v2-hemma/inputs/teacher_reference_voice.m4a"
)
DEFAULT_PROBE_TEXT = (
    "Hej. Det här är ett längre svenskt prov för Tjätterbåcks på Hemma. "
    "Vi vill höra om modellen kan hålla ihop en lärarröst över flera meningar "
    "utan att tappa tydlighet, rytm eller naturlighet. När texten blir längre "
    "måste övergångarna mellan segmenten fortfarande låta lugna och "
    "kontrollerade, utan brus i slutet av varje fras. Därför testar vi nu en "
    "längre sammanhängande text, men med kortare segment, så att modellen får "
    "mindre mängd tal att avsluta i varje del. Målet är att få ett jämnare "
    "flöde, bättre svensk prosodi och mindre av det vita brus som tidigare "
    "dök upp i slutet av vissa segment. Om det här fungerar bättre har vi en "
    "tydligare väg framåt för fortsatt Tjätterbåcks-tuning på Hemma."
)


@dataclass(frozen=True)
class ExperimentSettings:
    """Normalized CLI settings for the Task 91 Hemma experiment."""

    output_root: Path
    reference_audio_path: Path
    probe_text: str
    exaggeration: float
    cfg_weight: float
    segment_max_chars: int
    segment_cross_fade_ms: int
    build_image: bool


@dataclass(frozen=True)
class LaneSummary:
    """One summarized Task 86 segmented-lane outcome for the Task 91 report."""

    lane_id: str
    stitch_mode: str
    output_root: str
    synthesized_ok: bool | None
    output_path: str | None
    duration_seconds: float | None
    sha256: str | None
    peak_vram_used_bytes: int | None
    segment_text: bool | None
    segment_max_chars: int | None
    segment_cross_fade_ms: int | None
    segment_stitch_mode: str | None
    segment_debug_dir: str | None


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_args(argv: list[str]) -> ExperimentSettings:
    """Parse CLI arguments into normalized Task 91 settings."""
    parser = argparse.ArgumentParser(
        description="Run the Task 91 speech-aware Chatterbox experiment on Hemma."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--probe-text", default=DEFAULT_PROBE_TEXT)
    parser.add_argument("--exaggeration", type=float, default=0.5)
    parser.add_argument("--cfg-weight", type=float, default=0.5)
    parser.add_argument("--segment-max-chars", type=int, default=320)
    parser.add_argument("--segment-cross-fade-ms", type=int, default=80)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)
    return ExperimentSettings(
        output_root=Path(args.output_root),
        reference_audio_path=Path(args.reference_audio),
        probe_text=str(args.probe_text),
        exaggeration=float(args.exaggeration),
        cfg_weight=float(args.cfg_weight),
        segment_max_chars=int(args.segment_max_chars),
        segment_cross_fade_ms=int(args.segment_cross_fade_ms),
        build_image=not bool(args.skip_build),
    )


def _prepare_output_root(output_root: Path) -> dict[str, Path]:
    """Create a clean deterministic output tree for Task 91."""
    output_root.mkdir(parents=True, exist_ok=True)
    inputs_dir = output_root / "inputs"
    simple_dir = output_root / "simple"
    speech_aware_dir = output_root / "speech_aware"
    for directory in (inputs_dir, simple_dir, speech_aware_dir):
        directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "inputs_dir": inputs_dir,
        "simple_dir": simple_dir,
        "speech_aware_dir": speech_aware_dir,
        "report_json": output_root / "report.json",
        "report_md": output_root / "report.md",
        "probe_text": inputs_dir / "probe_text_sv.txt",
    }
    for path in (paths["report_json"], paths["report_md"], paths["probe_text"]):
        with suppress(FileNotFoundError):
            path.unlink()
    return paths


def _run_task86_lane(
    *,
    lane_output_root: Path,
    reference_audio_path: Path,
    probe_text_file: Path,
    exaggeration: float,
    cfg_weight: float,
    segment_max_chars: int,
    segment_cross_fade_ms: int,
    segment_stitch_mode: str,
    build_image: bool,
) -> int:
    """Execute one Task 86 segmented lane in-process on Hemma."""
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
        "--segment-text",
        "--segment-max-chars",
        str(segment_max_chars),
        "--segment-cross-fade-ms",
        str(segment_cross_fade_ms),
        "--segment-stitch-mode",
        segment_stitch_mode,
    ]
    if not build_image:
        argv.append("--skip-build")
    return run_task86_hemma_chatterbox_benchmark.main(argv)


def _load_lane_summary(lane_id: str, stitch_mode: str, output_root: Path) -> LaneSummary:
    """Load one Task 86 report into the Task 91 summary shape."""
    report_path = output_root / "report.json"
    if not report_path.exists():
        return LaneSummary(
            lane_id=lane_id,
            stitch_mode=stitch_mode,
            output_root=output_root.as_posix(),
            synthesized_ok=None,
            output_path=None,
            duration_seconds=None,
            sha256=None,
            peak_vram_used_bytes=None,
            segment_text=None,
            segment_max_chars=None,
            segment_cross_fade_ms=None,
            segment_stitch_mode=None,
            segment_debug_dir=None,
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    clone_probe = payload.get("swedish_clone_probe") or {}
    return LaneSummary(
        lane_id=lane_id,
        stitch_mode=stitch_mode,
        output_root=output_root.as_posix(),
        synthesized_ok=clone_probe.get("ok"),
        output_path=clone_probe.get("output_path"),
        duration_seconds=clone_probe.get("duration_seconds"),
        sha256=clone_probe.get("sha256"),
        peak_vram_used_bytes=clone_probe.get("peak_vram_used_bytes"),
        segment_text=payload.get("segment_text"),
        segment_max_chars=payload.get("segment_max_chars"),
        segment_cross_fade_ms=payload.get("segment_cross_fade_ms"),
        segment_stitch_mode=payload.get("segment_stitch_mode"),
        segment_debug_dir=payload.get("segment_debug_dir"),
    )


def _write_summary(
    *,
    output_root: Path,
    settings: ExperimentSettings,
    simple_lane: LaneSummary,
    speech_aware_lane: LaneSummary,
) -> None:
    """Write one deterministic Task 91 summary bundle."""
    payload = {
        "benchmark_id": "task-91-chatterbox-speech-aware-stitching-hemma",
        "generated_at": _utc_now_iso(),
        "reference_audio_path": settings.reference_audio_path.as_posix(),
        "probe_text": settings.probe_text,
        "simple_lane": asdict(simple_lane),
        "speech_aware_lane": asdict(speech_aware_lane),
    }
    (output_root / "report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = "\n".join(
        [
            "# Task 91 Chatterbox Speech-Aware Stitching Experiment",
            "",
            f"- reference_audio_path: `{settings.reference_audio_path.as_posix()}`",
            f"- segment_max_chars: `{settings.segment_max_chars}`",
            f"- segment_cross_fade_ms: `{settings.segment_cross_fade_ms}`",
            "",
            "## Simple Stitch Lane",
            f"- synthesized_ok: `{simple_lane.synthesized_ok}`",
            f"- output_path: `{simple_lane.output_path}`",
            f"- duration_seconds: `{simple_lane.duration_seconds}`",
            f"- peak_vram_used_bytes: `{simple_lane.peak_vram_used_bytes}`",
            f"- segment_debug_dir: `{simple_lane.segment_debug_dir}`",
            "",
            "## Speech-Aware Stitch Lane",
            f"- synthesized_ok: `{speech_aware_lane.synthesized_ok}`",
            f"- output_path: `{speech_aware_lane.output_path}`",
            f"- duration_seconds: `{speech_aware_lane.duration_seconds}`",
            f"- peak_vram_used_bytes: `{speech_aware_lane.peak_vram_used_bytes}`",
            f"- segment_debug_dir: `{speech_aware_lane.segment_debug_dir}`",
        ]
    )
    (output_root / "report.md").write_text(markdown + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the Task 91 Hemma experiment and write deterministic evidence."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    enforce_generated_output_path(settings.output_root, label="output_root")
    paths = _prepare_output_root(settings.output_root)
    paths["probe_text"].write_text(settings.probe_text + "\n", encoding="utf-8")
    LOGGER.info("Running Task 91 segmented simple-stitch baseline lane")
    simple_returncode = _run_task86_lane(
        lane_output_root=paths["simple_dir"],
        reference_audio_path=settings.reference_audio_path,
        probe_text_file=paths["probe_text"],
        exaggeration=settings.exaggeration,
        cfg_weight=settings.cfg_weight,
        segment_max_chars=settings.segment_max_chars,
        segment_cross_fade_ms=settings.segment_cross_fade_ms,
        segment_stitch_mode="simple",
        build_image=settings.build_image,
    )
    if simple_returncode != 0:
        return simple_returncode
    LOGGER.info("Running Task 91 segmented speech-aware stitch lane")
    speech_aware_returncode = _run_task86_lane(
        lane_output_root=paths["speech_aware_dir"],
        reference_audio_path=settings.reference_audio_path,
        probe_text_file=paths["probe_text"],
        exaggeration=settings.exaggeration,
        cfg_weight=settings.cfg_weight,
        segment_max_chars=settings.segment_max_chars,
        segment_cross_fade_ms=settings.segment_cross_fade_ms,
        segment_stitch_mode="speech_aware",
        build_image=False,
    )
    if speech_aware_returncode != 0:
        return speech_aware_returncode
    _write_summary(
        output_root=settings.output_root,
        settings=settings,
        simple_lane=_load_lane_summary("simple", "simple", paths["simple_dir"]),
        speech_aware_lane=_load_lane_summary(
            "speech_aware",
            "speech_aware",
            paths["speech_aware_dir"],
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
