"""Stop use case for detached Qwen training control-plane commands.

Purpose:
    Own intentional stop handling and stop-artifact persistence for
    `qwen-train stop`.

Relationships:
    - Uses launch loading and detached-runtime stop services.
    - Persists stop metadata through the canonical training metadata helpers.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime import stop_detached_training
from scripts.sir_convert_a_lot.ml.qwen.training.metadata import (
    resolve_launch_root,
    stop_metadata_path,
    write_json,
)

from .launch_loader import load_training_launch


def handle_stop(args) -> int:
    """Execute the detached training stop use case."""
    current_launch_root = resolve_launch_root(args.output_root, args.launch_root)
    launch = load_training_launch(current_launch_root)
    stopped = stop_detached_training(launch)
    write_json(stop_metadata_path(current_launch_root), asdict(stopped))
    print(json.dumps(asdict(stopped), indent=2, ensure_ascii=False))
    return 0
