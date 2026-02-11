"""Generate a markdown index for backlog planning files.

Purpose:
    Create a stable task index output for docs-as-code reporting workflows.

Relationships:
    - Used by `pdm run index-tasks`.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def extract_value(header: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*'?(.*?)'?$", header, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Index backlog markdown files into a report.")
    parser.add_argument("--root", required=True, help="Backlog root directory")
    parser.add_argument("--out", required=True, help="Output markdown file")
    parser.add_argument(
        "--fail-on-missing", action="store_true", help="Fail if required keys are missing"
    )
    args = parser.parse_args()

    root = Path(args.root)
    out = Path(args.out)
    task_files = sorted(path for path in root.rglob("*.md"))

    rows: list[str] = []
    missing_errors: list[str] = []

    for task_file in task_files:
        text = task_file.read_text(encoding="utf-8")
        parts = text.split("\n---\n", 1)
        header = parts[0] if text.startswith("---\n") and len(parts) > 1 else ""

        task_id = extract_value(header, "id")
        title = extract_value(header, "title")
        status = extract_value(header, "status")
        priority = extract_value(header, "priority")

        if args.fail_on_missing:
            if not task_id:
                missing_errors.append(f"{task_file}: missing id")
            if not title:
                missing_errors.append(f"{task_file}: missing title")

        rows.append(f"| `{task_id}` | {title} | {status} | {priority} | `{task_file}` |")

    if missing_errors:
        for err in missing_errors:
            print(err)
        raise SystemExit(1)

    report = [
        "# Backlog Index",
        "",
        "| ID | Title | Status | Priority | Path |",
        "|---|---|---|---|---|",
        *rows,
        "",
    ]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
