"""Detached launch identity helpers for Qwen training.

Purpose:
    Own deterministic launch and container naming for detached Qwen training
    and diagnostic runs.

Relationships:
    - Imported by control-plane use cases when creating new detached launches.
    - Shared by detached runtime services and schedule/diagnostic flows.
"""

from __future__ import annotations

from datetime import UTC, datetime


def default_container_name(launch_id: str) -> str:
    """Return the deterministic container name for one training launch."""
    return f"qwen-train-{launch_id}"


def default_launch_id() -> str:
    """Return one deterministic launch id for a new training run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
