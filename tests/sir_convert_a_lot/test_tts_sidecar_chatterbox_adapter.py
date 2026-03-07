"""Tests for the normalized Chatterbox sidecar adapter modules.

Purpose:
    Protect the reusable ADR-0007 sidecar contract surface and the Chatterbox
    backend-specific capability logic without requiring heavyweight model
    downloads during local test runs.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.tts_sidecar.chatterbox_runtime`.
    - Mirrors the normalized adapter coverage style used for Task 81 and Task 85.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import torch

from scripts.sir_convert_a_lot.tts_sidecar.chatterbox_runtime import (
    ChatterboxSidecarBackend,
    ChatterboxSidecarSettings,
    _normalize_language_code,
    _normalize_text,
    _run_generate,
)
from scripts.sir_convert_a_lot.tts_sidecar.contracts import (
    LanguageSupportLevel,
    NetworkScope,
    NormalizationProfile,
    OutputFormat,
    ReferenceAudio,
    SynthesizeRequest,
    VoiceMode,
)


def _settings() -> ChatterboxSidecarSettings:
    return ChatterboxSidecarSettings(
        backend_id="chatterbox_multilingual",
        backend_version="0.1.6",
        backend_profile="official_multilingual_0p5b",
        gpu_required=True,
        model_repo_id="ResembleAI/chatterbox",
        hf_cache_host_root="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        hf_cache_container_root="/cache/huggingface",
        network_scope=NetworkScope.INTERNAL_ONLY,
        exaggeration=0.5,
        cfg_weight=0.5,
    )


def test_chatterbox_backend_capabilities_surface_official_swedish_support() -> None:
    backend = ChatterboxSidecarBackend(_settings())
    backend._ready = True
    backend._supports_rocm = True
    backend._sample_rate_hz = 24000
    backend._supported_languages = {"en": "English", "sv": "Swedish"}

    capabilities = backend.capabilities()
    voices = backend.voices()

    assert capabilities.backend_id == "chatterbox_multilingual"
    assert capabilities.languages[1].support_level is LanguageSupportLevel.OFFICIAL
    assert capabilities.voice.reference_transcript_required is False
    assert capabilities.voice.reference_audio_required is False
    assert capabilities.voice.modes == [VoiceMode.PRESET, VoiceMode.REFERENCE_CLONE]
    assert voices.voices[0].voice_id == "builtin_default"


def test_chatterbox_backend_synthesizes_preset_and_clone_with_official_kwargs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    backend = ChatterboxSidecarBackend(_settings())
    backend._ready = True
    backend._sample_rate_hz = 24000
    backend._supported_languages = {"en": "English", "sv": "Swedish"}
    calls: list[dict[str, object]] = []

    def _fake_generate(**kwargs: object) -> torch.Tensor:
        calls.append(kwargs)
        return torch.zeros(1, 4)

    def _fake_prepare_reference_audio(*, source_path: Path, target_path: Path) -> None:
        target_path.write_bytes(source_path.read_bytes())

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.tts_sidecar.chatterbox_runtime._prepare_reference_audio",
        _fake_prepare_reference_audio,
    )
    backend._generate = _fake_generate

    preset_result = backend.synthesize(
        SynthesizeRequest(
            text="This is a smoke test.",
            language="en",
            voice_mode=VoiceMode.PRESET,
            output_format=OutputFormat.WAV,
            style_instructions=None,
            normalization_profile=NormalizationProfile.AUTO,
            preset_voice_id="builtin_default",
            reference_transcript=None,
        ),
        reference_audio=None,
    )
    clone_result = backend.synthesize(
        SynthesizeRequest(
            text="Hej världen",
            language="sv",
            voice_mode=VoiceMode.REFERENCE_CLONE,
            output_format=OutputFormat.WAV,
            style_instructions=None,
            normalization_profile=NormalizationProfile.AUTO,
            preset_voice_id=None,
            reference_transcript=None,
        ),
        reference_audio=ReferenceAudio(
            filename=(tmp_path / "voice.m4a").name,
            content_type="audio/mp4",
            data=b"audio",
        ),
    )

    assert preset_result.content_type == "audio/wav"
    assert clone_result.content_type == "audio/wav"
    assert calls[0] == {
        "text": "This is a smoke test.",
        "language_id": "en",
        "exaggeration": 0.5,
        "cfg_weight": 0.5,
    }
    assert calls[1]["language_id"] == "sv"
    audio_prompt_path = calls[1]["audio_prompt_path"]
    assert isinstance(audio_prompt_path, str)
    assert audio_prompt_path == str(Path(audio_prompt_path))


def test_chatterbox_backend_rejects_reference_transcript_and_unknown_preset() -> None:
    backend = ChatterboxSidecarBackend(_settings())
    backend._ready = True
    backend._sample_rate_hz = 24000
    backend._supported_languages = {"sv": "Swedish"}
    backend._generate = _noop_generate

    with pytest.raises(Exception) as transcript_error:
        backend.synthesize(
            SynthesizeRequest(
                text="Hej världen",
                language="sv",
                voice_mode=VoiceMode.PRESET,
                output_format=OutputFormat.WAV,
                style_instructions=None,
                normalization_profile=NormalizationProfile.AUTO,
                preset_voice_id="builtin_default",
                reference_transcript="Hej världen",
            ),
            reference_audio=None,
        )
    with pytest.raises(Exception) as preset_error:
        backend.synthesize(
            SynthesizeRequest(
                text="Hej världen",
                language="sv",
                voice_mode=VoiceMode.PRESET,
                output_format=OutputFormat.WAV,
                style_instructions=None,
                normalization_profile=NormalizationProfile.AUTO,
                preset_voice_id="unknown",
                reference_transcript=None,
            ),
            reference_audio=None,
        )

    assert "does not use reference transcripts" in str(transcript_error.value)
    assert "Unsupported preset voice" in str(preset_error.value)


def test_run_generate_wraps_value_error_into_sidecar_error() -> None:
    def _raise_value_error(**_kwargs: object) -> torch.Tensor:
        raise ValueError("Unsupported language_id")

    with pytest.raises(Exception) as exc_info:
        _run_generate(_raise_value_error, 24000, {"text": "Hej", "language_id": "zz"})

    assert "Unsupported language_id" in str(exc_info.value)


def test_chatterbox_normalization_helpers_keep_supported_aliases() -> None:
    assert _normalize_language_code("Swedish") == "sv"
    assert _normalize_language_code("en-US") == "en"
    assert _normalize_text("  Hej   världen  ", profile=NormalizationProfile.AUTO) == "Hej världen"
    assert (
        _normalize_text("  Hej   världen  ", profile=NormalizationProfile.NONE) == "Hej   världen"
    )


def _noop_generate(**_kwargs: object) -> torch.Tensor:
    raise AssertionError("Should not be called")
