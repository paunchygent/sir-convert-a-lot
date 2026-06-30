"""Source-job policy for exam authoring correction replay.

Purpose:
    Enforce that source-bound correction apply requests cannot project
    exportable replay readiness unless the signed producer source job still
    resolves.

Relationships:
    - Called by the Service API v2 correction apply route after request schema,
      source-state digest, and source-state signature validation.
    - Complements correction replay artifact writing, which still owns concrete
      artifact production for a resolved and authorized source job.
"""

from __future__ import annotations

from typing import TypeVar

_SourceJobT = TypeVar("_SourceJobT")


class ExamAuthoringCorrectionSourceJobResolutionError(ValueError):
    """Raised when a validated source binding cannot prove its source job."""

    status_code = 409
    code = "exam_authoring_correction_source_job_unavailable"

    def __init__(self, source_bundle_id: str) -> None:
        super().__init__("Correction replay source job is unavailable.")
        self.details: dict[str, object] = {"source_bundle_id": source_bundle_id}


def require_resolved_correction_source_job(
    *,
    source_bundle_id: str,
    source_job: _SourceJobT | None,
) -> _SourceJobT:
    """Return a resolved source job or fail closed for source-bound replay."""

    if source_job is None:
        raise ExamAuthoringCorrectionSourceJobResolutionError(source_bundle_id)
    return source_job
