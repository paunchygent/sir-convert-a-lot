"""Re-stitch saved Chatterbox speech-aware stitching Chatterbox chunks without rerunning model
inference.

Purpose:
    Reuse the already generated raw Chatterbox speech-aware stitching chunk WAV files and produce a
    new
    stitched artifact with a small stitch-parameter adjustment, so listening
    comparisons can be made without another Chatterbox generation run.

Relationships:
    - Consumes the `segment-debug/` artifacts emitted by Chatterbox speech-aware stitching.
    - Reuses the repo-owned speech-aware stitcher from
      `chatterbox_segmented_generation.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.tts_sidecar.chatterbox_segmented_generation import (
    read_wav_tensor,
    stitch_waveforms,
    wave_bytes_from_waveform,
)

if TYPE_CHECKING:
    import torch

DEFAULT_SOURCE_DEBUG_DIR = Path(
    "build/verification/chatterbox-speech-aware-stitching-hemma/speech_aware/segment-debug"
)
DEFAULT_OUTPUT_ROOT = Path(
    "build/verification/chatterbox-speech-aware-stitching-hemma/speech_aware_relaxed_fade"
)


@dataclass(frozen=True)
class RestitchReport:
    """Machine-readable report for one saved-chunk re-stitch run."""

    source_debug_dir: str
    output_root: str
    stitch_mode: str
    cross_fade_ms: int
    edge_fade_cap_ms: float
    sample_rate_hz: int
    segment_count: int
    segment_texts: list[str]
    output_path: str
    chunk_analysis_path: str
    boundary_decisions_path: str


@dataclass(frozen=True)
class SavedSegmentPlan:
    """Typed representation of one saved Chatterbox speech-aware stitching segment plan."""

    original_text: str
    segment_count: int
    segments: list[str]
    max_chars: int
    cross_fade_ms: int


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the saved-chunk Chatterbox speech-aware stitching restitcher."""
    parser = argparse.ArgumentParser(
        description="Re-stitch saved Chatterbox speech-aware stitching chunks locally."
    )
    parser.add_argument("--source-debug-dir", type=Path, default=DEFAULT_SOURCE_DEBUG_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--stitch-mode",
        choices=("simple", "speech_aware"),
        default="speech_aware",
    )
    parser.add_argument("--cross-fade-ms", type=int, default=None)
    parser.add_argument("--edge-fade-cap-ms", type=float, default=12.0)
    return parser.parse_args(argv)


def _prepare_output_root(output_root: Path) -> dict[str, Path]:
    """Create a deterministic output tree for one saved-chunk re-stitch run."""
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts_dir = output_root / "artifacts"
    debug_dir = output_root / "segment-debug"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "artifacts_dir": artifacts_dir,
        "debug_dir": debug_dir,
        "report_json": output_root / "report.json",
        "report_md": output_root / "report.md",
        "output_wav": artifacts_dir / "scenario-a-sv-ref-sv-out.wav",
        "chunk_analysis": debug_dir / "chunk_analysis.json",
        "boundary_decisions": debug_dir / "boundary_decisions.json",
        "stitched": debug_dir / "stitched.wav",
    }
    for path in paths.values():
        if path in {artifacts_dir, debug_dir}:
            continue
        path.unlink(missing_ok=True)
    return paths


def _load_segment_plan(source_debug_dir: Path) -> SavedSegmentPlan:
    """Load the original segment plan emitted by Chatterbox speech-aware stitching."""
    plan_path = source_debug_dir / "segment_plan.json"
    if not plan_path.exists():
        raise SystemExit(f"Missing segment plan: {plan_path}")
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid segment plan payload: {plan_path}")
    original_text = payload.get("original_text")
    segment_count = payload.get("segment_count")
    segments = payload.get("segments")
    max_chars = payload.get("max_chars")
    cross_fade_ms = payload.get("cross_fade_ms")
    if not isinstance(original_text, str):
        raise SystemExit(f"Invalid original_text in segment plan: {plan_path}")
    if not isinstance(segment_count, int):
        raise SystemExit(f"Invalid segment_count in segment plan: {plan_path}")
    if not isinstance(segments, list) or not all(isinstance(segment, str) for segment in segments):
        raise SystemExit(f"Invalid segments in segment plan: {plan_path}")
    if not isinstance(max_chars, int):
        raise SystemExit(f"Invalid max_chars in segment plan: {plan_path}")
    if not isinstance(cross_fade_ms, int):
        raise SystemExit(f"Invalid cross_fade_ms in segment plan: {plan_path}")
    return SavedSegmentPlan(
        original_text=original_text,
        segment_count=segment_count,
        segments=list(segments),
        max_chars=max_chars,
        cross_fade_ms=cross_fade_ms,
    )


