"""Artifact I/O helpers for Qwen training status and report payloads.

Purpose:
    Own deterministic JSON writing and launch-tracking metadata merge behavior
    for Qwen training artifacts.

Relationships:
    - Used by status writers, report builders, and evaluator surfaces.
    - Serves as the single canonical artifact-writing owner after Qwen architecture boundary.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_launch_tracking_metadata(
    launch_metadata_path: Path,
    *,
    tracking: dict[str, object],
) -> None:
    """Merge live tracker metadata into the detached launch artifact."""
    if not launch_metadata_path.exists():
        return
    payload = json.loads(launch_metadata_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Launch metadata was malformed while merging tracking data.")
    payload["tracking"] = tracking
    write_json(launch_metadata_path, payload)


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
