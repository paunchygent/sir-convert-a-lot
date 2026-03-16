"""Launch-artifact path helpers for Qwen training control-plane flows.

Purpose:
    Define canonical launch-root artifact paths so control-plane use cases
    share one path convention owner.

Relationships:
    - Used by launch/resume/diagnose/eval/status/stop use cases.
    - Consumed by pointer resolution and artifact writing helpers.
"""

from __future__ import annotations

from pathlib import Path


def launch_root(output_root: Path, launch_id: str) -> Path:
    """Return the canonical verification root for one launch id."""
    return output_root / launch_id


def launch_metadata_path(launch_root_path: Path) -> Path:
    """Return the launch metadata path for one detached training run."""
    return launch_root_path / "launch.json"


def status_metadata_path(launch_root_path: Path) -> Path:
    """Return the status metadata path for one detached training run."""
    return launch_root_path / "status.json"


def status_markdown_path(launch_root_path: Path) -> Path:
    """Return the markdown status path for one detached training run."""
    return launch_root_path / "status.md"


def latest_pointer_path(output_root: Path) -> Path:
    """Return the pointer file that records the latest launch root."""
    return output_root / "latest-launch.json"


def stop_metadata_path(launch_root_path: Path) -> Path:
    """Return the stop metadata path for one detached training container."""
    return launch_root_path / "stop.json"
