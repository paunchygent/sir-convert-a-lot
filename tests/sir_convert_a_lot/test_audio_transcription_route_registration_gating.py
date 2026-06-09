"""Audio transcription route-registration gating evidence.

Purpose:
    Prove the planned audio transcript route remains unavailable through the
    public Service API v2 route boundary while production STT and diarization
    profiles are rejected.

Relationships:
    - Reads the governed audio route and profile review records as docs-as-code
      authority.
    - Exercises `interfaces.http_create_job_routes_v2` and `domain.specs_v2`
      to ensure no `audio -> transcript_bundle` create-job route is exposed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    build_create_job_route_registry_v2,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIO_ROUTE_STORY_PATH = (
    REPO_ROOT
    / "docs/backlog/stories/"
    / "story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md"
)
PROFILE_REJECTION_REVIEW_PATH = (
    REPO_ROOT
    / "docs/backlog/reviews/"
    / (
        "review-27-ruthless-review-of-story-52-hemma-stt-and-diarization-"
        "backend-benchmark-profile-selection.md"
    )
)


def test_audio_transcript_route_remains_unregistered_after_profile_rejection() -> None:
    registry = build_create_job_route_registry_v2()
    route_keys = {
        (key.source_format.value, key.output_format.value)
        for key in registry.registered_route_keys()
    }

    assert ("audio", "transcript_bundle") not in route_keys

    with pytest.raises(ValidationError):
        JobSpecV2.model_validate(
            {
                "api_version": "v2",
                "source": {
                    "kind": "upload",
                    "filename": "teacher-meeting.m4a",
                    "format": "audio",
                },
                "conversion": {"output_format": "transcript_bundle"},
                "retention": {"pin": False},
            }
        )


def test_audio_transcript_route_block_is_recorded_without_runtime_completion() -> None:
    story_text = _single_line(AUDIO_ROUTE_STORY_PATH.read_text(encoding="utf-8"))
    review_text = _single_line(PROFILE_REJECTION_REVIEW_PATH.read_text(encoding="utf-8"))

    assert "status: proposed" in story_text
    assert "## Blocked Implementation Decision" in story_text
    assert "Story 52 production profile rejection" in story_text
    assert "Do not register the route" in story_text
    assert "- [x] Blocked implementation decision recorded" in story_text
    assert "- [x] Runtime route remains unregistered" in story_text
    assert "- [ ] Runtime route implementation complete" in story_text
    assert "does not authorize Story 53 route registration" in review_text


def _single_line(value: str) -> str:
    return " ".join(value.split())
