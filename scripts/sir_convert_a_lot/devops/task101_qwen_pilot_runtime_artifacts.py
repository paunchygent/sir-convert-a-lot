"""Artifact and payload parsing helpers for the detached Task 101 runtime.

Purpose:
    Keep JSON artifact loading, subprocess fallback, and Docker inspect payload
    validation out of the main Task 101 runtime orchestration module.

Relationships:
    - Imported by `task101_qwen_pilot_runtime.py` for status inspection.
    - Reused indirectly by the detached launcher tests that exercise
      `inspect_detached_pilot`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _load_optional_json(path: Path) -> dict[str, object] | None:
    """Load one optional JSON object from disk, retrying via sudo if needed."""
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except PermissionError:
        raw_payload = subprocess_checked(
            ["sudo", "-n", "cat", path.as_posix()],
            label="sudo cat task101 detached artifact",
        )
        loaded = json.loads(raw_payload)
    if not isinstance(loaded, dict):
        raise SystemExit(f"Expected one JSON object in `{path.as_posix()}`.")
    return loaded


def subprocess_checked(command: list[str], *, label: str) -> str:
    """Run one subprocess command and return stdout or raise on failure."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Detached Task 101 inspect payload returned malformed `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Detached Task 101 inspect payload returned malformed `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer value from a Docker inspect payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Detached Task 101 inspect payload returned malformed `{key}`.")
    return value
