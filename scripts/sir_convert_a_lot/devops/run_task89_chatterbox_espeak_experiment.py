"""Run the Task 89 Chatterbox eSpeak experiment from the local repo.

Purpose:
    Invoke the committed Hemma-side Task 89 experiment runner through the
    canonical `run-hemma` wrapper and mirror the resulting evidence bundle back
    into the local repo copy.

Relationships:
    - Calls `benchmark:task-89-hemma` remotely in the Hemma repo clone.
    - Syncs the remote `build/verification/` bundle into the local repo.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path

LOGGER = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = Path("build/verification/task-89-chatterbox-espeak-hemma")
DEFAULT_REFERENCE_AUDIO = Path(
    "build/verification/task-81-openvoice-v2-hemma/inputs/teacher_reference_voice.m4a"
)
DEFAULT_HEMMA_HOST = "hemma"
DEFAULT_HEMMA_ROOT = Path("/home/paunchygent/apps/sir-convert-a-lot")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for the local Task 89 orchestrator."""
    parser = argparse.ArgumentParser(description="Run the Task 89 eSpeak experiment on Hemma.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument(
        "--probe-text",
        default=(
            "Hej. Det här är ett rent svenskt prov. Vi testar om modellen kan klona en "
            "lärarröst och läsa svensk text tydligt, naturligt och utan störande artefakter."
        ),
    )
    parser.add_argument("--espeak-language", default="sv")
    parser.add_argument(
        "--hemma-host",
        default=os.environ.get("SIR_CONVERT_A_LOT_HEMMA_HOST", DEFAULT_HEMMA_HOST),
    )
    parser.add_argument(
        "--hemma-root",
        type=Path,
        default=Path(os.environ.get("SIR_CONVERT_A_LOT_HEMMA_ROOT", DEFAULT_HEMMA_ROOT.as_posix())),
    )
    parser.add_argument("--skip-helper-build", action="store_true")
    parser.add_argument("--skip-benchmark-build", action="store_true", default=True)
    return parser.parse_args(argv)


def _run_local(command: list[str]) -> int:
    """Run one local command in the repo root and return the exit code."""
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    """Run the remote Task 89 experiment and sync the evidence locally."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    enforce_generated_output_path(Path(args.output_root), label="output_root")
    remote_command = [
        "pdm",
        "run",
        "run-hemma",
        "--",
        "pdm",
        "run",
        "benchmark:task-89-hemma",
        "--output-root",
        Path(args.output_root).as_posix(),
        "--reference-audio",
        Path(args.reference_audio).as_posix(),
        "--probe-text",
        str(args.probe_text),
        "--espeak-language",
        str(args.espeak_language),
    ]
    if args.skip_helper_build:
        remote_command.append("--skip-helper-build")
    if args.skip_benchmark_build:
        remote_command.append("--skip-benchmark-build")
    LOGGER.info("Running Task 89 remotely on Hemma")
    remote_returncode = _run_local(remote_command)
    sync_command = [
        "rsync",
        "-a",
        f"{args.hemma_host}:{(Path(args.hemma_root) / Path(args.output_root)).as_posix()}/",
        (REPO_ROOT / Path(args.output_root)).as_posix() + "/",
    ]
    LOGGER.info("Syncing Task 89 evidence bundle back to the local repo")
    sync_returncode = _run_local(sync_command)
    if remote_returncode != 0 or sync_returncode != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
