"""Tests for the normalized OpenVoice sidecar adapter modules.

Purpose:
    Protect the reusable ADR-0007 sidecar contract surface and the OpenVoice
    backend-specific capability logic without requiring heavyweight model
    downloads during local test runs.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.tts_sidecar.app_factory`.
    - Exercises `scripts.sir_convert_a_lot.tts_sidecar.openvoice_runtime`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.tts_sidecar.app_factory import create_tts_sidecar_app
from scripts.sir_convert_a_lot.tts_sidecar.contracts import (
    CacheCapability,
    CapabilityResponse,
    HealthResponse,
    LanguageCapability,
    LanguageSupportLevel,
    NetworkScope,
    NormalizationProfile,
    OutputFormat,
    ReferenceAudio,
    RuntimeCapability,
    SidecarRequestError,
    SidecarStatus,
    SynthesisCapability,
    SynthesizeRequest,
    SynthesizeResult,
    VoiceCapability,
    VoiceMode,
    VoicesResponse,
)
from scripts.sir_convert_a_lot.tts_sidecar.openvoice_runtime import (
    OpenVoiceSidecarBackend,
    OpenVoiceSidecarSettings,
    _normalize_language_code,
    _normalize_text,
    _normalized_suffix,
)


class _FakeBackend:
    def startup(self) -> None:
        return None

    def health(self) -> HealthResponse:
        return HealthResponse(
            status=SidecarStatus.OK,
            backend_id="fake_backend",
            backend_version="1.0.0",
            ready=True,
        )

    def capabilities(self) -> CapabilityResponse:
        return CapabilityResponse(
            backend_id="fake_backend",
            backend_version="1.0.0",
            backend_profile="test",
            runtime=RuntimeCapability(
                python_version="3.12.12",
                gpu_required=True,
                supports_rocm=True,
                network_scope=NetworkScope.INTERNAL_ONLY,
            ),
            cache=CacheCapability(
                cache_family="huggingface",
                host_root="/srv/cache/hf",
                container_root="/cache/hf",
                reuse_strategy="persistent_host_cache",
            ),
            synthesis=SynthesisCapability(
                output_formats=[OutputFormat.WAV],
                sample_rates_hz=[22050],
                supports_streaming=False,
            ),
            voice=VoiceCapability(
                modes=[VoiceMode.REFERENCE_CLONE],
                reference_transcript_required=False,
                reference_audio_required=True,
            ),
            languages=[
                LanguageCapability(
                    code="sv", support_level=LanguageSupportLevel.CROSS_LINGUAL_CLAIMED
                )
            ],
        )

    def voices(self) -> VoicesResponse:
        return VoicesResponse(voices=[])

    def synthesize(
        self,
        request: SynthesizeRequest,
        *,
        reference_audio: ReferenceAudio | None,
    ) -> SynthesizeResult:
        if reference_audio is None:
            raise SidecarRequestError(
                code="missing_reference_audio",
                message="missing reference audio",
                status_code=422,
            )
        if request.output_format is not OutputFormat.WAV:
            raise SidecarRequestError(
                code="unsupported_output_format",
                message="wav only",
                status_code=422,
            )
        return SynthesizeResult(
            audio_bytes=b"RIFFfakewav",
            content_type="audio/wav",
            filename="synthesized.wav",
            sample_rate_hz=22050,
        )


def test_generic_sidecar_app_exposes_normalized_contract() -> None:
    app = create_tts_sidecar_app(_FakeBackend(), title="test")

    with TestClient(app) as client:
        health_response = client.get("/health")
        capabilities_response = client.get("/capabilities")
        voices_response = client.get("/voices")
        synth_response = client.post(
            "/synthesize",
            data={
                "text": "Hej världen",
                "language": "sv",
                "voice_mode": "reference_clone",
                "output_format": "wav",
                "normalization_profile": "auto",
            },
            files={"reference_audio": ("voice.wav", b"ref", "audio/wav")},
        )

    assert health_response.json()["backend_id"] == "fake_backend"
    assert capabilities_response.json()["languages"][0]["support_level"] == "cross_lingual_claimed"
    assert voices_response.json() == {"voices": []}
    assert synth_response.headers["content-type"] == "audio/wav"
    assert synth_response.content == b"RIFFfakewav"


def test_generic_sidecar_app_returns_structured_error_payload() -> None:
    app = create_tts_sidecar_app(_FakeBackend(), title="test")

    with TestClient(app) as client:
        response = client.post(
            "/synthesize",
            data={
                "text": "Hej världen",
                "language": "sv",
                "voice_mode": "reference_clone",
                "output_format": "wav",
                "normalization_profile": "auto",
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": "missing reference audio",
        "code": "missing_reference_audio",
    }


def test_openvoice_backend_capabilities_surface_cache_and_language_truth() -> None:
    settings = OpenVoiceSidecarSettings(
        backend_id="openvoice_v2",
        backend_version="74a1d147",
        backend_profile="mms_tts_swe_base",
        bind_host="0.0.0.0",
        port=8092,
        gpu_required=True,
        openvoice_checkpoints_root=Path("/cache/openvoice/checkpoints_v2"),
        openvoice_cache_host_root="/srv/scratch/sir-convert-a-lot/cache/openvoice",
        openvoice_cache_container_root="/cache/openvoice",
        hf_cache_host_root="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        hf_cache_container_root="/cache/huggingface",
        base_model_id="facebook/mms-tts-swe",
        supported_language_codes=("sv",),
        enable_watermark=False,
        watermark_message="",
        network_scope=NetworkScope.INTERNAL_ONLY,
    )
    backend = OpenVoiceSidecarBackend(settings)
    backend._ready = True
    backend._supports_rocm = True
    backend._sample_rate_hz = 22050

    capabilities = backend.capabilities()

    assert capabilities.backend_id == "openvoice_v2"
    assert capabilities.cache.cache_family == "openvoice_assets"
    assert capabilities.auxiliary_caches[0].cache_family == "huggingface"
    assert capabilities.languages[0].code == "sv"
    assert capabilities.languages[0].support_level is LanguageSupportLevel.CROSS_LINGUAL_CLAIMED
    assert capabilities.voice.reference_transcript_required is False


def test_openvoice_backend_rejects_non_clone_requests_before_runtime_use() -> None:
    settings = OpenVoiceSidecarSettings(
        backend_id="openvoice_v2",
        backend_version="74a1d147",
        backend_profile="mms_tts_swe_base",
        bind_host="0.0.0.0",
        port=8092,
        gpu_required=True,
        openvoice_checkpoints_root=Path("/cache/openvoice/checkpoints_v2"),
        openvoice_cache_host_root="/srv/scratch/sir-convert-a-lot/cache/openvoice",
        openvoice_cache_container_root="/cache/openvoice",
        hf_cache_host_root="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        hf_cache_container_root="/cache/huggingface",
        base_model_id="facebook/mms-tts-swe",
        supported_language_codes=("sv",),
        enable_watermark=False,
        watermark_message="",
        network_scope=NetworkScope.INTERNAL_ONLY,
    )
    backend = OpenVoiceSidecarBackend(settings)
    backend._ready = True

    request = SynthesizeRequest(
        text="Hej världen",
        language="sv",
        voice_mode=VoiceMode.PRESET,
        output_format=OutputFormat.WAV,
        style_instructions=None,
        normalization_profile=NormalizationProfile.AUTO,
        preset_voice_id=None,
        reference_transcript=None,
    )

    try:
        backend.synthesize(request, reference_audio=None)
    except SidecarRequestError as exc:
        assert exc.code == "unsupported_voice_mode"
        assert exc.status_code == 422
    else:
        raise AssertionError("Expected SidecarRequestError for unsupported voice mode.")


def test_openvoice_text_helpers_normalize_language_suffixes_and_whitespace() -> None:
    assert _normalize_language_code("sv-SE") == "sv"
    assert _normalized_suffix("voice-sample.m4a") == ".m4a"
    assert (
        _normalize_text("  Hej\n\n världen  ", profile=NormalizationProfile.AUTO) == "Hej världen"
    )
