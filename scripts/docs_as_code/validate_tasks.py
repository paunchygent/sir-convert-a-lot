"""Validate docs/backlog frontmatter and template structure.

Purpose:
    Enforce strict planning-document quality for `docs/backlog/` by validating
    required frontmatter keys, type values, required
    template sections, and folder/type alignment.

Relationships:
    - Uses `scripts.docs_as_code.task_templates` as template source of truth.
    - Invoked by `pdm run validate-tasks`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.docs_as_code.common import BACKLOG_DIR, ROOT
from scripts.docs_as_code.task_templates import TEMPLATES, invalid_title_prefixes, subdirectory_for

REQUIRED_KEYS = (
    "id",
    "title",
    "type",
    "status",
    "priority",
    "created",
    "last_updated",
)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, object] | None, str | None]:
    """Parse YAML frontmatter from markdown text."""
    if not text.startswith("---"):
        return None, "missing frontmatter start"

    match = FRONTMATTER_RE.match(text)
    if match is None:
        return None, "missing frontmatter end"

    try:
        raw = yaml.safe_load(match.group(1)) or {}
    except Exception as exc:  # pragma: no cover - defensive parse error path
        return None, f"invalid YAML frontmatter: {exc}"

    if not isinstance(raw, dict):
        return None, "frontmatter must be a mapping"

    frontmatter: dict[str, object] = {str(key): value for key, value in raw.items()}
    return frontmatter, None


def extract_h1(text: str) -> str | None:
    """Extract first markdown H1 value from body after frontmatter."""
    match = FRONTMATTER_RE.match(text)
    body = text[match.end() :] if match is not None else text
    match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def repo_relative(path: Path) -> str:
    """Return repository-relative path string."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def validate_sections(path: Path, text: str, item_type: str) -> list[str]:
    """Validate required template sections for an item type."""
    errors: list[str] = []
    template = TEMPLATES.get(item_type)
    if template is None:
        return errors

    for section in template.sections:
        section_marker = f"## {section}"
        if section_marker not in text:
            errors.append(f"{repo_relative(path)}: missing required section '{section_marker}'")

    return errors


def validate_location(path: Path, item_type: str) -> list[str]:
    """Validate that file location matches backlog type semantics."""
    errors: list[str] = []
    rel = path.relative_to(BACKLOG_DIR)
    parts = rel.parts
    expected_subdir = subdirectory_for(item_type)

    if expected_subdir:
        if len(parts) < 2 or parts[0] != expected_subdir:
            errors.append(
                f"{repo_relative(path)}: type '{item_type}' must be stored under "
                f"docs/backlog/{expected_subdir}/"
            )
    else:
        if len(parts) != 1:
            errors.append(
                f"{repo_relative(path)}: type '{item_type}' must be stored at docs/backlog root"
            )

    if item_type == "task-log" and rel.name != "current.md":
        errors.append(f"{repo_relative(path)}: task-log file must be named current.md")

    if item_type == "reference" and len(parts) == 1:
        if rel.name != "README.md" and not rel.name.startswith("README-"):
            errors.append(
                f"{repo_relative(path)}: root reference filename should be README.md or README-*.md"
            )

    return errors


def validate_file(path: Path) -> list[str]:
    """Validate one backlog document."""
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    frontmatter, parse_error = parse_frontmatter(text)
    if parse_error is not None:
        return [f"{repo_relative(path)}: {parse_error}"]
    assert frontmatter is not None

    for key in REQUIRED_KEYS:
        if key not in frontmatter:
            errors.append(f"{repo_relative(path)}: missing required key '{key}'")

    item_type = str(frontmatter.get("type", "")).strip()
    if item_type not in TEMPLATES:
        errors.append(f"{repo_relative(path)}: unsupported type '{item_type}'")
        return errors

    title = str(frontmatter.get("title", "")).strip()
    if not title:
        errors.append(f"{repo_relative(path)}: title must be non-empty")
    else:
        lowered = title.lower()
        for prefix in invalid_title_prefixes():
            if lowered.startswith(prefix):
                errors.append(
                    f"{repo_relative(path)}: title should not start with "
                    f"'{prefix.strip()}' since type already exists in frontmatter"
                )
                break

    h1 = extract_h1(text)
    if h1 is not None:
        errors.append(
            f"{repo_relative(path)}: top-level markdown H1 headings are not allowed; "
            "frontmatter title is canonical"
        )

    errors.extend(validate_location(path, item_type))
    errors.extend(validate_sections(path, text, item_type))

    return errors


def main() -> None:
    """Run validation on docs/backlog markdown files."""
    if not BACKLOG_DIR.exists():
        raise SystemExit("docs/backlog is missing")

    backlog_files = sorted(BACKLOG_DIR.rglob("*.md"))
    all_errors: list[str] = []

    for backlog_file in backlog_files:
        all_errors.extend(validate_file(backlog_file))

    if all_errors:
        for error in all_errors:
            print(error)
        raise SystemExit(1)

    print(f"Validated {len(backlog_files)} backlog files")


if __name__ == "__main__":
    main()
