"""Incremental Docling formula diagnostic event writer.

Purpose:
    Persist sanitized formula/code VLM diagnostic breadcrumbs before blocking
    model calls so bounded replay keeps evidence when a child is killed.

Relationships:
    - Used by `infrastructure.docling_formula_diagnostics`.
    - Consumed by Docling page-window replay page-window replay reports.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_FORMULA_DIAGNOSTICS_JSONL"
DOCLING_FORMULA_SINGLE_ITEM_REPLAY_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_FORMULA_SINGLE_ITEM_REPLAY"


def emit_docling_formula_diagnostic_event(record: dict[str, object]) -> None:
    """Append one sanitized diagnostic event when a JSONL path is configured."""
    path_value = os.environ.get(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR)
    if not path_value:
        return
    payload = {
        "monotonic_ms": int(time.monotonic() * 1000),
        **record,
    }
    try:
        path = Path(path_value)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
    except Exception:
        return


def docling_formula_diagnostic_events_enabled() -> bool:
    """Return whether the incremental diagnostics sidecar is configured."""
    return bool(os.environ.get(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR))


def docling_formula_single_item_replay_enabled() -> bool:
    """Return whether diagnostic replay should isolate formula items."""
    return os.environ.get(DOCLING_FORMULA_SINGLE_ITEM_REPLAY_ENV_VAR) == "1"
