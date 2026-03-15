"""Public CLI composition root for detached Qwen training on Hemma.

Purpose:
    Provide the canonical `qwen-train` entrypoint while delegating parser
    construction and command execution to bounded control-plane modules.

Relationships:
    - Uses `ml.qwen.training.control_plane` for parser and dispatch logic.
    - Keeps the CLI layer free of domain validation and orchestration logic.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.control_plane import (
    build_parser,
    dispatch_command,
)
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_DOCKERFILE_PATH,
)


def main(argv: list[str] | None = None) -> int:
    """Parse one `qwen-train` command and dispatch it to the control plane."""
    parser = build_parser()
    args = parser.parse_args(argv)
    setattr(args, "repo_root", Path.cwd())
    setattr(args, "default_dockerfile_path", DEFAULT_DOCKERFILE_PATH)
    return dispatch_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