def _load_chunk_waveforms(
    source_debug_dir: Path, segment_count: int
) -> tuple[list[torch.Tensor], int]:
    """Load the original raw chunk waveforms from the saved debug bundle."""
    waveforms: list[torch.Tensor] = []
    sample_rate_hz: int | None = None
    for index in range(1, segment_count + 1):
        chunk_path = source_debug_dir / f"chunk_{index:02d}.wav"
        if not chunk_path.exists():
            raise SystemExit(f"Missing saved chunk WAV: {chunk_path}")
        waveform, chunk_sample_rate_hz = read_wav_tensor(chunk_path)
        if sample_rate_hz is None:
            sample_rate_hz = chunk_sample_rate_hz
        elif sample_rate_hz != chunk_sample_rate_hz:
            raise SystemExit(
                "Mismatched chunk sample rate: expected "
                f"{sample_rate_hz}, got {chunk_sample_rate_hz}"
            )
        waveforms.append(waveform)
    if sample_rate_hz is None:
        raise SystemExit("No saved chunks were loaded.")
    return waveforms, sample_rate_hz


def _write_summary(report: RestitchReport, report_json: Path, report_md: Path) -> None:
    """Write deterministic JSON and markdown evidence for the re-stitch run."""
    report_json.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = "\n".join(
        [
            "# Chatterbox speech-aware stitching Saved-Chunk Restitch",
            "",
            f"- source_debug_dir: `{report.source_debug_dir}`",
            f"- stitch_mode: `{report.stitch_mode}`",
            f"- cross_fade_ms: `{report.cross_fade_ms}`",
            f"- edge_fade_cap_ms: `{report.edge_fade_cap_ms}`",
            f"- output_path: `{report.output_path}`",
            f"- chunk_analysis_path: `{report.chunk_analysis_path}`",
            f"- boundary_decisions_path: `{report.boundary_decisions_path}`",
        ]
    )
    report_md.write_text(markdown + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """
    Re-stitch saved Chatterbox speech-aware stitching chunks and write a new local evidence bundle.
    """
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    enforce_generated_output_path(args.output_root, label="output_root")
    paths = _prepare_output_root(args.output_root)
    source_debug_dir = Path(args.source_debug_dir)
    plan = _load_segment_plan(source_debug_dir)
    segment_texts = plan.segments
    cross_fade_ms = (
        int(args.cross_fade_ms) if args.cross_fade_ms is not None else plan.cross_fade_ms
    )
    waveforms, sample_rate_hz = _load_chunk_waveforms(
        source_debug_dir=source_debug_dir,
        segment_count=plan.segment_count,
    )
    stitched = stitch_waveforms(
        waveforms=waveforms,
        sample_rate_hz=sample_rate_hz,
        cross_fade_ms=cross_fade_ms,
        segment_texts=segment_texts,
        stitch_mode=str(args.stitch_mode),
        edge_fade_cap_ms=float(args.edge_fade_cap_ms),
    )
    paths["chunk_analysis"].write_text(
        json.dumps([asdict(chunk_analysis) for chunk_analysis in stitched.chunk_analyses], indent=2)
        + "\n",
        encoding="utf-8",
    )
    paths["boundary_decisions"].write_text(
        json.dumps(
            [asdict(boundary_decision) for boundary_decision in stitched.boundary_decisions],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    wav_bytes = wave_bytes_from_waveform(stitched.waveform, sample_rate_hz=sample_rate_hz)
    paths["output_wav"].write_bytes(wav_bytes)
    paths["stitched"].write_bytes(wav_bytes)
    report = RestitchReport(
        source_debug_dir=source_debug_dir.as_posix(),
        output_root=Path(args.output_root).as_posix(),
        stitch_mode=str(args.stitch_mode),
        cross_fade_ms=cross_fade_ms,
        edge_fade_cap_ms=float(args.edge_fade_cap_ms),
        sample_rate_hz=sample_rate_hz,
        segment_count=plan.segment_count,
        segment_texts=segment_texts,
        output_path=paths["output_wav"].as_posix(),
        chunk_analysis_path=paths["chunk_analysis"].as_posix(),
        boundary_decisions_path=paths["boundary_decisions"].as_posix(),
    )
    _write_summary(report, paths["report_json"], paths["report_md"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
