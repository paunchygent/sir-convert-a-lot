"""Common helpers for docs-as-code scripts.

Purpose:
    Provide shared filesystem and formatting utilities for task/doc/rule
    automation scripts in this repository.

Relationships:
    - Used by `scripts.docs_as_code.new_task`, `new_doc`, `new_rule`,
      `validate_tasks`, `validate_docs`, and `index_tasks`.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
BACKLOG_DIR = DOCS_DIR / "backlog"
PROGRAMMES_DIR = BACKLOG_DIR / "programmes"
EPICS_DIR = BACKLOG_DIR / "epics"
STORIES_DIR = BACKLOG_DIR / "stories"
TASKS_DIR = BACKLOG_DIR / "tasks"
REVIEWS_DIR = BACKLOG_DIR / "reviews"
RULES_DIR = ROOT / ".agents" / "rules"


def now_utc_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_iso() -> str:
    """Return current UTC date in ISO format."""
    return date.today().isoformat()


def slugify(value: str) -> str:
    """Convert an arbitrary label into lowercase kebab-case."""
    compact = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return compact.lower()


def ensure_parent(path: Path) -> None:
    """Create parent directories for a target file path."""
    path.parent.mkdir(parents=True, exist_ok=True)


def next_numeric_prefix(directory: Path, width: int = 3) -> str:
    """Return next zero-padded numeric prefix from files in a directory."""
    max_id = 0
    for file_path in directory.glob("*.md*"):
        match = re.match(r"^(\d+)", file_path.name)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"{max_id + 1:0{width}d}"


def next_prefixed_index(directory: Path, prefix: str, width: int = 4) -> str:
    """Return next index for files named `<prefix>-<number>-...` in a directory."""
    max_id = 0
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)(?:-|\.|$)")
    for file_path in directory.glob("*.md*"):
        match = pattern.match(file_path.name)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"{max_id + 1:0{width}d}"
