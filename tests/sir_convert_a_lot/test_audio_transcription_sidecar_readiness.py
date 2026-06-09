"""Behavioral tests for STT sidecar readiness parsing.

Purpose:
    Prove the audio transcription sidecar contract fails closed on unsafe
    runtime, model/cache, secret, media, and normalized-audio capability truth.

Relationships:
    - Exercises sidecar health and capability parsing before route execution
      exists.
    - Complements route-admission tests by proving sidecar readiness cannot
      drift from the governed converter contract.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from scripts.sir_convert_a_lot.domain.audio_transcription_policy import (
    AudioTranscriptionErrorCode,
    evaluate_stt_sidecar_readiness,
)
from tests.sir_convert_a_lot.audio_transcription_test_support import (
    capabilities,
    health,
    media_capability,
    media_capability_without_normalized_audio,
)


@pytest.mark.parametrize(
    ("health_patch", "capability_patch", "expected_code"),
    [
        (
            {"gpu_ready": False},
            {},
            AudioTranscriptionErrorCode.GPU_REQUIRED_UNAVAILABLE,
        ),
        (
            {},
            {"runtime": {"published_port_allowed": True}},
            AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE,
        ),
        (
            {},
            {"cache": {"model_artifacts_present": False}},
            AudioTranscriptionErrorCode.MODEL_CACHE_UNAVAILABLE,
        ),
        (
            {},
            {"secrets": {"required_secrets_present": False}},
            AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED,
        ),
        (
            {},
            {"transcription": {"model_id": "openai/whisper-large-v3"}},
            AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE,
        ),
    ],
)
def test_sidecar_readiness_fails_closed_for_unsafe_capability_truth(
    health_patch: Mapping[str, object],
    capability_patch: Mapping[str, object],
    expected_code: AudioTranscriptionErrorCode,
) -> None:
    readiness = evaluate_stt_sidecar_readiness(
        health_payload=health(**health_patch),
        capability_payload=capabilities(**capability_patch),
    )

    assert readiness.ready is False
    assert readiness.error_code == expected_code


def test_sidecar_readiness_accepts_internal_gpu_ready_provider_neutral_profile() -> None:
    readiness = evaluate_stt_sidecar_readiness(
        health_payload=health(),
        capability_payload=capabilities(),
    )

    assert readiness.ready is True
    assert readiness.error_code is None
    assert readiness.profile_labels == {
        "stt_profile": "stt_sv_en_primary",
        "diarization_profile": "diarization_sv_en_primary",
    }


def test_sidecar_readiness_fails_closed_when_media_caps_cannot_satisfy_route() -> None:
    readiness = evaluate_stt_sidecar_readiness(
        health_payload=health(),
        capability_payload=capabilities(
            media={
                "max_upload_bytes": 100,
                "max_duration_seconds": 600,
                "accepted_containers": ["wav"],
                "input_protocols": ["local_upload"],
            }
        ),
    )

    assert readiness.ready is False
    assert readiness.error_code == AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE
    assert readiness.details == {"reason": "max_upload_bytes_below_route_contract"}


@pytest.mark.parametrize(
    ("normalized_audio", "expected_reason"),
    [
        (None, "normalized_audio_missing"),
        (
            {
                "container": "flac",
                "sample_rate_hz": 16000,
                "channels": 1,
                "sample_format": "s16",
            },
            "normalized_audio_container_unsupported",
        ),
        (
            {
                "container": "wav",
                "sample_rate_hz": 44100,
                "channels": 1,
                "sample_format": "s16",
            },
            "normalized_audio_sample_rate_unsupported",
        ),
        (
            {
                "container": "wav",
                "sample_rate_hz": 16000,
                "channels": 2,
                "sample_format": "s16",
            },
            "normalized_audio_channels_unsupported",
        ),
        (
            {
                "container": "wav",
                "sample_rate_hz": 16000,
                "channels": 1,
                "sample_format": "f32",
            },
            "normalized_audio_sample_format_unsupported",
        ),
    ],
)
def test_sidecar_readiness_fails_closed_without_required_normalized_audio_contract(
    normalized_audio: Mapping[str, object] | None,
    expected_reason: str,
) -> None:
    media = (
        media_capability_without_normalized_audio()
        if normalized_audio is None
        else media_capability(normalized_audio=normalized_audio)
    )

    readiness = evaluate_stt_sidecar_readiness(
        health_payload=health(),
        capability_payload=capabilities(media=media),
    )

    assert readiness.ready is False
    assert readiness.error_code == AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE
    assert readiness.details == {"reason": expected_reason}
