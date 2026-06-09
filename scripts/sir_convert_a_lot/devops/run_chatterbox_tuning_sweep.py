"""Run the Chatterbox tuning sweep Chatterbox tuning sweep against Hemma.

Purpose:
    Execute the documented Chatterbox `cfg_weight` / `exaggeration` sweep in a
    conservative-first order, mirror every remote evidence bundle back into the
    local repo, and write one local sweep summary.

Relationships:
    - Invokes `benchmark:chatterbox` remotely through the canonical
      `pdm run run-hemma -- ...` wrapper.
    - Uses the Chatterbox benchmark evidence shape as the per-lane source of truth.
    - Writes the Chatterbox tuning sweep sweep summary under `build/verification/`.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path

LOGGER = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REFERENCE_AUDIO = Path(
    "build/verification/openvoice-v2-hemma/inputs/teacher_reference_voice.m4a"
)
DEFAULT_PROBE_TEXT = (
    "Hej. Det här är ett rent svenskt prov. Vi testar om modellen kan klona en "
    "lärarröst och läsa svensk text tydligt, naturligt och utan störande "
    "artefakter."
)
DEFAULT_SWEEP_OUTPUT_ROOT = Path("build/verification/chatterbox-tuning-tuning-sweep")
DEFAULT_HEMMA_HOST = "hemma"
DEFAULT_HEMMA_ROOT = Path("/home/paunchygent/apps/sir-convert-a-lot")


@dataclass(frozen=True)
class SweepLane:
    """One deterministic Chatterbox tuning lane."""

    slug: str
    exaggeration: float
    cfg_weight: float
    output_root: Path


@dataclass(frozen=True)
class SweepSettings:
    """Normalized CLI settings for the Chatterbox tuning sweep tuning sweep."""

    output_root: Path
    reference_audio: Path
    probe_text: str
    hemma_host: str
    hemma_root: Path
    skip_build: bool


@dataclass(frozen=True)
class LaneResult:
    """One summarized lane outcome for the Chatterbox tuning sweep report."""

    slug: str
    exaggeration: float
    cfg_weight: float
    output_root: str
    returncode: int
    synthesized_ok: bool | None
    clone_output_path: str | None
    clone_duration_seconds: float | None
    clone_sha256: str | None
    peak_vram_used_bytes: int | None


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _float_token(value: float) -> str:
    """Return one path-safe token for a sweep float value."""
    return format(value, ".1f").replace(".", "p")


def _default_lanes() -> list[SweepLane]:
    """Return the documented conservative-first tuning grid."""
    combos: tuple[tuple[float, float], ...] = (
        (0.5, 0.5),
        (0.5, 0.3),
        (0.7, 0.5),
        (0.7, 0.3),
        (0.5, 0.0),
        (0.7, 0.0),
    )
    lanes: list[SweepLane] = []
    for exaggeration, cfg_weight in combos:
        slug = f"exag-{_float_token(exaggeration)}-cfg-{_float_token(cfg_weight)}"
        lanes.append(
            SweepLane(
                slug=slug,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                output_root=Path(f"build/verification/chatterbox-tuning-{slug}"),
            )
        )
    return lanes


def _parse_args(argv: list[str]) -> SweepSettings:
    """Parse CLI arguments into normalized Chatterbox tuning sweep settings."""
    parser = argparse.ArgumentParser(
        description="Run the Chatterbox tuning sweep Chatterbox tuning sweep."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_SWEEP_OUTPUT_ROOT)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--probe-text", default=DEFAULT_PROBE_TEXT)
    parser.add_argument(
        "--hemma-host",
        default=os.environ.get("SIR_CONVERT_A_LOT_HEMMA_HOST", DEFAULT_HEMMA_HOST),
    )
    parser.add_argument(
        "--hemma-root",
        type=Path,
        default=Path(os.environ.get("SIR_CONVERT_A_LOT_HEMMA_ROOT", DEFAULT_HEMMA_ROOT.as_posix())),
    )
    parser.add_argument("--skip-build", action="store_true", default=True)
    args = parser.parse_args(argv)
    return SweepSettings(
        output_root=Path(args.output_root),
        reference_audio=Path(args.reference_audio),
        probe_text=str(args.probe_text),
        hemma_host=str(args.hemma_host),
        hemma_root=Path(args.hemma_root),
        skip_build=bool(args.skip_build),
    )


def _run_local(command: list[str], *, label: str) -> int:
    """Run one local command and return the exit code."""
    LOGGER.info("%s: %s", label, " ".join(command))
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def _run_lane(settings: SweepSettings, lane: SweepLane) -> int:
    """Run one Chatterbox benchmark lane remotely on Hemma."""
    command = [
        "pdm",
        "run",
        "run-hemma",
        "--",
        "pdm",
        "run",
        "benchmark:chatterbox",
        "--output-root",
        lane.output_root.as_posix(),
        "--reference-audio",
        settings.reference_audio.as_posix(),
        "--probe-text",
        settings.probe_text,
        "--exaggeration",
        str(lane.exaggeration),
        "--cfg-weight",
        str(lane.cfg_weight),
    ]
    if settings.skip_build:
        command.append("--skip-build")
    LOGGER.info("Running lane %s", lane.slug)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def _sync_lane(settings: SweepSettings, lane: SweepLane) -> int:
    """Mirror one remote Hemma lane back into the local repo copy."""
    local_output_root = REPO_ROOT / lane.output_root
    local_output_root.parent.mkdir(parents=True, exist_ok=True)
    remote_source = f"{settings.hemma_host}:{(settings.hemma_root / lane.output_root).as_posix()}/"
    command = ["rsync", "-a", remote_source, local_output_root.as_posix() + "/"]
    return _run_local(command, label=f"rsync {lane.slug}")


def _load_lane_result(lane: SweepLane) -> LaneResult:
    """Load one local Chatterbox benchmark report into the Chatterbox tuning sweep summary shape."""
    report_path = REPO_ROOT / lane.output_root / "report.json"
    if not report_path.exists():
        return LaneResult(
            slug=lane.slug,
            exaggeration=lane.exaggeration,
            cfg_weight=lane.cfg_weight,
            output_root=lane.output_root.as_posix(),
            returncode=1,
            synthesized_ok=None,
            clone_output_path=None,
            clone_duration_seconds=None,
            clone_sha256=None,
            peak_vram_used_bytes=None,
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    clone_probe = payload.get("swedish_clone_probe") or {}
    return LaneResult(
        slug=lane.slug,
        exaggeration=lane.exaggeration,
        cfg_weight=lane.cfg_weight,
        output_root=lane.output_root.as_posix(),
        returncode=0,
        synthesized_ok=clone_probe.get("ok"),
        clone_output_path=clone_probe.get("output_path"),
        clone_duration_seconds=clone_probe.get("duration_seconds"),
        clone_sha256=clone_probe.get("sha256"),
        peak_vram_used_bytes=clone_probe.get("peak_vram_used_bytes"),
    )


def _write_summary(*, output_root: Path, settings: SweepSettings, lanes: list[LaneResult]) -> None:
    """Write one deterministic Chatterbox tuning sweep summary bundle."""
    output_root.mkdir(parents=True, exist_ok=True)
    summary_json = output_root / "report.json"
    summary_md = output_root / "report.md"
    payload = {
        "benchmark_id": "chatterbox-tuning-tuning-sweep",
        "generated_at": _utc_now_iso(),
        "reference_audio": settings.reference_audio.as_posix(),
        "probe_text": settings.probe_text,
        "lanes": [asdict(lane) for lane in lanes],
    }
    summary_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_lines = [
        "# Chatterbox tuning sweep Chatterbox Tuning Sweep",
        "",
        f"- reference_audio: `{settings.reference_audio.as_posix()}`",
        f"- probe_text: `{settings.probe_text}`",
        "",
        "## Lanes",
    ]
    for lane in lanes:
        markdown_lines.extend(
            [
                f"- `{lane.slug}`",
                f"  - exaggeration: `{lane.exaggeration}`",
                f"  - cfg_weight: `{lane.cfg_weight}`",
                f"  - synthesized_ok: `{lane.synthesized_ok}`",
                f"  - clone_output_path: `{lane.clone_output_path}`",
                f"  - clone_duration_seconds: `{lane.clone_duration_seconds}`",
                f"  - peak_vram_used_bytes: `{lane.peak_vram_used_bytes}`",
            ]
        )
    summary_md.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the complete Chatterbox tuning sweep sweep and mirror the evidence locally."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    enforce_generated_output_path(settings.output_root, label="output_root")
    lanes = _default_lanes()
    lane_results: list[LaneResult] = []
    for lane in lanes:
        returncode = _run_lane(settings, lane)
        sync_returncode = _sync_lane(settings, lane)
        result = _load_lane_result(lane)
        if returncode != 0 or sync_returncode != 0:
            result = LaneResult(
                slug=result.slug,
                exaggeration=result.exaggeration,
                cfg_weight=result.cfg_weight,
                output_root=result.output_root,
                returncode=max(returncode, sync_returncode),
                synthesized_ok=result.synthesized_ok,
                clone_output_path=result.clone_output_path,
                clone_duration_seconds=result.clone_duration_seconds,
                clone_sha256=result.clone_sha256,
                peak_vram_used_bytes=result.peak_vram_used_bytes,
            )
        lane_results.append(result)
    _write_summary(output_root=settings.output_root, settings=settings, lanes=lane_results)
    failures = [
        lane for lane in lane_results if lane.returncode != 0 or lane.synthesized_ok is not True
    ]
    if failures:
        LOGGER.error(
            "Chatterbox tuning sweep completed with failing lanes: %s",
            ", ".join(lane.slug for lane in failures),
        )
        return 1
    LOGGER.info("Chatterbox tuning sweep completed successfully for %s lanes", len(lane_results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
