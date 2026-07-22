"""CLI composition root for the isolated Qwen PDM project."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.sir_convert_a_lot.devops.qwen_project_runtime import run_qwen_project


def main(arguments: list[str] | None = None) -> int:
    """Run one public Qwen command through its owning project."""
    project_root = Path(__file__).resolve().parents[3]
    return run_qwen_project(project_root, arguments if arguments is not None else sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
