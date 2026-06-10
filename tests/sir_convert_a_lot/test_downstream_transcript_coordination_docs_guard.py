"""downstream transcript coordination downstream transcript coordination docs guard.

Purpose:
    Prove the completed downstream transcript coordination record remains truthful about Gateway and
    downstream transcript delivery coordination after the current STT route and
    formatter slices are sequenced behind Sir Convert's admission-only audio
    route state.

Relationships:
    - Reads downstream transcript coordination as the governed Sir Convert planning authority for
    the
      HuleEdu and Skriptoteket downstream transcript-delivery handoff.
    - Guards links to retained audio-transcription profile selection, audio-transcription route
      execution, and transcript formatter review records
      without requiring sibling repositories to exist at absolute paths.
"""

from __future__ import annotations

from tests.sir_convert_a_lot.backlog_document_test_support import (
    backlog_document_path,
    repo_relative_path,
)

DOWNSTREAM_TRANSCRIPT_COORDINATION_STORY_PATH = backlog_document_path(
    category="stories",
    title_slug="gateway-and-downstream-transcript-delivery-coordination",
)
AUDIO_PROFILE_REVIEW_PATH = backlog_document_path(
    category="reviews",
    title_slug="hemma-stt-and-diarization-backend-benchmark-profile-selection",
)
AUDIO_ROUTE_REVIEW_PATH = backlog_document_path(
    category="reviews",
    title_slug="audio-transcript-bundle-route-execution-and-json-artifact-persistence",
)
TRANSCRIPT_FORMATTER_STORY_PATH = backlog_document_path(
    category="stories",
    title_slug="transcript-formatter-strategies-over-canonical-json",
)
TRANSCRIPT_FORMATTER_REVIEW_PATH = backlog_document_path(
    category="reviews",
    title_slug="transcript-formatter-strategies-over-canonical-json",
)


def test_downstream_transcript_records_gateway_planning_constraints() -> None:
    story_source = DOWNSTREAM_TRANSCRIPT_COORDINATION_STORY_PATH.read_text(encoding="utf-8")
    story_text = _single_line(story_source)

    assert "coordination is completed as planning/alignment only" in story_text
    assert "not runtime Gateway proxy, sidecar execution, formatter, or UI work" in story_text
    assert "HuleEdu ST-01-08" in story_text
    assert "Skriptoteket ST-21-05" in story_text
    assert "Skriptoteket ST-21-06" in story_text
    assert "Skriptoteket ST-21-07" in story_text
    assert "Gateway-only `/sir-convert/v2/convert` product access" in story_text
    assert "`InternalIdentityContextV1`" in story_text
    assert "admission-registered planning authority" in story_text
    assert "not a transcript execution or artifact-delivery surface" in story_text
    assert "short Sir Convert operational retention" in story_text
    assert "durable Skriptoteket transcript retention" in story_text
    assert "JSON-first durable save" in story_text
    assert "formatter artifacts as follow-on" in story_text
    assert "no public, no-login, direct sidecar, or sidecar-public ingress" in (story_text)


def test_downstream_transcript_links_current_route_delivery_authority() -> None:
    story_source = DOWNSTREAM_TRANSCRIPT_COORDINATION_STORY_PATH.read_text(encoding="utf-8")
    story_frontmatter = _frontmatter(story_source)
    story_text = _single_line(story_source)

    expected_related_paths = [
        repo_relative_path(AUDIO_PROFILE_REVIEW_PATH),
        repo_relative_path(AUDIO_ROUTE_REVIEW_PATH),
        repo_relative_path(TRANSCRIPT_FORMATTER_STORY_PATH),
        repo_relative_path(TRANSCRIPT_FORMATTER_REVIEW_PATH),
    ]

    for path in expected_related_paths:
        assert f"  - {path}" in story_frontmatter

    assert "governed production-profile rejection has been superseded" in story_text
    assert "`audio -> transcript_bundle` route-admission slice" in story_text
    assert "before downstream stories may treat transcript delivery as live" in story_text


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
