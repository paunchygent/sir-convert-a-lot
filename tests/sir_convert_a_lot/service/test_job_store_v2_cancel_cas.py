"""Regression tests for v2 job store cancellation CAS semantics.

Purpose:
    Prove that a late cancel attempt cannot overwrite a terminal job outcome,
    preventing the "cancel overwrote success" hazard in race conditions.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.job_store_v2.JobStoreV2`.
    - Validates invariants required by `scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import JobStateConflictV2
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2


def _md_to_pdf_spec(*, filename: str) -> JobSpecV2:
    return JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": filename, "format": "md"},
            "conversion": {
                "output_format": "pdf",
                "css_filenames": [],
                "reference_docx_filename": None,
            },
            "retention": {"pin": False},
        }
    )


def test_mark_canceled_rejects_terminal_status_and_preserves_success(tmp_path: Path) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
    )

    job_id = "jobv2_test_cancel_cas"
    store.create_job(
        job_id=job_id,
        spec=_md_to_pdf_spec(filename="note.md"),
        upload_bytes=b"# Title\n\nHello.\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    assert store.claim_queued_job(job_id) is True

    store.mark_succeeded(
        job_id,
        artifact_bytes=b"%PDF-1.4\n% fake\n%%EOF\n",
        pipeline_used="md_to_pdf_v2",
        backend_used="stub",
        acceleration_used=None,
        options_fingerprint="sha256:test",
        warnings=[],
        phase_timings_ms={},
    )
    assert store.get_job(job_id).status == JobStatus.SUCCEEDED

    with pytest.raises(JobStateConflictV2):
        store.mark_canceled(job_id)

    assert store.get_job(job_id).status == JobStatus.SUCCEEDED
