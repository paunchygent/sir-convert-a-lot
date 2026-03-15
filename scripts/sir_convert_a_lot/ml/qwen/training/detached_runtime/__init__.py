"""Bounded detached-runtime package for Qwen training control-plane flows.

Purpose:
    Expose the canonical detached launch, inspect, stop, id, snapshot, and
    command-building surfaces after the Story 28 god-file split.

Relationships:
    - Imported by control-plane use cases, schedule control, and diagnostics.
    - Replaces the former mixed-concern `training.orchestrator` module.
"""

from .artifact_freshness import load_optional_json
from .command_builder import build_detached_training_command
from .ids import default_container_name, default_launch_id
from .inspect_service import inspect_detached_training
from .launch_service import launch_detached_training
from .paths import run_root_for_launch
from .settings_snapshot import snapshot_settings
from .stop_service import stop_detached_training

__all__ = [
    "build_detached_training_command",
    "default_container_name",
    "default_launch_id",
    "inspect_detached_training",
    "launch_detached_training",
    "load_optional_json",
    "run_root_for_launch",
    "snapshot_settings",
    "stop_detached_training",
]
