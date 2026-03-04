"""PDF metadata helpers used by v2 job orchestration.

Purpose:
    Provide small, best-effort helpers for extracting inexpensive PDF metadata
    (currently: total page count) used to populate v2 progress fields without
    coupling the runtime engine to backend-specific conversion logic.

Relationships:
    - Used by `infrastructure.runtime_engine_v2` during RUNNING stage setup to
      populate `job.progress.total_pages` for PDF routes.
"""

from __future__ import annotations

from pathlib import Path


def best_effort_pdf_total_pages(path: Path) -> int | None:
    """Return PDF page count or None when the file is missing/unreadable."""
    try:
        import pymupdf
    except Exception:  # pragma: no cover - environment-level import failure.
        return None

    try:
        document = pymupdf.open(path.as_posix())
    except Exception:
        return None
    try:
        page_count = getattr(document, "page_count", None)
        if not isinstance(page_count, int) or isinstance(page_count, bool):
            return None
        if page_count <= 0:
            return None
        return page_count
    finally:
        try:
            document.close()
        except Exception:
            pass
