"""Aggregate Sir Convert docs validation with optional path scoping.

Purpose:
    Expose the public `pdm run docs-validate [paths...]` contract for governed
    docs and backlog docs.

Relationships:
    - Wraps `scripts.docs_as_code.validate_tasks` for backlog markdown files.
    - Wraps `scripts.docs_as_code.validate_docs` for non-backlog docs/rules.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.docs_as_code import validate_docs, validate_tasks
from scripts.docs_as_code.common import BACKLOG_DIR, ROOT


def main(argv: Sequence[str] | None = None) -> int:
    """Run aggregate or explicit-path docs validation."""
    paths = [Path(path) for path in (argv or [])]
    if not paths:
        return _run_aggregate_validation()
    return _run_scoped_validation(paths)


def _run_aggregate_validation() -> int:
    """Run the full docs validation gate."""
    return _run_commands(
        [
            [sys.executable, "-m", "scripts.docs_as_code.validate_tasks"],
            [sys.executable, "-m", "scripts.docs_as_code.validate_docs"],
        ]
    )


def _run_scoped_validation(paths: Sequence[Path]) -> int:
    """Run docs validation only for supplied paths."""
    markdown_paths = [_normalize_user_path(path) for path in paths if path.suffix == ".md"]
    backlog_paths = [path for path in markdown_paths if _is_backlog_path(path)]
    non_backlog_paths = [path for path in markdown_paths if not _is_backlog_path(path)]

    failures = 0
    if backlog_paths:
        failures += _validate_backlog_paths(backlog_paths)
    if non_backlog_paths:
        failures += _validate_non_backlog_paths(non_backlog_paths)
    return 1 if failures else 0


def _validate_backlog_paths(paths: Sequence[Path]) -> int:
    """Validate supplied backlog markdown files."""
    errors: list[str] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        errors.extend(validate_tasks.validate_file(path))
    if not errors:
        print(f"Validated {len(paths)} scoped backlog files")
        return 0
    for error in errors:
        print(error)
    return 1


def _validate_non_backlog_paths(paths: Sequence[Path]) -> int:
    """Validate supplied docs/rules markdown files without global index checks."""
    contract = validate_docs.load_contract()
    docs_contract = validate_docs.to_mapping(contract.get("docs"))
    rules_contract = validate_docs.to_mapping(contract.get("rules"))
    if docs_contract is None or rules_contract is None:
        print("[docs-validate] Invalid contract sections for docs/rules.")
        return 1

    violations: list[validate_docs.Violation] = []
    docs_count = 0
    rules_count = 0
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        relative_path = _repo_relative(path)
        if relative_path.startswith("docs/"):
            docs_count += 1
            violations.extend(validate_docs.validate_doc(path, docs_contract))
        elif relative_path.startswith(".codex/rules/"):
            rules_count += 1
            violations.extend(validate_docs.validate_rule(path, rules_contract))

    if not violations:
        print(f"Validated scoped docs={docs_count} rules={rules_count}")
        return 0

    print("\n[docs-validate] Contract violations found:\n")
    for violation in violations:
        print(f"- {violation.path}: {violation.message}")
    return 1


def _run_commands(commands: Sequence[Sequence[str]]) -> int:
    """Run child validation commands and mirror their output."""
    failures = 0
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            failures += 1
    return failures


def _normalize_user_path(path: Path) -> Path:
    """Resolve a user path against the repository root."""
    return path if path.is_absolute() else ROOT / path


def _repo_relative(path: Path) -> str:
    """Return a repository-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _is_backlog_path(path: Path) -> bool:
    """Return whether the path is a docs/backlog markdown file."""
    try:
        path.resolve().relative_to(BACKLOG_DIR.resolve())
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
