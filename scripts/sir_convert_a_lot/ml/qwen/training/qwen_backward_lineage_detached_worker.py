"""
Detached worker entrypoint for the Qwen backward-lineage and fresh-start proof lane backward-lineage
proof.

Purpose:
    Execute the canonical backward-lineage host-side proof runner in a background Hemma
    process and persist one worker-status artifact for detached inspection.

Relationships:
    - Invoked by `qwen_backward_lineage_detached.py`.
    - Delegates the actual proof execution to `qwen_backward_lineage_runner.py`.
"""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_detached import (
    failure_path,
    worker_status_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_runner import (
    main as run_backward_lineage_main,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso, write_json


def _build_parser() -> argparse.ArgumentParser:
    """Build the detached worker parser."""
    parser = argparse.ArgumentParser(description="Run the detached backward-lineage worker.")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("proof_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the backward-lineage proof and persist detached worker status."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    proof_args = list(args.proof_args)
    if len(proof_args) > 0 and proof_args[0] == "--":
        proof_args = proof_args[1:]
    exit_code = 1
    try:
        exit_code = int(run_backward_lineage_main(proof_args))
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
        if exit_code != 0:
            failure_path(output_root).write_text(
                f"Detached Qwen backward-lineage worker exited via SystemExit: {exc}\n",
                encoding="utf-8",
            )
    except Exception as exc:
        traceback.print_exc()
        failure_path(output_root).write_text(
            f"Detached Qwen backward-lineage worker failed: {exc}\n",
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
