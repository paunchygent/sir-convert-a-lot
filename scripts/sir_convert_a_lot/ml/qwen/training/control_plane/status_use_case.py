"""Status inspection use case for detached Qwen training control-plane commands.

Purpose:
    Own pointer resolution, detached inspection, and status artifact
    persistence for `qwen-train status`.

Relationships:
    - Uses launch loading and detached-runtime inspection services.
    - Persists status JSON and markdown artifacts through metadata helpers.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import inspect_detached_training
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    render_status_markdown,
    resolve_launch_root,
    status_markdown_path,
    status_metadata_path,
    write_json,
    write_markdown,
)

from .launch_loader import load_training_launch


def handle_status(args) -> int:
    """Execute the detached training status inspection use case."""
    current_launch_root = resolve_launch_root(args.output_root, args.launch_root)
    launch = load_training_launch(current_launch_root)
    status = inspect_detached_training(launch)
    write_json(status_metadata_path(current_launch_root), asdict(status))
    write_markdown(status_markdown_path(current_launch_root), render_status_markdown(status))
    print(json.dumps(asdict(status), indent=2, ensure_ascii=False))
    return 0
