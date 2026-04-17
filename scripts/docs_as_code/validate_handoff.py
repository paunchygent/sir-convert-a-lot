"""Validate the repo-local handoff and long-term-memory doorway.

Purpose:
    Enforce the lightweight `.codex/handoff.md` and
    `.codex/long-term-memory/` topology used by this repository's agent
    governance surface.

Relationships:
    - Validates session handoff topology separately from `docs-validate`.
    - Exposed as `pdm run handoff-validate`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.docs_as_code.common import ROOT

HANDOFF_PATH = ROOT / ".codex" / "handoff.md"
LTM_INDEX_PATH = ROOT / ".codex" / "long-term-memory" / "index.md"
LTM_ENTRIES_DIR = ROOT / ".codex" / "long-term-memory" / "entries"
HANDOFF_MAX_LINES = 200
LTM_ENTRY_FILENAME_PREFIX = "session-"


def _repo_path(path: Path) -> str:
    """Return a stable repository-relative path."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _has_frontmatter(path: Path) -> bool:
    """Return whether a markdown file starts with a YAML frontmatter fence."""
    try:
        return path.read_text(encoding="utf-8").startswith("---\n")
    except OSError:
        return False


def validate_handoff() -> list[str]:
    """Return actionable handoff validation failures."""
    errors: list[str] = []

    if not HANDOFF_PATH.exists():
        errors.append(".codex/handoff.md: missing required handoff file")
    else:
        text = HANDOFF_PATH.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        if line_count > HANDOFF_MAX_LINES:
            errors.append(
                ".codex/handoff.md: "
                f"{line_count} lines exceeds {HANDOFF_MAX_LINES}; move durable history to "
                ".codex/long-term-memory/entries/ and keep only active next-action state"
            )
        if any(line.startswith("# ") for line in text.splitlines()):
            errors.append(
                ".codex/handoff.md: H1 headings are not allowed; frontmatter title is canonical"
            )
        if not _has_frontmatter(HANDOFF_PATH):
            errors.append(".codex/handoff.md: missing YAML frontmatter")

    if not LTM_INDEX_PATH.exists():
        errors.append(".codex/long-term-memory/index.md: missing required memory index")
    elif not _has_frontmatter(LTM_INDEX_PATH):
        errors.append(".codex/long-term-memory/index.md: missing YAML frontmatter")

    if not LTM_ENTRIES_DIR.exists():
        errors.append(".codex/long-term-memory/entries/: missing required entries directory")
    else:
        entries = sorted(LTM_ENTRIES_DIR.glob("*.md"))
        if not entries:
            errors.append(
                ".codex/long-term-memory/entries/: add at least one retained memory entry"
            )

        index_text = LTM_INDEX_PATH.read_text(encoding="utf-8") if LTM_INDEX_PATH.exists() else ""
        for entry in entries:
            display = _repo_path(entry)
            if not entry.name.startswith(LTM_ENTRY_FILENAME_PREFIX):
                errors.append(f"{display}: session-*.md required")
            if not _has_frontmatter(entry):
                errors.append(f"{display}: missing YAML frontmatter")
            if entry.name not in index_text:
                errors.append(f"{display}: not referenced from .codex/long-term-memory/index.md")

    return errors


def main() -> int:
    """CLI entry point."""
    errors = validate_handoff()
    if errors:
        print("handoff-validate: failed")
        for error in errors:
            print(error)
        return 1
    print("handoff-validate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
