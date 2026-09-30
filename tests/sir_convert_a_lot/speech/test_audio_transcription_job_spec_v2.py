"""Audio transcription Service API v2 JobSpec validation behavior.

Purpose:
    Prove `JobSpecV2` accepts, normalizes, and rejects `audio ->
    transcript_bundle` public options, diarization, retention, and execution
    fields before any HTTP admission happens.

Relationships:
    - Exercises `domain.specs_v2` as the audio route validation authority.
    - Builds payloads through `audio_route_admission_test_support`.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from tests.sir_convert_a_lot.speech.audio_route_admission_test_support import (
    audio_job_spec as _audio_job_spec,
)


@pytest.mark.parametrize(
    ("language", "diarization"),
    [
        (
            "auto",
            {
                "mode": "auto",
                "num_speakers": None,
                "min_speakers": None,
                "max_speakers": None,
            },
        ),
        (
            "sv",
            {
                "mode": "known_speaker_count",
                "num_speakers": 2,
                "min_speakers": None,
                "max_speakers": None,
            },
        ),
        (
            "en",
            {
                "mode": "speaker_range",
                "num_speakers": None,
                "min_speakers": 1,
                "max_speakers": 4,
            },
        ),
    ],
)
def test_job_spec_accepts_audio_transcript_bundle_public_options(
    language: str,
    diarization: Mapping[str, object],
) -> None:
    spec = JobSpecV2.model_validate(_audio_job_spec(language=language, diarization=diarization))

    assert spec.source.format.value == "audio"
    assert spec.conversion.output_format.value == "transcript_bundle"
    assert spec.audio_transcription_options is not None
    assert spec.audio_transcription_options.language == language
    assert spec.audio_transcription_options.output_artifacts == ("json",)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (("txt",), ("json", "txt")),
        (("json", "srt"), ("json", "srt")),
        (("vtt", "json", "vtt", "md"), ("json", "md", "vtt")),
        (("json", "txt", "md", "vtt", "srt"), ("json", "txt", "md", "vtt", "srt")),
    ],
)
def test_job_spec_accepts_and_normalizes_audio_formatter_output_artifacts(
    requested: tuple[str, ...],
    expected: tuple[str, ...],
) -> None:
    spec = JobSpecV2.model_validate(
        _audio_job_spec(audio_options_patch={"output_artifacts": requested})
    )

    assert spec.audio_transcription_options is not None
    assert spec.audio_transcription_options.output_artifacts == expected


@pytest.mark.parametrize(
    ("patch", "expected_code"),
    [
        ({"language": "fr"}, "audio_public_options_unsupported"),
        ({"output_artifacts": ("json", "pdf")}, "audio_public_options_unsupported"),
        ({"max_duration_seconds": 0}, "audio_duration_exceeded"),
        ({"max_duration_seconds": 7201}, "audio_duration_exceeded"),
        ({"model_id": "provider/raw-stt-model"}, "audio_public_options_unsupported"),
    ],
)
def test_job_spec_rejects_invalid_audio_public_options(
    patch: Mapping[str, object],
    expected_code: str,
) -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(audio_options_patch=patch))

    assert expected_code in str(error_info.value)


@pytest.mark.parametrize(
    "diarization",
    [
        {
            "mode": "auto",
            "num_speakers": 2,
            "min_speakers": None,
            "max_speakers": None,
        },
        {
            "mode": "known_speaker_count",
            "num_speakers": 0,
            "min_speakers": None,
            "max_speakers": None,
        },
        {
            "mode": "speaker_range",
            "num_speakers": None,
            "min_speakers": 4,
            "max_speakers": 2,
        },
    ],
)
def test_job_spec_rejects_invalid_audio_diarization_options(
    diarization: Mapping[str, object],
) -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(diarization=diarization))

    assert "audio_diarization_options_invalid" in str(error_info.value)


def test_job_spec_rejects_audio_retention_pin() -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(retention_pin=True))

    assert "audio_retention_pin_unsupported" in str(error_info.value)


def test_job_spec_requires_audio_transcription_options_for_audio_route() -> None:
    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_audio_job_spec(include_audio_options=False))

    assert "audio_transcription_options is required" in str(error_info.value)


def test_job_spec_requires_audio_execution_with_route_message() -> None:
    payload = _audio_job_spec()
    payload.pop("execution")

    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(payload)

    error_text = str(error_info.value)
    assert "execution is required for audio transcription routes" in error_text
    assert "source.format is 'pdf'" not in error_text
