"""Transcript formatter blocked-state governance evidence.

Purpose:
    Prove transcript formatter remains a governed blocked formatter slice while the
    canonical transcript JSON route and persistence contract are not accepted.

Relationships:
    - Reads transcript formatter and the retained audio-transcription route execution review as
      docs-as-code
      authority for the current blocked implementation decision.
    - Exercises the v2 route/spec and audio public-options boundaries to ensure
      formatter artifact requests are not exposed as runtime behavior.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioDiarizationMode,
    AudioDiarizationOptions,
    AudioTranscriptionErrorCode,
    AudioTranscriptionPublicOptions,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from tests.sir_convert_a_lot.backlog_document_test_support import (
    backlog_document_path,
    repo_relative_path,
)

TRANSCRIPT_FORMATTER_STORY_PATH = backlog_document_path(
    category="stories",
    title_slug="transcript-formatter-strategies-over-canonical-json",
)
TRANSCRIPT_ROUTE_REVIEW_PATH = backlog_document_path(
    category="reviews",
    title_slug="audio-transcript-bundle-route-execution-and-json-artifact-persistence",
)


def test_transcript_formatters_stay_blocked_without_canonical_json_runtime() -> None:
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {
                "kind": "upload",
                "filename": "teacher-meeting.m4a",
                "format": "audio",
            },
            "conversion": {"output_format": "transcript_bundle"},
            "audio_transcription_options": {
                "language": "auto",
                "diarization": {
                    "mode": "auto",
                    "num_speakers": None,
                    "min_speakers": None,
                    "max_speakers": None,
                },
                "max_duration_seconds": 7200,
                "output_artifacts": ["json"],
            },
            "execution": {
                "acceleration_policy": "gpu_required",
                "priority": "normal",
                "document_timeout_seconds": 7200,
            },
            "retention": {"pin": False},
        }
    )

    assert spec.source.format.value == "audio"
    assert spec.conversion.output_format.value == "transcript_bundle"


@pytest.mark.parametrize(
    "formatter_artifact",
    ["transcript_txt", "transcript_md", "transcript_vtt", "transcript_srt"],
)
def test_formatter_artifact_requests_are_rejected_until_transcript_json_persists(
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


def test_transcript_formatter_records_blocked_decision_without_runtime_completion() -> None:
    story_source = TRANSCRIPT_FORMATTER_STORY_PATH.read_text(encoding="utf-8")
    story_frontmatter = _frontmatter(story_source)
    story_text = _single_line(story_source)
    route_review_text = _single_line(TRANSCRIPT_ROUTE_REVIEW_PATH.read_text(encoding="utf-8"))

    assert "status: proposed" in story_text
    assert f"  - {repo_relative_path(TRANSCRIPT_ROUTE_REVIEW_PATH)}" in story_frontmatter
    assert "## Blocked Implementation Decision" in story_text
    assert "remains `proposed`" in story_text
    assert "canonical `transcript_json` persistence" in story_text
    assert "Do not implement formatter strategies" in story_text
    assert "- [x] Blocked implementation decision recorded" in story_text
    assert "- [x] Formatter runtime remains unimplemented" in story_text
    assert "- [ ] Runtime formatter implementation complete" in story_text
    assert "transcript artifact persistence" in route_review_text


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
