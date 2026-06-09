"""Backlog document lookup support for docs-as-code tests.

Purpose:
    Resolve governed backlog documents by their domain slug so tests can assert
    planning-state behavior without depending on numeric backlog identifiers.

Relationships:
    - Used by audio-transcription docs guards that read Sir Convert backlog
      records as runtime gating authority.
    - Keeps repository-relative path assertions aligned with generated backlog
      frontmatter links.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def backlog_document_path(*, category: str, title_slug: str) -> Path:
    """Return the single backlog document whose filename ends with the domain slug."""
    directory = REPO_ROOT / "docs" / "backlog" / category
    matches = sorted(
        path for path in directory.glob("*.md") if path.name.endswith(f"{title_slug}.md")
    )
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one backlog document in {directory} ending with "
            f"{title_slug}.md; found {len(matches)}."
        )
    return matches[0]


def repo_relative_path(path: Path) -> str:
    """Return a repository-relative POSIX path for frontmatter link assertions."""
    return path.relative_to(REPO_ROOT).as_posix()
