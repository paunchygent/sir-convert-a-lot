"""ROCm profiler wrapper for the Task 101 in-container probe.

Purpose:
    Execute the existing Task 101 probe under `rocprofv3` without ad hoc shell
    commands so one bounded ROCm trace can be captured through governed
    launcher/runtime surfaces.

Relationships:
    - Invoked by `task101_qwen_pilot_runtime.py` when ROCm profiling is enabled.
    - Launches `task101_qwen_pilot_probe.py` as the profiled child process.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _split_wrapper_and_probe_args(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split wrapper args from probe args using `--` as the separator."""
    if "--" not in argv:
        return argv, []
    split_index = argv.index("--")
    return argv[:split_index], argv[split_index + 1 :]


def _build_parser() -> argparse.ArgumentParser:
    """Build the bounded ROCm profiler wrapper parser."""
    parser = argparse.ArgumentParser(
        description="Run Task 101 probe under rocprofv3 with deterministic outputs."
    )
    parser.add_argument("--rocprof-output-dir", type=Path, required=True)
    parser.add_argument("--rocprof-trace-name", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Task 101 probe under rocprofv3."""
    raw_argv = sys.argv[1:] if argv is None else argv
    wrapper_argv, probe_argv = _split_wrapper_and_probe_args(raw_argv)
    if len(probe_argv) == 0:
        raise SystemExit("Task 101 rocprof wrapper requires probe args after `--`.")
    parser = _build_parser()
    args = parser.parse_args(wrapper_argv)
    output_dir = Path(args.rocprof_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_prefix = (output_dir / args.rocprof_trace_name).as_posix()
    command = [
        "rocprofv3",
        "--runtime-trace",
        "--output-format",
        "csv",
        "--output-file",
        trace_prefix,
        "--",
        sys.executable,
        "-m",
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_probe",
        *probe_argv,
    ]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
