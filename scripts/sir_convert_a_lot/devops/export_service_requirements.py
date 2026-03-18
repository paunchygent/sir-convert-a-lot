"""Export filtered runtime requirements for the HTTP service image.

Purpose:
    Generate a locked production requirements file for the Sir Convert-a-Lot
    HTTP service image while excluding CUDA-oriented PyTorch packages that are
    replaced by ROCm wheels during the image build.

Relationships:
    - Consumes `pdm export --prod --without-hashes` from the repository root.
    - Used by the root `Dockerfile` dependency-builder stage.
    - Covered by `tests/sir_convert_a_lot/test_export_service_requirements.py`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

DEFAULT_EXCLUDED_PACKAGES = frozenset(
    {
        "cuda-bindings",
        "torch",
        "torchaudio",
        "torchvision",
        "triton",
    }
)
DEFAULT_EXCLUDED_PREFIXES = ("nvidia-",)
_REQUIREMENT_NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")


def _canonicalize_package_name(package_name: str) -> str:
    """Normalize a package name using the canonical PEP 503-compatible form."""
    return re.sub(r"[-_.]+", "-", package_name).lower()


def _canonical_requirement_name(requirement_line: str) -> str | None:
    """Return the normalized package name for a requirement line when possible."""
    stripped_line = requirement_line.strip()
    if stripped_line == "" or stripped_line.startswith(("#", "-")):
        return None
    requirement_match = _REQUIREMENT_NAME_PATTERN.match(stripped_line)
    if requirement_match is None:
        return None
    return _canonicalize_package_name(requirement_match.group(1))


def _should_exclude_requirement(
    requirement_line: str,
    *,
    excluded_packages: frozenset[str],
    excluded_prefixes: tuple[str, ...],
) -> bool:
    """Return whether the requirement line should be dropped from the export."""
    normalized_name = _canonical_requirement_name(requirement_line)
    if normalized_name is None:
        return False
    if normalized_name in excluded_packages:
        return True
    return any(normalized_name.startswith(prefix) for prefix in excluded_prefixes)


def filter_requirement_lines(
    exported_requirements: str,
    *,
    excluded_packages: frozenset[str] = DEFAULT_EXCLUDED_PACKAGES,
    excluded_prefixes: tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES,
) -> str:
    """Filter CUDA-oriented packages from an exported requirements payload."""
    filtered_lines: list[str] = []
    for line in exported_requirements.splitlines():
        if _should_exclude_requirement(
            line,
            excluded_packages=excluded_packages,
            excluded_prefixes=excluded_prefixes,
        ):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines).rstrip() + "\n"


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the requirements export helper."""
    parser = argparse.ArgumentParser(
        description="Export production requirements for the service image without CUDA wheels."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
        help="Repository root that contains pyproject.toml and pdm.lock.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write the filtered requirements file.",
    )
    return parser.parse_args()


def main() -> None:
    """Export, filter, and persist the service runtime requirements file."""
    args = _parse_args()
    exported_requirements = subprocess.run(
        ["pdm", "export", "--prod", "--without-hashes", "--format", "requirements"],
        cwd=args.project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    filtered_requirements = filter_requirement_lines(exported_requirements)
    args.output.write_text(filtered_requirements, encoding="utf-8")


if __name__ == "__main__":
    main()
