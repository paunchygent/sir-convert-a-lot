"""Create a new documentation file with contract-compliant frontmatter.

Purpose:
    Generate markdown documents under `docs/` using consistent YAML frontmatter
    so `pdm run validate-docs` passes by default.

Relationships:
    - Uses `scripts.docs_as_code.common` helpers.
    - Validated by `scripts.docs_as_code.validate_docs`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.docs_as_code.common import DOCS_DIR, ensure_parent, slugify, today_iso


def infer_doc_type(relative_path: Path) -> str:
    """Infer document type from the first path segment under docs/."""
    if not relative_path.parts:
        return "spec"

    top = relative_path.parts[0]
    if top == "converters":
        return "converter"
    if top == "decisions":
        return "decision"
    if top == "runbooks":
        return "runbook"
    if top == "tasks":
        return "task"
    if top == "_meta":
        return "meta"
    return "spec"


def default_id(doc_type: str, target: Path) -> str:
    """Build a default ID for the new document."""
    stem_slug = slugify(target.stem)

    if doc_type == "converter":
        return f"CONV-{stem_slug}"

    if doc_type == "decision":
        prefix = target.name.split("-", 1)[0]
        if prefix.isdigit() and len(prefix) == 4:
            return f"ADR-{prefix}"
        return f"ADR-{stem_slug}"

    if doc_type == "runbook":
        suffix = stem_slug.replace("runbook-", "")
        return f"RUN-{suffix}"

    if doc_type == "meta":
        return f"META-{stem_slug}"

    if doc_type == "task":
        return stem_slug

    return f"SPEC-{stem_slug}"


def default_status(doc_type: str) -> str:
    """Return a default status for new docs by type."""
    if doc_type == "decision":
        return "proposed"
    if doc_type == "task":
        return "proposed"
    return "draft"


def default_title(relative_path: Path) -> str:
    """Derive human-readable title from target filename."""
    return relative_path.stem.replace("_", " ").replace("-", " ").title()


def main() -> None:
    """Parse arguments and write a new doc file."""
    parser = argparse.ArgumentParser(description="Create a docs markdown file under docs/.")
    parser.add_argument("path", help="Relative path under docs/, e.g. runbooks/runbook-example.md")
    parser.add_argument("--title", default="", help="Optional document title")
    parser.add_argument("--type", default="", help="Override inferred type")
    parser.add_argument("--status", default="", help="Override default status")
    parser.add_argument("--id", default="", help="Override generated ID")
    parser.add_argument(
        "--owner",
        action="append",
        default=[],
        help="Owner value; repeat for multiple entries (default: platform)",
    )
    args = parser.parse_args()

    relative_path = Path(args.path)
    target = DOCS_DIR / relative_path
    if target.suffix == "":
        target = target.with_suffix(".md")

    if target.exists():
        raise SystemExit(f"Target already exists: {target}")

    doc_type = args.type if args.type else infer_doc_type(relative_path)
    title = args.title if args.title else default_title(relative_path)
    status = args.status if args.status else default_status(doc_type)
    doc_id = args.id if args.id else default_id(doc_type, target)
    owners = args.owner if args.owner else ["platform"]
    created = today_iso()

    owners_yaml = "\n".join(f"  - {owner}" for owner in owners)

    content = f"""---
type: {doc_type}
id: {doc_id}
title: {title}
status: {status}
created: {created}
updated: {created}
owners:
{owners_yaml}
tags: []
links: []
---
## Purpose

TBD.
"""

    ensure_parent(target)
    target.write_text(content, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
