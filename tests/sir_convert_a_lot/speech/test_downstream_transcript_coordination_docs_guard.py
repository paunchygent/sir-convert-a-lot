"""Downstream transcript coordination docs guard.

Purpose:
    Prove Gateway and downstream transcript-delivery coordination remains
    truthful while Sir Convert exposes admission-only audio route behavior.

Relationships:
    - Reads the governed Sir Convert planning authority for the HuleEdu and
      Skriptoteket transcript-delivery handoff.
    - Guards audio-transcription route and contract records without requiring
      sibling repositories to exist at absolute paths.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs_v2 import (
    JobSpecV2,
    OutputFormatV2,
    SourceFormatV2,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

AUDIO_TRANSCRIPTION_CONTRACT_PATH = (
    REPO_ROOT
    / "docs"
    / "reference"
    / (
        "ref-sircon-general-audio-transcription-service-api-artifact-contract-"
        "audio-transcription-service-api-artifact-contract.md"
    )
)


def test_audio_contract_initial_request_shape_is_admissible() -> None:
    contract_source = AUDIO_TRANSCRIPTION_CONTRACT_PATH.read_text(encoding="utf-8")
    payload = _json_block_after_heading(contract_source, "## Initial Request Shape")

    spec = JobSpecV2.model_validate(payload)

    assert spec.source.format == SourceFormatV2.AUDIO
    assert spec.conversion.output_format == OutputFormatV2.TRANSCRIPT_BUNDLE
    assert spec.conversion.artifact_language is None
    assert spec.audio_transcription_options is not None
    assert spec.audio_transcription_options.language == "auto"


def _json_block_after_heading(markdown: str, heading: str) -> dict[str, object]:
    heading_start = markdown.index(heading)
    request_line = markdown[heading_start:].splitlines()[1]
    decoded = json.loads(request_line.strip("`"))
    if not isinstance(decoded, dict):
        raise AssertionError("Expected contract JSON example to decode to an object.")
    return {str(key): value for key, value in decoded.items()}
