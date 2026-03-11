"""Helper surface for Task 103 completed-row resume indexes.

Purpose:
    Provide one committed CLI for rebuilding or validating the Task 103
    completed-row resume index so older run roots can gain the faster resume
    path without notebook-only or ad hoc shell logic.

Relationships:
    - Wraps `task103_qwen_preprocessing_storage.py` resume-index helpers.
    - Operates against existing Task 103 run roots on Hemma or Drive-backed
      Colab storage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    completed_row_keys_index_path,
    load_completed_row_keys_from_index,
    rebuild_completed_row_keys_index,
    spool_rows_dir,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for the resume-index helper surface."""
    parser = argparse.ArgumentParser(
        description="Rebuild or validate the Task 103 completed-row resume index."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    rebuild_parser = subparsers.add_parser(
        "rebuild",
        help="Rebuild the completed-row index from canonical spool JSON rows.",
    )
    rebuild_parser.add_argument("--run-root", type=Path, required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate that the completed-row index can be read successfully.",
    )
    validate_parser.add_argument("--run-root", type=Path, required=True)

    return parser.parse_args(argv)


def _render_summary(
    *,
    command: str,
    run_root: Path,
    completed_row_count: int,
    index_exists: bool,
) -> str:
    """Render one deterministic JSON summary for the helper surface."""
    return json.dumps(
        {
            "command": command,
            "run_root": run_root.as_posix(),
            "spool_rows_dir": spool_rows_dir(run_root).as_posix(),
            "index_path": completed_row_keys_index_path(run_root).as_posix(),
            "index_exists": index_exists,
            "completed_row_count": completed_row_count,
        },
        indent=2,
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the Task 103 completed-row resume-index helper surface."""
    args = _parse_args(argv)
    run_root = args.run_root.resolve()
    if args.command == "rebuild":
        completed_row_keys = rebuild_completed_row_keys_index(run_root)
        print(
            _render_summary(
                command="rebuild",
                run_root=run_root,
                completed_row_count=len(completed_row_keys),
                index_exists=completed_row_keys_index_path(run_root).exists(),
            )
        )
        return 0
    if args.command == "validate":
        completed_row_keys = load_completed_row_keys_from_index(run_root)
        print(
            _render_summary(
                command="validate",
                run_root=run_root,
                completed_row_count=len(completed_row_keys),
                index_exists=completed_row_keys_index_path(run_root).exists(),
            )
        )
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
