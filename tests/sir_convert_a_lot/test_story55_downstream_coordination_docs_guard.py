"""Story 55 downstream transcript coordination docs guard.

Purpose:
    Prove the completed Story 55 record remains truthful about Gateway and
    downstream transcript delivery coordination after the current STT route and
    formatter slices were accepted only as blocked planning outcomes.

Relationships:
    - Reads Story 55 as the governed Sir Convert planning authority for the
      HuleEdu and Skriptoteket downstream transcript-delivery handoff.
    - Guards links to retained Story 52, Story 53, and Story 54 review records
      without requiring sibling repositories to exist at absolute paths.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STORY_55_PATH = (
    REPO_ROOT
    / "docs/backlog/stories/"
    / "story-55-gateway-and-downstream-transcript-delivery-coordination.md"
)


def test_story_55_records_gateway_downstream_planning_constraints() -> None:
    story_source = STORY_55_PATH.read_text(encoding="utf-8")
    story_text = _single_line(story_source)

    assert "coordination is completed as planning/alignment only" in story_text
    assert "not runtime Gateway proxy, route registration, formatter, or UI work" in (
        story_text
    )
    assert "HuleEdu ST-01-08" in story_text
    assert "Skriptoteket ST-21-05" in story_text
    assert "Skriptoteket ST-21-06" in story_text
    assert "Skriptoteket ST-21-07" in story_text
    assert "Gateway-only `/sir-convert/v2/convert` product access" in story_text
    assert "`InternalIdentityContextV1`" in story_text
    assert "accepted planning authority but not an implemented runtime surface" in (
        story_text
    )
    assert "short Sir Convert operational retention" in story_text
    assert "durable Skriptoteket transcript retention" in story_text
    assert "JSON-first durable save" in story_text
    assert "formatter artifacts as follow-on" in story_text
    assert "no public, no-login, direct sidecar, or sidecar-public ingress" in (
        story_text
    )


def test_story_55_links_current_blocked_review_authority() -> None:
    story_source = STORY_55_PATH.read_text(encoding="utf-8")
    story_frontmatter = _frontmatter(story_source)
    story_text = _single_line(story_source)

    expected_related_paths = [
        "docs/backlog/reviews/review-27-ruthless-review-of-story-52-hemma-stt-and-diarization-backend-benchmark-profile-selection.md",
        "docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md",
        "docs/backlog/stories/story-54-transcript-formatter-strategies-over-canonical-json.md",
        "docs/backlog/reviews/review-29-ruthless-review-of-story-54-transcript-formatter-strategies-over-canonical-json.md",
    ]

    for path in expected_related_paths:
        assert f"  - {path}" in story_frontmatter

    assert "Story 52 was accepted in Review 27 as a governed production-profile rejection" in (
        story_text
    )
    assert "Story 53 remains `proposed` and blocked" in story_text
    assert "Story 54 remains `proposed` and blocked" in story_text
    assert "no downstream story may treat the route as live" in story_text


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
