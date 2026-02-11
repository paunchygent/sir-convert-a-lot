"""Create a new planning document under docs/backlog.

Purpose:
    Generate contract-compliant backlog documents with type-specific structure.

Relationships:
    - Uses `scripts.docs_as_code.task_templates` as source of truth.
    - Validated by `scripts.docs_as_code.validate_tasks`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.docs_as_code.common import (
    BACKLOG_DIR,
    ensure_parent,
    next_prefixed_index,
    slugify,
    today_iso,
)
from scripts.docs_as_code.task_templates import (
    TEMPLATES,
    filename_prefix_for,
    subdirectory_for,
    supported_types,
)


def render_checklist(items: tuple[str, ...]) -> str:
    """Render checklist markdown entries."""
    if not items:
        return ""
    lines = [f"- [ ] {item}" for item in items]
    return "\n".join(lines)


def render_sections(task_type: str) -> str:
    """Render markdown sections according to template."""
    template = TEMPLATES[task_type]
    sections: list[str] = []

    for section in template.sections:
        sections.append(f"## {section}\n")

        if section == "Checklist":
            checklist = render_checklist(template.checklist)
            sections.append(f"{checklist}\n" if checklist else "- [ ] Items defined\n")
            continue

        if section in {"Acceptance Criteria", "Test Requirements", "Deliverables", "Findings"}:
            sections.append("- [ ] TBD\n")
            continue

        if section in {"Stories", "Active Epics", "Follow-up Actions"}:
            sections.append("1. TBD\n")
            continue

        sections.append("TBD.\n")

    return "\n".join(sections).rstrip() + "\n"


def resolve_target(task_type: str, title: str) -> tuple[str, Path]:
    """Resolve backlog ID and output path for a new planning document."""
    prefix = filename_prefix_for(task_type)
    subdir = subdirectory_for(task_type)
    slug = slugify(title)

    base_dir = BACKLOG_DIR / subdir if subdir else BACKLOG_DIR

    if task_type == "task-log":
        return "current-task-log", base_dir / "current.md"
    if task_type == "reference":
        return f"reference-{slug}", base_dir / f"README-{slug}.md"

    index = next_prefixed_index(base_dir, prefix, width=2)
    doc_id = f"{prefix}-{index}-{slug}"
    target = base_dir / f"{prefix}-{index}-{slug}.md"
    return doc_id, target


def main() -> None:
    """Parse args and write the backlog document."""
    parser = argparse.ArgumentParser(description="Create a planning document in docs/backlog/.")
    parser.add_argument("title", help="Document title")
    parser.add_argument("--type", default="task", choices=list(supported_types()))
    parser.add_argument("--priority", default="high", choices=["low", "medium", "high", "critical"])
    args = parser.parse_args()

    template = TEMPLATES[args.type]
    doc_id, target = resolve_target(args.type, args.title)

    if target.exists():
        raise SystemExit(f"Target already exists: {target}")

    today = today_iso()

    ensure_parent(target)
    content = f"""---
id: '{doc_id}'
title: '{args.title}'
type: '{args.type}'
status: '{template.status}'
priority: '{args.priority}'
created: '{today}'
last_updated: '{today}'
related: []
labels: []
---
# {args.title}

{template.intro}

{render_sections(args.type)}"""
    target.write_text(content, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
