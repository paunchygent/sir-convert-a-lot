"""Formula candidate evaluation output parsing and marker accounting.

Purpose:
    Normalize candidate text artifacts and known failure-marker counts for the
    Task 346/350 formula/OCR evidence harness.

Relationships:
    - Used by formula candidate execution and reporting helpers.
    - Shares marker definitions with tests that guard incident-class evidence.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Mapping, Sequence

from scripts.sir_convert_a_lot.devops.formula_candidate_eval_inputs import object_mapping

BAD_MARKERS = ("</formula", "\\mathbmath", "\\mathbf", "l o o l y")
TAIL_CHARS = 6000


def candidate_output_text(*, output_root: Path, stdout: str) -> str:
    """Extract candidate text from saved JSON outputs or stdout."""
    fragments: list[str] = []
    for path in sorted(output_root.rglob("*.json")):
        loaded = read_json_object(path)
        fragments.extend(json_text_fragments(loaded))
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or not is_candidate_text_artifact(path):
            continue
        fragments.append(path.read_text(encoding="utf-8", errors="replace"))
    if fragments:
        return "\n\n".join(fragments)
    return tail_text(stdout)


def is_candidate_text_artifact(path: Path) -> bool:
    """Return whether a candidate-produced file should count as output text."""
    if path.name in {"candidate-output.txt", "stdout.txt", "stderr.txt"}:
        return False
    return path.suffix.lower() in {".md", ".mmd", ".txt", ".tex"}


def json_text_fragments(value: object) -> list[str]:
    """Collect formula-like text fields from nested JSON structures."""
    fragments: list[str] = []
    if isinstance(value, dict):
        for key_obj, child in value.items():
            key = str(key_obj)
            if key in {"rec_formula", "formula", "latex", "text", "markdown"} and isinstance(
                child, str
            ):
                fragments.append(child)
            else:
                fragments.extend(json_text_fragments(child))
    elif isinstance(value, list):
        for child in value:
            fragments.extend(json_text_fragments(child))
    return fragments


def collect_marker_counts(text: str) -> dict[str, int]:
    """Count Docling page-window replay known bad output markers."""
    return {marker: text.count(marker) for marker in BAD_MARKERS}


def sum_marker_counts(results: Sequence[Mapping[str, object]]) -> dict[str, int]:
    """Sum marker counts across input results."""
    totals = {marker: 0 for marker in BAD_MARKERS}
    for result in results:
        counts = object_mapping(result.get("marker_counts"))
        for marker in BAD_MARKERS:
            value = counts.get(marker)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[marker] += value
    return totals


def baseline_elapsed_ms(report: Mapping[str, object]) -> int | None:
    """Extract the Docling page-window replay baseline elapsed time when present."""
    records = report.get("records")
    if not isinstance(records, list) or not records:
        return None
    first = object_mapping(records[0])
    child = object_mapping(first.get("child"))
    elapsed = child.get("elapsed_ms")
    if isinstance(elapsed, int) and not isinstance(elapsed, bool):
        return elapsed
    return None


def executable_exists(executable: str) -> bool:
    """Return whether an executable is available."""
    if "/" in executable:
        return Path(executable).exists()
    return shutil.which(executable) is not None


def timeout_text(value: object) -> str:
    """Normalize TimeoutExpired stdout/stderr values."""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return ""


def tail_text(value: str) -> str:
    """Return a bounded text tail for reports."""
    if len(value) <= TAIL_CHARS:
        return value
    return value[-TAIL_CHARS:]


def read_json_object(path: Path) -> dict[str, object]:
    """Read a JSON object from disk, returning empty mapping for non-objects."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return {str(key): value for key, value in loaded.items()}
    return {}
