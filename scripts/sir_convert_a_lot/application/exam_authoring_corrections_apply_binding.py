"""Request binding validation for exam authoring correction application.

Purpose:
    Validate source-state binding, canonical content digests, and signed
    producer-state authority before correction batches can affect readiness.

Relationships:
    - Used by `application.exam_authoring_corrections_apply_contracts`.
    - Uses integrity helpers that are shared with producer/test surfaces.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_integrity import (
    request_source_state_content_digest,
    source_state_authority_signature_matches,
)
from scripts.sir_convert_a_lot.application.exam_authoring_corrections_apply_models import (
    ExamAuthoringCorrectionsApplyRequestV1,
)


class ExamAuthoringCorrectionsApplyBindingError(ValueError):
    """Raised when a correction request is not bound to producer authority."""

    def __init__(self, code: str, message: str, details: dict[str, object]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def validate_correction_request_binding(
    *,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    source_state_signature_secret: str | None,
) -> None:
    """Validate request binding against canonical and server-verifiable state."""

    binding = request_body.source_binding
    state = request_body.source_authoring_state
    if binding.source_authoring_schema_version != state.source_authoring_schema_version:
        raise ExamAuthoringCorrectionsApplyBindingError(
            "stale_exam_authoring_schema_version",
            "Correction source binding schema version does not match the source state.",
            {
                "submitted_schema_version": binding.source_authoring_schema_version,
                "expected_schema_version": state.source_authoring_schema_version,
            },
        )
    if binding.source_state_sha256 != state.source_state_sha256:
        raise ExamAuthoringCorrectionsApplyBindingError(
            "stale_exam_authoring_source_state",
            "Correction source binding digest does not match the source state.",
            {
                "submitted_source_state_sha256": binding.source_state_sha256,
                "expected_source_state_sha256": state.source_state_sha256,
            },
        )
    canonical_digest = request_source_state_content_digest(request_body)
    if state.source_state_sha256 != canonical_digest:
        raise ExamAuthoringCorrectionsApplyBindingError(
            "stale_exam_authoring_source_state_digest",
            "Correction source state digest does not match canonical producer state content.",
            {
                "submitted_source_state_sha256": state.source_state_sha256,
                "expected_source_state_sha256": canonical_digest,
            },
        )
    _validate_source_state_authority(
        request_body=request_body,
        source_state_signature_secret=source_state_signature_secret,
    )


def _validate_source_state_authority(
    *,
    request_body: ExamAuthoringCorrectionsApplyRequestV1,
    source_state_signature_secret: str | None,
) -> None:
    if source_state_signature_secret is None or source_state_signature_secret.strip() == "":
        raise ExamAuthoringCorrectionsApplyBindingError(
            "exam_authoring_source_state_authority_not_configured",
            "Correction source state authority signing is not configured.",
            {},
        )
    secret = source_state_signature_secret.strip()
    if source_state_authority_signature_matches(
        binding=request_body.source_binding,
        secret=secret,
    ):
        return
    binding = request_body.source_binding
    raise ExamAuthoringCorrectionsApplyBindingError(
        "stale_exam_authoring_source_state_authority",
        "Correction source binding signature does not match producer authority.",
        {
            "source_state_sha256": binding.source_state_sha256,
            "source_bundle_id": binding.source_bundle_id,
            "source_file_sha256": binding.source_file_sha256,
        },
    )
