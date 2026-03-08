"""Tests for the normalized F5-TTS sidecar adapter modules.

Purpose:
    Protect the reusable ADR-0007 sidecar contract surface and the F5-TTS
    backend-specific capability logic without requiring heavyweight model
    downloads during local test runs.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.tts_sidecar.f5_runtime`.
    - Mirrors the normalized adapter coverage style used for Task 81.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.tts_sidecar.contracts import (
    LanguageSupportLevel,
    NetworkScope,
    NormalizationProfile,
    OutputFormat,
    ReferenceAudio,
    SynthesizeRequest,
    VoiceMode,
)
from scripts.sir_convert_a_lot.tts_sidecar.f5_runtime import (
    F5TtsSidecarBackend,
    F5TtsSidecarSettings,
    _render_infer_toml,
)


def _settings() -> F5TtsSidecarSettings:
    return F5TtsSidecarSettings(
        backend_id="f5_tts_swedish",
        backend_version="swedish-tts",
        backend_profile="f5tts_v1_base_swedish_finetune",
        gpu_required=True,
        model_name="F5TTS_v1_Base",
        model_repo_id="EkhoCollective/f5-tts-swedish",
        model_root=Path("/models/swedish"),
        model_cfg_path=None,
        hf_cache_host_root="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        hf_cache_container_root="/cache/huggingface",
        model_cache_host_root="/srv/scratch/sir-convert-a-lot/cache/f5-tts-swedish",
        model_cache_container_root="/models",
        supported_language_codes=("sv",),
        network_scope=NetworkScope.INTERNAL_ONLY,
        remove_silence=False,
        nfe_step=64,
        cfg_strength=2.0,
        sway_sampling_coef=-1.0,
        speed=1.0,
        fix_duration=None,
        cross_fade_duration=0.15,
        target_rms=0.1,
        vocoder_name="vocos",
        load_vocoder_from_local=False,
    )


def test_f5_backend_capabilities_require_reference_transcript() -> None:
    backend = F5TtsSidecarBackend(_settings())
    backend._ready = True
    backend._supports_rocm = True
    backend._sample_rate_hz = 24000

    capabilities = backend.capabilities()

    assert capabilities.backend_id == "f5_tts_swedish"
    assert capabilities.languages[0].support_level is LanguageSupportLevel.EXPERIMENTAL
    assert capabilities.voice.reference_audio_required is True
    assert capabilities.voice.reference_transcript_required is True
    assert capabilities.synthesis.sample_rates_hz == [24000]


def test_f5_backend_rejects_missing_reference_transcript() -> None:
    backend = F5TtsSidecarBackend(_settings())
    backend._ready = True

    with pytest.raises(Exception) as exc_info:
        backend.synthesize(
            SynthesizeRequest(
                text="Hej varlden",
                language="sv",
                voice_mode=VoiceMode.REFERENCE_CLONE,
                output_format=OutputFormat.WAV,
                style_instructions=None,
                normalization_profile=NormalizationProfile.AUTO,
                preset_voice_id=None,
                reference_transcript=None,
            ),
            reference_audio=ReferenceAudio(
                filename="voice.wav",
                content_type="audio/wav",
                data=b"ref",
            ),
        )

    assert "Reference transcript is required" in str(exc_info.value)


def test_render_infer_toml_includes_deterministic_paths() -> None:
    config = _render_infer_toml(
        model_name="F5TTS_v1_Base",
        ckpt_file=Path("/models/swedish/model_last.pt"),
        vocab_file=Path("/models/swedish/vocab.txt"),
        ref_audio=Path("/tmp/reference.wav"),
        ref_text="Hej hej",
        gen_text=None,
        gen_file=Path("/tmp/gen_text.txt"),
        output_dir=Path("/tmp/output"),
        output_file="sample.wav",
        model_cfg_path=None,
        remove_silence=True,
        nfe_step=64,
        cfg_strength=2.5,
        sway_sampling_coef=0.0,
        speed=0.9,
        fix_duration=12.0,
        cross_fade_duration=0.2,
        target_rms=0.12,
        vocoder_name="bigvgan",
        load_vocoder_from_local=True,
    )

    assert 'ckpt_file = "/models/swedish/model_last.pt"' in config
    assert 'vocab_file = "/models/swedish/vocab.txt"' in config
    assert 'output_file = "sample.wav"' in config
    assert 'gen_text = ""' in config
    assert 'gen_file = "/tmp/gen_text.txt"' in config
    assert "remove_silence = true" in config
    assert "nfe_step = 64" in config
    assert "cfg_strength = 2.5" in config
    assert "sway_sampling_coef = 0.0" in config
    assert "speed = 0.9" in config
    assert "fix_duration = 12.0" in config
    assert "cross_fade_duration = 0.2" in config
    assert "target_rms = 0.12" in config
    assert 'vocoder_name = "bigvgan"' in config
    assert "load_vocoder_from_local = true" in config
