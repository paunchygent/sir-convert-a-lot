"""Transcript formatter replay Service API v2 behavior.

Purpose:
    Prove saved canonical transcript JSON can be replayed through the normal
    v2 job lifecycle with typed speaker display-name overlays and product-
    neutral formatter artifacts.

Relationships:
    - Exercises the public `transcript_json -> transcript_bundle` route.
    - Exercises the pure replay formatter projection without invoking STT,
      diarization, alignment, sidecar, codec, or source-media modules.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    build_create_job_route_registry_v2,
    infer_source_format_from_filename_v2,
)
from tests.sir_convert_a_lot.speech.transcript_formatter_replay_test_support import (
    _app,
    _invalid_payload_bytes,
    _post_replay_job,
    _replay_job_spec,
)


def test_replay_options_are_strict_and_route_is_registered() -> None:
    registry = build_create_job_route_registry_v2()
    route_keys = {
        (key.source_format.value, key.output_format.value)
        for key in registry.registered_route_keys()
    }
    spec = JobSpecV2.model_validate(_replay_job_spec())

    assert ("transcript_json", "transcript_bundle") in route_keys
    assert infer_source_format_from_filename_v2("saved-transcript.json") is not None
    assert spec.source.format.value == "transcript_json"
    assert spec.conversion.output_format.value == "transcript_bundle"
    assert spec.transcript_formatter_options is not None
    assert spec.transcript_formatter_options.requested_artifacts == ("txt", "md", "vtt", "srt")


@pytest.mark.parametrize(
    ("patch", "expected_text"),
    [
        ({"schema_version": "other"}, "transcript_formatter_replay_v1"),
        ({"requested_artifacts": ["json"]}, "unsupported transcript formatter artifact"),
        ({"requested_artifacts": []}, "at least one requested artifact"),
        ({"speaker_label_overrides": []}, "at least one speaker label override"),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"},
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Karin"},
                ]
            },
            "duplicate canonical speaker label",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"},
                    {"canonical_speaker_label": "SPEAKER_01", "display_name": "Anna"},
                ]
            },
            "duplicate display name",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "   "}
                ]
            },
            "display name must not be empty",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna\nA"}
                ]
            },
            "control characters",
        ),
        (
            {
                "speaker_label_overrides": [
                    {"canonical_speaker_label": "SPEAKER_00", "display_name": "A" * 121}
                ]
            },
            "at most 120 characters",
        ),
        ({"unexpected": True}, "Extra inputs are not permitted"),
    ],
)
def test_replay_options_reject_invalid_shapes(
    patch: Mapping[str, object],
    expected_text: str,
) -> None:
    payload = _replay_job_spec(options_patch=patch)

    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(payload)

    assert expected_text in str(error_info.value)


@pytest.mark.parametrize(
    ("payload_kind", "spec_patch", "expected_code"),
    [
        ("canonical", {"retention": {"pin": True}}, "validation_error"),
        (
            "canonical",
            {
                "transcript_formatter_options": {
                    "schema_version": "transcript_formatter_replay_v1",
                    "requested_artifacts": ["txt"],
                    "speaker_label_overrides": [
                        {"canonical_speaker_label": "UNKNOWN", "display_name": "Anna"}
                    ],
                }
            },
            "transcript_formatter_replay_invalid",
        ),
        ("malformed", {}, "transcript_formatter_replay_invalid"),
        ("partial", {}, "transcript_formatter_replay_invalid"),
    ],
)
def test_replay_invalid_requests_fail_before_artifact_generation(
    tmp_path: Path,
    payload_kind: str,
    spec_patch: Mapping[str, object],
    expected_code: str,
) -> None:
    app = _app(tmp_path)
    client = TestClient(app)

    response = _post_replay_job(
        client=client,
        idempotency_key=f"idem-transcript-replay-invalid-{expected_code}-{payload_kind}",
        wait_seconds=20,
        file_bytes=_invalid_payload_bytes(payload_kind),
        spec=_replay_job_spec(top_level_patch=spec_patch),
    )

    if expected_code == "validation_error":
        assert response.status_code == 422
        assert response.json()["error"]["code"] == expected_code
        return

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.FAILED.value
    job_id = job["job_id"]
    stored_job = app.state.runtime_v2.get_job(job_id)
    assert stored_job is not None
    assert stored_job.failure_code == expected_code
    assert not (stored_job.artifact_path.parent / "transcript_txt.txt").exists()
    assert not (stored_job.artifact_path.parent / "transcript_md.md").exists()
