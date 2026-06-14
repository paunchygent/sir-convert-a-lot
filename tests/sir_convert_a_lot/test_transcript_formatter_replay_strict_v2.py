"""Strict replay contract tests for transcript formatter Service API v2.

Purpose:
    Prove replay rejects non-contract runtime options and undocumented aliases
    before downstream clients build against loose replay shapes.

Relationships:
    - Complements `test_transcript_formatter_replay_v2`.
    - Exercises the `transcript_json -> transcript_bundle` contract corrections
      requested by retained Review 45.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from tests.sir_convert_a_lot.test_transcript_formatter_replay_v2 import (
    _app,
    _post_replay_job,
    _replay_job_spec,
)


def _valid_pdf_options() -> dict[str, object]:
    return {
        "backend_strategy": "auto",
        "ocr_mode": "auto",
        "table_mode": "accurate",
        "normalize": "strict",
    }


@pytest.mark.parametrize(
    ("options_patch", "expected_text"),
    [
        ({"requested_artifacts": ["TXT"]}, "unsupported transcript formatter artifact"),
        ({"requested_artifacts": [" txt "]}, "unsupported transcript formatter artifact"),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00\t", "display_name": "Anna"}
                ]
            },
            "control characters",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "\tAnna"}
                ]
            },
            "control characters",
        ),
    ],
)
def test_replay_options_reject_undocumented_aliases(
    options_patch: Mapping[str, object],
    expected_text: str,
) -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_replay_job_spec(options_patch=options_patch))

    assert expected_text in str(error_info.value)


@pytest.mark.parametrize(
    ("top_level_patch", "expected_text"),
    [
        ({"pdf_options": _valid_pdf_options()}, "pdf_options is not supported"),
        ({"execution": {"acceleration_policy": "gpu_required"}}, "execution is not supported"),
    ],
)
def test_replay_route_rejects_pdf_and_execution_options(
    top_level_patch: Mapping[str, object],
    expected_text: str,
) -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_replay_job_spec(top_level_patch=top_level_patch))

    assert expected_text in str(error_info.value)


def test_replay_idempotency_does_not_ignore_rejected_runtime_options(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path, run_jobs_on_submit=False))
    idempotency_key = "idem-transcript-replay-runtime-options-not-ignored"
    accepted_response = _post_replay_job(
        client=client,
        idempotency_key=idempotency_key,
        wait_seconds=0,
    )
    rejected_spec = _replay_job_spec(
        top_level_patch={"execution": {"acceleration_policy": "gpu_required"}}
    )

    rejected_response = _post_replay_job(
        client=client,
        idempotency_key=idempotency_key,
        wait_seconds=0,
        spec=rejected_spec,
    )

    assert accepted_response.status_code == 200
    assert accepted_response.json()["job"]["status"] == JobStatus.SUCCEEDED.value
    assert rejected_response.status_code == 422
    assert rejected_response.headers.get("X-Idempotent-Replay") is None
    assert rejected_response.json()["error"]["code"] == "validation_error"


def test_replay_speaker_label_whitespace_is_not_normalized_before_inventory_check(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path)
    client = TestClient(app)
    response = _post_replay_job(
        client=client,
        idempotency_key="idem-transcript-replay-speaker-label-whitespace",
        wait_seconds=20,
        spec=_replay_job_spec(
            options_patch={
                "speaker_label_overrides": [
                    {"canonical_speaker_label": " SPEAKER_00 ", "display_name": "Anna"},
                ],
            }
        ),
    )

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.FAILED.value
    stored_job = app.state.runtime_v2.get_job(job["job_id"])
    assert stored_job is not None
    assert stored_job.failure_code == "transcript_formatter_replay_invalid"
    assert stored_job.failure_details == {"reason": "unknown_speaker_label"}
