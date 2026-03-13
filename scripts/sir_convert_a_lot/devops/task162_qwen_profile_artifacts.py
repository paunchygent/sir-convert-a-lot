"""Artifact inspection helper for Task 162 profiling outputs.

Purpose:
    Provide one committed script surface that enumerates PyTorch and ROCm trace
    files for a Task 101 run root so operators can collect profiling evidence
    without ad hoc shell payloads.

Relationships:
    - Used by `run_task162_hemma_task101_profiling.py`.
    - Reads trace artifacts written by `sft_12hz.py` and rocprof wrapper runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def collect_task162_profile_artifacts(run_root: Path) -> dict[str, object]:
    """Return one deterministic profile artifact summary for a run root."""
    pytorch_trace_dir = run_root / "profiling" / "pytorch"
    rocm_trace_dir = run_root / "profiling" / "rocm"
    pytorch_trace_files = sorted(
        path.as_posix() for path in pytorch_trace_dir.glob("**/*.pt.trace.json") if path.is_file()
    )
    rocm_trace_files = sorted(
        path.as_posix() for path in rocm_trace_dir.glob("**/*") if path.is_file()
    )
    return {
        "run_root": run_root.as_posix(),
        "pytorch_trace_dir": pytorch_trace_dir.as_posix(),
        "pytorch_trace_files": pytorch_trace_files,
        "rocm_trace_dir": rocm_trace_dir.as_posix(),
        "rocm_trace_files": rocm_trace_files,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build the artifact collector CLI parser."""
    parser = argparse.ArgumentParser(description="Collect Task 162 profiling artifact paths.")
    parser.add_argument("--run-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Task 162 profile artifact collector."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload = collect_task162_profile_artifacts(Path(args.run_root))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
