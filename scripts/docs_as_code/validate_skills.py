"""Validate repo-local Codex skill metadata.

Purpose:
    Keep `.codex/skills/*/SKILL.md` discoverable by requiring the minimal
    frontmatter that agent skill routing depends on.

Relationships:
    - Validates the repo-local skill delivery surface under `.codex/skills/`.
    - Exposed as `pdm run skills-validate`.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.docs_as_code.common import ROOT

SKILLS_ROOT = ROOT / ".codex" / "skills"
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
REQUIRED_FIELDS = ("name", "description")


def _repo_path(path: Path) -> str:
    """Return a stable repository-relative path."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _frontmatter(path: Path) -> dict[str, object] | None:
    """Parse a skill frontmatter block."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return None
    raw = yaml.safe_load(match.group(1)) or {}
    if not isinstance(raw, dict):
        return None
    return {str(key): value for key, value in raw.items()}


def validate_skills() -> list[str]:
    """Return skill metadata validation failures."""
    errors: list[str] = []
    skill_files = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
    if not skill_files:
        return [".codex/skills/: no SKILL.md files found"]

    for skill_file in skill_files:
        display = _repo_path(skill_file)
        try:
            frontmatter = _frontmatter(skill_file)
        except yaml.YAMLError as exc:
            errors.append(f"{display}: invalid YAML frontmatter: {exc}")
            continue

        if frontmatter is None:
            errors.append(f"{display}: missing YAML frontmatter")
            continue

        for field_name in REQUIRED_FIELDS:
            value = frontmatter.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{display}: missing required frontmatter field '{field_name}'")

    return errors


def main() -> int:
    """CLI entry point."""
    errors = validate_skills()
    if errors:
        print("skills-validate: failed")
        for error in errors:
            print(error)
        return 1
    print("skills-validate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
