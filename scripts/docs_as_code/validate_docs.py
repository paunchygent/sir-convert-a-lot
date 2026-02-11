"""Validate docs and rules against the repository docs contract.

Purpose:
    Enforce YAML frontmatter and metadata conventions for `docs/` and
    `.agents/rules/` using a contract file.

Relationships:
    - Source contract: `docs/_meta/docs-contract.yaml`
    - Invoked by: `pdm run validate-docs`
    - Complements: `scripts.docs_as_code.validate_tasks`
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from scripts.docs_as_code.common import ROOT

YamlMapping = dict[str, object]
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
CONTRACT_PATH = ROOT / "docs" / "_meta" / "docs-contract.yaml"


@dataclass(frozen=True)
class Violation:
    """Represents a single contract violation."""

    path: str
    message: str


def normalize_path(path: Path) -> str:
    """Return a repo-relative normalized path string."""
    return str(path.relative_to(ROOT)).replace("\\", "/")


def to_mapping(value: object) -> YamlMapping | None:
    """Convert an arbitrary object to a string-key mapping when possible."""
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def to_str_list(value: object) -> list[str]:
    """Convert a YAML sequence to a list of strings."""
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def load_contract() -> YamlMapping:
    """Load and validate base contract structure."""
    if not CONTRACT_PATH.exists():
        raise SystemExit(f"[docs-validate] Missing contract: {normalize_path(CONTRACT_PATH)}")

    raw = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8")) or {}
    contract = to_mapping(raw)
    if contract is None:
        raise SystemExit("[docs-validate] Contract must be a YAML mapping.")

    docs_block = to_mapping(contract.get("docs"))
    rules_block = to_mapping(contract.get("rules"))
    if docs_block is None:
        raise SystemExit("[docs-validate] Contract missing mapping key: docs")
    if rules_block is None:
        raise SystemExit("[docs-validate] Contract missing mapping key: rules")

    return contract


def parse_frontmatter(text: str) -> tuple[YamlMapping | None, str | None]:
    """Parse YAML frontmatter from markdown-like content."""
    if not text.startswith("---"):
        return None, "Missing YAML frontmatter block at top of file."

    match = FRONTMATTER_RE.match(text)
    if match is None:
        return None, "Frontmatter not closed. Expected second '---' delimiter."

    try:
        raw_frontmatter = yaml.safe_load(match.group(1)) or {}
    except Exception as exc:  # pragma: no cover - defensive parse error path
        return None, f"Invalid YAML in frontmatter: {exc}"

    frontmatter = to_mapping(raw_frontmatter)
    if frontmatter is None:
        return None, "Frontmatter must parse to a mapping/object."

    return frontmatter, None


def extract_body(text: str) -> str:
    """Return file body content after frontmatter."""
    match = FRONTMATTER_RE.match(text)
    return text[match.end() :] if match is not None else text


def first_h1(body: str) -> str | None:
    """Return the first markdown H1 heading text when present."""
    match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def is_iso_date(value: object) -> bool:
    """Return True when value is an ISO date (YYYY-MM-DD)."""
    if isinstance(value, date):
        return True
    if isinstance(value, str):
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False
    return False


def validate_owners(path: str, frontmatter: YamlMapping) -> list[Violation]:
    """Validate optional owners frontmatter key."""
    owners = frontmatter.get("owners")
    if owners is None:
        return []
    if isinstance(owners, str):
        return []
    if isinstance(owners, list) and all(isinstance(item, str) for item in owners):
        return []
    return [Violation(path, "Frontmatter 'owners' must be a string or list of strings.")]


def collect_paths(patterns: list[str]) -> list[Path]:
    """Collect existing files from contract glob patterns."""
    paths: list[Path] = []
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.is_file():
                paths.append(path)
    unique_sorted = sorted({path.resolve() for path in paths})
    return [Path(path) for path in unique_sorted]


def match_section(path: str, sections: list[YamlMapping]) -> YamlMapping | None:
    """Match a docs path to the most specific configured section folder."""
    candidates: list[tuple[int, YamlMapping]] = []
    for section in sections:
        folder = str(section.get("folder", "")).strip("/")
        if not folder:
            continue
        if path == folder or path.startswith(folder + "/"):
            candidates.append((len(folder), section))
    if not candidates:
        return None
    candidates.sort(key=lambda entry: entry[0], reverse=True)
    return candidates[0][1]


def validate_doc(path: Path, docs_contract: YamlMapping) -> list[Violation]:
    """Validate one docs markdown file against docs contract."""
    norm = normalize_path(path)
    violations: list[Violation] = []

    exempt = set(to_str_list(docs_contract.get("frontmatter_exempt")))
    if norm in exempt:
        return violations

    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, error = parse_frontmatter(text)
    if error is not None:
        return [Violation(norm, error)]
    assert frontmatter is not None

    h1 = first_h1(extract_body(text))
    if h1 is not None:
        violations.append(
            Violation(
                norm,
                "Top-level markdown H1 headings are not allowed; frontmatter title is canonical.",
            )
        )

    raw_sections = docs_contract.get("sections")
    if not isinstance(raw_sections, list):
        return [Violation(norm, "Contract docs.sections must be a list.")]

    sections: list[YamlMapping] = []
    for section in raw_sections:
        section_mapping = to_mapping(section)
        if section_mapping is not None:
            sections.append(section_mapping)

    section = match_section(norm, sections)
    if section is None:
        return [Violation(norm, "No docs contract section matched this path.")]

    filename_regex = str(section.get("filename_regex", ""))
    if filename_regex and re.match(filename_regex, path.name) is None:
        violations.append(
            Violation(norm, f"Filename does not match section regex: {filename_regex}")
        )

    common_required = to_str_list(docs_contract.get("common_required"))
    common_optional = set(to_str_list(docs_contract.get("common_optional")))
    section_required = to_str_list(section.get("required"))
    section_optional = set(to_str_list(section.get("optional")))

    for key in common_required + section_required:
        if key not in frontmatter:
            violations.append(Violation(norm, f"Missing required frontmatter key: '{key}'"))

    expected_type = section.get("type")
    if isinstance(expected_type, str) and frontmatter.get("type") != expected_type:
        violations.append(
            Violation(
                norm,
                f"Frontmatter type '{frontmatter.get('type')}' must equal '{expected_type}'.",
            )
        )

    allowed_types = to_str_list(section.get("type_one_of"))
    if allowed_types and str(frontmatter.get("type")) not in allowed_types:
        violations.append(
            Violation(
                norm,
                "Frontmatter type must be one of "
                f"{allowed_types}, got '{frontmatter.get('type')}'.",
            )
        )

    status_allowed = set(to_str_list(section.get("status_allowed")))
    status = frontmatter.get("status")
    if isinstance(status, str) and status_allowed and status not in status_allowed:
        violations.append(
            Violation(norm, f"Invalid status '{status}'. Allowed: {sorted(status_allowed)}")
        )

    id_regex = section.get("id_regex")
    if isinstance(id_regex, str) and "id" in frontmatter:
        if re.match(id_regex, str(frontmatter["id"])) is None:
            violations.append(Violation(norm, f"Frontmatter id does not match regex: {id_regex}"))

    if section.get("name") == "decision":
        match = re.match(r"^(\d{4})-", path.name)
        if match is not None and "id" in frontmatter:
            expected_id = f"ADR-{match.group(1)}"
            if str(frontmatter["id"]) != expected_id:
                violations.append(
                    Violation(norm, f"Decision id must match filename prefix: '{expected_id}'.")
                )

    for date_key in ("created", "updated", "last_updated"):
        value = frontmatter.get(date_key)
        if value is not None and not is_iso_date(value):
            violations.append(Violation(norm, f"Frontmatter '{date_key}' must be YYYY-MM-DD."))

    allowed_keys = set(common_required) | common_optional | set(section_required) | section_optional
    unknown_keys = sorted(set(frontmatter.keys()) - allowed_keys)
    if unknown_keys:
        violations.append(
            Violation(
                norm,
                f"Unknown frontmatter keys not allowed: {unknown_keys}."
                " Update docs/_meta/docs-contract.yaml if needed.",
            )
        )

    violations.extend(validate_owners(norm, frontmatter))
    return violations


def validate_rule(path: Path, rules_contract: YamlMapping) -> list[Violation]:
    """Validate one rule markdown/mdc file against rules contract."""
    norm = normalize_path(path)
    violations: list[Violation] = []

    exempt = set(to_str_list(rules_contract.get("frontmatter_exempt")))
    if norm in exempt:
        return violations

    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, error = parse_frontmatter(text)
    if error is not None:
        return [Violation(norm, error)]
    assert frontmatter is not None

    h1 = first_h1(extract_body(text))
    if h1 is not None:
        violations.append(
            Violation(
                norm,
                "Top-level markdown H1 headings are not allowed; frontmatter title is canonical.",
            )
        )

    required = to_str_list(rules_contract.get("required"))
    optional = set(to_str_list(rules_contract.get("optional")))

    for key in required:
        if key not in frontmatter:
            violations.append(Violation(norm, f"Missing required rule frontmatter key: '{key}'"))

    status_allowed = set(to_str_list(rules_contract.get("status_allowed")))
    status = frontmatter.get("status")
    if isinstance(status, str) and status_allowed and status not in status_allowed:
        violations.append(
            Violation(norm, f"Invalid status '{status}'. Allowed: {sorted(status_allowed)}")
        )

    rule_id_regex = rules_contract.get("rule_id_regex")
    if isinstance(rule_id_regex, str) and "rule_id" in frontmatter:
        if re.match(rule_id_regex, str(frontmatter["rule_id"])) is None:
            violations.append(Violation(norm, f"rule_id does not match regex: {rule_id_regex}"))

    trigger = frontmatter.get("trigger")
    if not isinstance(trigger, str):
        violations.append(Violation(norm, "Frontmatter 'trigger' must be a string."))

    for date_key in ("created", "updated"):
        value = frontmatter.get(date_key)
        if value is not None and not is_iso_date(value):
            violations.append(Violation(norm, f"Frontmatter '{date_key}' must be YYYY-MM-DD."))

    allowed_keys = set(required) | optional
    unknown_keys = sorted(set(frontmatter.keys()) - allowed_keys)
    if unknown_keys:
        violations.append(
            Violation(
                norm,
                f"Unknown rule frontmatter keys not allowed: {unknown_keys}."
                " Update docs/_meta/docs-contract.yaml if needed.",
            )
        )

    violations.extend(validate_owners(norm, frontmatter))
    return violations


def filter_user_paths(paths: list[str]) -> tuple[list[Path], list[Path]]:
    """Split user-provided paths into docs and rules files."""
    docs_targets: list[Path] = []
    rule_targets: list[Path] = []

    for raw_path in paths:
        candidate = (ROOT / raw_path).resolve()
        if not candidate.exists() or not candidate.is_file():
            continue
        norm = normalize_path(candidate)
        if norm.startswith("docs/") and candidate.suffix == ".md":
            docs_targets.append(candidate)
        if norm.startswith(".agents/rules/") and candidate.suffix == ".md":
            rule_targets.append(candidate)

    return docs_targets, rule_targets


def main(argv: list[str]) -> int:
    """Run docs/rules validation and return process exit code."""
    contract = load_contract()
    docs_contract = to_mapping(contract.get("docs"))
    rules_contract = to_mapping(contract.get("rules"))
    if docs_contract is None or rules_contract is None:
        print("[docs-validate] Invalid contract sections for docs/rules.")
        return 1

    if len(argv) > 1:
        docs_paths, rule_paths = filter_user_paths(argv[1:])
    else:
        docs_paths = collect_paths(to_str_list(docs_contract.get("include_globs")))
        rule_paths = collect_paths(to_str_list(rules_contract.get("include_globs")))

    violations: list[Violation] = []

    for path in docs_paths:
        violations.extend(validate_doc(path, docs_contract))

    for path in rule_paths:
        violations.extend(validate_rule(path, rules_contract))

    if violations:
        print("\n[docs-validate] Contract violations found:\n")
        for violation in violations:
            print(f"- {violation.path}: {violation.message}")
        print(
            "\nFix the issues above.\n"
            "Contract: docs/_meta/docs-contract.yaml\n"
            "Validator: scripts/docs_as_code/validate_docs.py\n"
        )
        return 1

    print(f"Validated docs={len(docs_paths)} rules={len(rule_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
