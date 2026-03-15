"""Detached stop service for Qwen training launches.

Purpose:
    Own intentional detached training shutdown behavior and corresponding
    `DetachedStop` payload construction.

Relationships:
    - Used by host control-plane stop and schedule flows.
    - Consumes Docker execution from the shared runtime helpers.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import docker_checked
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch, DetachedStop

from .artifact_freshness import utc_now_iso


def stop_detached_training(launch: DetachedLaunch) -> DetachedStop:
    """Stop one detached training container intentionally."""
    stop_output = docker_checked(
        ["stop", "--time", "300", launch.container_name],
        label="docker stop qwen detached training",
    )
    return DetachedStop(
        stopped_at=utc_now_iso(),
        launch_id=launch.launch_id,
        container_name=launch.container_name,
        container_id=launch.container_id,
        stop_output=stop_output.strip(),
    )
