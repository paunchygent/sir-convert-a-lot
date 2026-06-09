"""Write formula candidate evaluation formula candidate evaluation reports.

Purpose:
    Produce compact Markdown, JSON, and HTML review artifacts from the Task
    346 candidate-evaluation payload.

Relationships:
    - Consumes candidate records from formula candidate evaluation candidate helpers.
    - Consumes source inputs from formula candidate evaluation input helpers.
    - Writes local evidence only; it is not a production artifact surface.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Mapping, Sequence

from scripts.sir_convert_a_lot.devops.formula_candidate_eval_inputs import (
    SourceInput,
    object_mapping,
)


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    """Write deterministic JSON."""
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_markdown_report(*, path: Path, payload: Mapping[str, object]) -> None:
    """Write a concise human report for the evaluation bundle."""
    lines = [
        "# formula candidate evaluation formula candidate evaluation",
        "",
        f"- Source SHA256: `{payload.get('source_sha256')}`",
        f"- Pages: `{payload.get('pages')}`",
        f"- Formula regions harvested: `{payload.get('formula_region_count')}`",
        f"- Formula regions evaluated: `{payload.get('evaluated_formula_region_count')}`",
        "",
        "| Candidate | Status | Inputs | Elapsed ms | Markers | Notes |",
        "|---|---:|---:|---:|---|---|",
    ]
    for candidate in candidate_dicts(payload):
        marker_counts = object_mapping(candidate.get("marker_counts"))
        marker_summary = ", ".join(f"{key}={value}" for key, value in marker_counts.items())
        note = str(candidate.get("block_reason", candidate.get("notes", "")))
        lines.append(
            "| "
            + str(candidate.get("candidate_id"))
            + " | "
            + str(candidate.get("status"))
            + " | "
            + str(candidate.get("input_count", ""))
            + " | "
            + str(candidate.get("elapsed_ms", ""))
            + " | "
            + marker_summary
            + " | "
            + note
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_visual_review_index(
    *,
    path: Path,
    source_inputs: Sequence[SourceInput],
    candidate_results: Sequence[Mapping[str, object]],
) -> None:
    """Write an HTML side-by-side source image and candidate-output index."""
    rows = [
        review_row(source_input=source_input, candidate_results=candidate_results, base=path.parent)
        for source_input in source_inputs
    ]
    html_text = (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<title>formula candidate evaluation visual review</title>"
        "<style>body{font-family:sans-serif;margin:24px}article{border-top:1px solid #999;"
        "padding:18px 0}img{max-width:920px;border:1px solid #ccc}section{display:inline-block;"
        "vertical-align:top;width:31%;margin-right:1%;}pre{white-space:pre-wrap;background:#f7f7f7;"
        "padding:10px;max-height:420px;overflow:auto}</style></head>"
        "<body><h1>formula candidate evaluation visual review</h1>"
        + "".join(rows)
        + "</body></html>\n"
    )
    path.write_text(html_text, encoding="utf-8")


def review_row(
    *,
    source_input: SourceInput,
    candidate_results: Sequence[Mapping[str, object]],
    base: Path,
) -> str:
    """Render one source input and its candidate output snippets."""
    candidate_cells: list[str] = []
    for candidate in candidate_results:
        candidate_id = str(candidate.get("candidate_id", "candidate"))
        output_text = output_text_for_candidate(source_input.input_id, candidate)
        candidate_cells.append(
            "<section><h3>"
            + html.escape(candidate_id)
            + "</h3><pre>"
            + html.escape(output_text[:4000])
            + "</pre></section>"
        )
    return (
        "<article><h2>"
        + html.escape(source_input.input_id)
        + '</h2><img src="'
        + html.escape(display_path(source_input.image_path, base))
        + '" alt="'
        + html.escape(source_input.input_id)
        + '">'
        + "".join(candidate_cells)
        + "</article>"
    )


def output_text_for_candidate(input_id: str, candidate: Mapping[str, object]) -> str:
    """Return review text for one candidate/input pair."""
    input_results = candidate.get("input_results")
    if isinstance(input_results, list):
        for result_obj in input_results:
            result = object_mapping(result_obj)
            if result.get("input_id") == input_id:
                text = text_from_path_value(result.get("output_text_path"))
                if text:
                    return text
    text = text_from_path_value(candidate.get("output_text_path"))
    if text:
        return text
    if candidate.get("status") == "blocked":
        return "BLOCKED: " + str(candidate.get("block_reason", "unknown"))
    return ""


def text_from_path_value(value: object) -> str:
    """Read text when a JSON path value points to an existing file."""
    if not isinstance(value, str):
        return ""
    output_path = Path(value)
    if output_path.exists():
        return output_path.read_text(encoding="utf-8", errors="replace")
    return ""


def candidate_dicts(payload: Mapping[str, object]) -> list[dict[str, object]]:
    """Return normalized candidate result mappings."""
    candidates = payload.get("candidate_results")
    if not isinstance(candidates, list):
        return []
    return [object_mapping(candidate) for candidate in candidates]


def display_path(path: Path, base: Path) -> str:
    """Return a path relative to the HTML review when possible."""
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()
