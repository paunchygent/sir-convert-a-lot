"""Artifact-writing helpers for Qwen training control-plane metadata.

Purpose:
    Provide deterministic JSON/Markdown artifact writes and latest-pointer
    persistence for detached training control-plane workflows.

Relationships:
    - Used by control-plane use cases and schedule control reporting.
    - Shares generated-output policy enforcement with benchmarking helpers.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path

from .launch_artifact_paths import latest_pointer_path


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def write_latest_pointer(output_root: Path, launch_root_path: Path) -> None:
    """Record the latest detached launch root for status inspection."""
    write_json(
        latest_pointer_path(output_root),
        {"launch_root": launch_root_path.as_posix()},
    )
