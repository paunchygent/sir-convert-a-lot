"""Sir Convert-a-Lot integration adapter exports.

Purpose:
    Provide thin, contract-aligned integration helpers for consumer backends
    (HuleEdu and Skriptoteket) without introducing conversion business logic.

Relationships:
    - Delegates HTTP operations to `interfaces.http_client`.
    - Enforces adapter requirements documented in converter integration docs.
"""

from scripts.sir_convert_a_lot.integrations.adapter_profiles import (
    AdapterPreparedSubmission,
    AdapterRequestContext,
    ConsumerProfile,
    build_correlation_id,
    build_idempotency_key,
    build_job_spec_for_profile,
    prepare_submission,
    submit_pdf_for_profile,
)

__all__ = [
    "AdapterPreparedSubmission",
    "AdapterRequestContext",
    "ConsumerProfile",
    "build_correlation_id",
    "build_idempotency_key",
    "build_job_spec_for_profile",
    "prepare_submission",
    "submit_pdf_for_profile",
]
