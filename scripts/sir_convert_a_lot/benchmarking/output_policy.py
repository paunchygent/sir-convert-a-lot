"""Programmatic output-governance checks for benchmark artifacts.

Purpose:
    Enforce repository policy that generated benchmark/evaluation output must
    not be written into `docs/reference`.

Relationships:
    - Used by benchmark runners before writing JSON/Markdown/artifact outputs.
    - Keeps generated output in `build/` (or other non-doc paths) by default.
"""

from __future__ import annotations

from pathlib import Path


def _to_absolute(path: Path) -> Path:
    """Return absolute normalized path for relative or absolute input."""
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() / path).resolve()


def enforce_generated_output_path(path: Path, *, label: str) -> None:
    """Raise when a generated-output path targets `docs/reference`."""
    docs_reference_root = _to_absolute(Path("docs/reference"))
    target_path = _to_absolute(path)
    if target_path == docs_reference_root or docs_reference_root in target_path.parents:
        raise ValueError(
            f"{label} must not target docs/reference. "
            "Use a build/ path for generated benchmark/evaluation output."
        )
