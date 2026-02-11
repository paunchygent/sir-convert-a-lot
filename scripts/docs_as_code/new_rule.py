"""Create a new rule file with contract-compliant frontmatter.

Purpose:
    Generate a numbered rule in `.agents/rules/` with required metadata keys.

Relationships:
    - Uses `scripts.docs_as_code.common` utilities.
    - Validated by `scripts.docs_as_code.validate_docs`.
"""

from __future__ import annotations

import argparse

from scripts.docs_as_code.common import (
    RULES_DIR,
    ensure_parent,
    next_numeric_prefix,
    slugify,
    today_iso,
)


def main() -> None:
    """Parse args and write the new rule file."""
    parser = argparse.ArgumentParser(description="Create a new rule file in .agents/rules/.")
    parser.add_argument("name", help="Rule name")
    parser.add_argument("--trigger", default="model_decision", help="Rule trigger value")
    parser.add_argument("--status", default="active", help="Rule status")
    parser.add_argument(
        "--owner",
        action="append",
        default=[],
        help="Owner value; repeat for multiple entries (default: platform)",
    )
    args = parser.parse_args()

    prefix = next_numeric_prefix(RULES_DIR)
    slug = slugify(args.name)
    target = RULES_DIR / f"{prefix}-{slug}.md"

    owners = args.owner if args.owner else ["platform"]
    owners_yaml = "\n".join(f"  - {owner}" for owner in owners)
    created = today_iso()

    ensure_parent(target)
    content = f"""---
trigger: {args.trigger}
rule_id: RULE-{prefix}
title: {args.name}
status: {args.status}
created: {created}
owners:
{owners_yaml}
tags: []
scope: repo
---
## Purpose

TBD.

## Rules

- TBD.
"""
    target.write_text(content, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
