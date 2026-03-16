"""Detached worker entrypoint for the Story 29 fallback standalone eval.

Purpose:
    Execute the canonical Story 29 fallback standalone eval in a background
    host process and persist one worker-status artifact for detached
    inspection.

Relationships:
    - Invoked by `story29_fallback_eval_detached.py`.
    - Delegates the actual eval execution to the public `qwen-train` CLI.
"""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from scripts.sir_convert_a_lot.cli.ml.qwen_train import main as qwen_train_main
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso, write_json
from scripts.sir_convert_a_lot.ml.qwen.training.story29_fallback_eval_detached import (
    failure_path,
    worker_status_path,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the detached worker parser."""
    parser = argparse.ArgumentParser(description="Run the detached Story 29 fallback eval worker.")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("eval_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Story 29 fallback standalone eval and persist detached worker status."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    eval_args = list(args.eval_args)
    if len(eval_args) > 0 and eval_args[0] == "--":
        eval_args = eval_args[1:]
    exit_code = 1
    try:
        exit_code = int(qwen_train_main(["eval", *eval_args]))
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:
        traceback.print_exc()
        failure_path(output_root).write_text(
            f"Detached Story 29 fallback eval worker failed: {exc}\n",
            encoding="utf-8",
        )
        exit_code = 1
    write_json(
        worker_status_path(output_root),
        {
            "finished_at": utc_now_iso(),
            "exit_code": int(exit_code),
        },
    )
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
