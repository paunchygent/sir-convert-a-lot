"""Producer source-state issuance for exam authoring corrections.

Purpose:
    Resolve persisted producer-owned exam-authoring source state and issue the
    signed binding bundle that downstream correction consumers echo to the
    unified correction apply route.

Relationships:
    - Uses source-state DTOs from
      `application.exam_authoring_correction_source_state_models`.
    - Shares digest and signature helpers with correction-apply validation.
    - Exposed by `interfaces.http_routes_exam_authoring_corrections_v2` as the
      Sir Convert-owned source-state issuance surface for Service API v2.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.exam_authoring_correction_source_state_models import (
    ExamAuthoringCorrectionSourceBindingV1,
    ExamAuthoringCorrectionSourceStateIssueRequestV1,
    ExamAuthoringCorrectionSourceStateIssueResultV1,
    ExamAuthoringCorrectionSourceStateV1,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_integrity import (
    source_state_authority_signature,
    source_state_content_digest,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2

SOURCE_STATE_ARTIFACT_FILENAME = "exam-authoring-correction-source-state.json"


class ExamAuthoringCorrectionSourceStateIssueError(ValueError):
    """Raised when source-state authority issuance cannot produce a binding."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, object],
        *,
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details
        self.status_code = status_code


def issue_exam_authoring_correction_source_state(
    request_body: ExamAuthoringCorrectionSourceStateIssueRequestV1,
    *,
    job: StoredJobV2,
    source_state_signature_secret: str | None,
) -> ExamAuthoringCorrectionSourceStateIssueResultV1:
    """Return a canonical source state and signed producer-owned binding."""

    _validate_job_can_issue_source_state(job)
    if source_state_signature_secret is None or source_state_signature_secret.strip() == "":
        raise ExamAuthoringCorrectionSourceStateIssueError(
            "exam_authoring_source_state_authority_not_configured",
            "Correction source state authority signing is not configured.",
            {},
            status_code=500,
        )
    source_state = _canonical_source_state(_load_source_state_artifact(job))
    if (
        request_body.expected_source_state_sha256 is not None
        and request_body.expected_source_state_sha256 != source_state.source_state_sha256
    ):
        raise ExamAuthoringCorrectionSourceStateIssueError(
            "stale_exam_authoring_source_state",
            "Requested correction source-state digest does not match producer state.",
            {
                "submitted_source_state_sha256": request_body.expected_source_state_sha256,
                "expected_source_state_sha256": source_state.source_state_sha256,
            },
        )
    unsigned_binding = ExamAuthoringCorrectionSourceBindingV1(
        source_authoring_schema_version=source_state.source_authoring_schema_version,
        source_state_sha256=source_state.source_state_sha256,
        source_state_signature="hmac-sha256:unsigned",
        source_bundle_id=job.job_id,
        source_file_sha256=_source_file_sha256(job),
    )
    source_binding = unsigned_binding.model_copy(
        update={
            "source_state_signature": source_state_authority_signature(
                binding=unsigned_binding,
                secret=source_state_signature_secret.strip(),
            )
        }
    )
    return ExamAuthoringCorrectionSourceStateIssueResultV1(
        source_binding=source_binding,
        source_authoring_state=source_state,
    )


def correction_source_state_artifact_path_for_job(job: StoredJobV2) -> Path:
    """Return the server-owned source-state artifact path for a v2 producer job."""

    return job.artifact_path.parent / SOURCE_STATE_ARTIFACT_FILENAME


def write_exam_authoring_correction_source_state_artifact(
    *,
    path: Path,
    source_state: ExamAuthoringCorrectionSourceStateV1,
) -> None:
    """Persist canonical producer source state for later signed issuance."""

    canonical_source_state = _canonical_source_state(source_state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(canonical_source_state.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validate_job_can_issue_source_state(job: StoredJobV2) -> None:
    if job.status == JobStatus.SUCCEEDED:
        return
    raise ExamAuthoringCorrectionSourceStateIssueError(
        "exam_authoring_source_state_not_ready",
        "Correction source state can only be issued for a succeeded producer job.",
        {"job_id": job.job_id, "status": job.status.value},
        status_code=409,
    )


def _load_source_state_artifact(job: StoredJobV2) -> ExamAuthoringCorrectionSourceStateV1:
    path = correction_source_state_artifact_path_for_job(job)
    if not path.exists():
        raise ExamAuthoringCorrectionSourceStateIssueError(
            "exam_authoring_source_state_artifact_missing",
            "Producer job has no correction source-state artifact.",
            {"job_id": job.job_id},
            status_code=409,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExamAuthoringCorrectionSourceStateIssueError(
            "exam_authoring_source_state_artifact_invalid",
            "Correction source-state artifact could not be loaded.",
            {"job_id": job.job_id},
            status_code=500,
        ) from exc
    if not isinstance(payload, dict):
        raise ExamAuthoringCorrectionSourceStateIssueError(
            "exam_authoring_source_state_artifact_invalid",
            "Correction source-state artifact must be a JSON object.",
            {"job_id": job.job_id},
            status_code=500,
        )
    try:
        return ExamAuthoringCorrectionSourceStateV1.model_validate(payload)
    except ValidationError as exc:
        raise ExamAuthoringCorrectionSourceStateIssueError(
            "exam_authoring_source_state_artifact_invalid",
            "Correction source-state artifact does not match the source-state schema.",
            {"job_id": job.job_id},
            status_code=500,
        ) from exc


def _source_file_sha256(job: StoredJobV2) -> str:
    payload = job.upload_path.read_bytes()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _canonical_source_state(
    source_state: ExamAuthoringCorrectionSourceStateV1,
) -> ExamAuthoringCorrectionSourceStateV1:
    digest = source_state_content_digest(source_state)
    return source_state.model_copy(update={"source_state_sha256": digest})
