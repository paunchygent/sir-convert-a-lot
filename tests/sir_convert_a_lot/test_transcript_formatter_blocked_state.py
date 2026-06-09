"""Transcript formatter blocked-state governance evidence.

Purpose:
    Prove Story 54 remains a governed blocked formatter slice while the
    canonical transcript JSON route and persistence contract are not accepted.

Relationships:
    - Reads Story 54 and the retained Story 53 review as docs-as-code
      authority for the current blocked implementation decision.
    - Exercises the v2 route/spec and audio public-options boundaries to ensure
      formatter artifact requests are not exposed as runtime behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioDiarizationMode,
    AudioDiarizationOptions,
    AudioTranscriptionErrorCode,
    AudioTranscriptionPublicOptions,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    build_create_job_route_registry_v2,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STORY_54_PATH = (
    REPO_ROOT
    / "docs/backlog/stories/"
    / "story-54-transcript-formatter-strategies-over-canonical-json.md"
)
STORY_53_REVIEW_PATH = (
    REPO_ROOT
    / "docs/backlog/reviews/"
    / (
        "review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-"
        "execution-and-json-artifact-persistence.md"
    )
)
STORY_53_REVIEW_RELATED_PATH = (
    "docs/backlog/reviews/"
    "review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-"
    "execution-and-json-artifact-persistence.md"
)


def test_transcript_formatters_stay_blocked_without_canonical_json_runtime() -> None:
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


@pytest.mark.parametrize(
    "formatter_artifact",
    ["transcript_txt", "transcript_md", "transcript_vtt", "transcript_srt"],
)
def test_formatter_artifact_requests_are_rejected_while_story_53_is_blocked(
    formatter_artifact: str,
) -> None:
    options = AudioTranscriptionPublicOptions(
        language="sv",
        diarization=AudioDiarizationOptions(mode=AudioDiarizationMode.AUTO),
        max_duration_seconds=300,
        output_artifacts=("json", formatter_artifact),
        raw_option_keys=frozenset({"language", "diarization", "output_artifacts"}),
    )

    failure = options.validation_failure()

    assert failure == (
        AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED,
        {"unsupported_option": "output_artifacts"},
    )


def test_story_54_records_blocked_decision_without_runtime_completion() -> None:
    story_source = STORY_54_PATH.read_text(encoding="utf-8")
    story_frontmatter = _frontmatter(story_source)
    story_text = _single_line(story_source)
    story_53_review_text = _single_line(STORY_53_REVIEW_PATH.read_text(encoding="utf-8"))

    assert "status: proposed" in story_text
    assert f"  - {STORY_53_REVIEW_RELATED_PATH}" in story_frontmatter
    assert "## Blocked Implementation Decision" in story_text
    assert "Story 54 remains `proposed`" in story_text
    assert "canonical `transcript_json` persistence" in story_text
    assert "Do not implement formatter strategies" in story_text
    assert "- [x] Blocked implementation decision recorded" in story_text
    assert "- [x] Formatter runtime remains unimplemented" in story_text
    assert "- [ ] Runtime formatter implementation complete" in story_text
    assert "This review does not authorize route registration" in story_53_review_text
    assert "transcript artifact persistence" in story_53_review_text


def _single_line(value: str) -> str:
    return " ".join(value.split())


def _frontmatter(value: str) -> str:
    delimiter = "---"
    if not value.startswith(delimiter):
        raise AssertionError("Expected story document to start with YAML frontmatter.")
    frontmatter_end = value.find(f"\n{delimiter}\n", len(delimiter))
    if frontmatter_end == -1:
        raise AssertionError("Expected story document frontmatter to be closed.")
    return value[:frontmatter_end]
