"""Chatterbox backend adapter for the normalized internal TTS sidecar contract.

Purpose:
    Wrap the official Chatterbox Multilingual Python API behind the reusable
    ADR-0007 sidecar contract so Hemma can benchmark Swedish cloning through a
    stable internal HTTP surface.

Relationships:
    - Uses the generic FastAPI surface built by `app_factory.py`.
    - Depends on the official `chatterbox-tts` package and
      `chatterbox.mtl_tts.ChatterboxMultilingualTTS`.
"""

from __future__ import annotations

import io
import logging
import os
import re
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Callable

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
    VoiceDescriptor,
    VoiceMode,
    VoicesResponse,
)

LOGGER = logging.getLogger(__name__)
_DEFAULT_PRESET_VOICE_ID = "builtin_default"
_SUPPORTED_LANGUAGE_ALIASES = {
    "en-us": "en",
    "eng": "en",
    "english": "en",
    "sv-se": "sv",
    "swe": "sv",
    "swedish": "sv",
}

if TYPE_CHECKING:
    import torch


@dataclass(frozen=True)
class ChatterboxSidecarSettings:
    """Environment-driven settings for the Task 86 Chatterbox sidecar."""

    backend_id: str
    backend_version: str
    backend_profile: str
    gpu_required: bool
    model_repo_id: str
    hf_cache_host_root: str
    hf_cache_container_root: str
    network_scope: NetworkScope
    exaggeration: float
    cfg_weight: float

    @classmethod
    def from_env(cls) -> "ChatterboxSidecarSettings":
        """Load one settings object from environment variables."""
        return cls(
            backend_id=os.environ.get(
                "SIR_TTS_SIDECAR_BACKEND_ID",
                "chatterbox_multilingual",
            ),
            backend_version=os.environ.get(
                "SIR_TTS_SIDECAR_BACKEND_VERSION",
                "0.1.6",
            ),
            backend_profile=os.environ.get(
                "SIR_TTS_SIDECAR_BACKEND_PROFILE",
                "official_multilingual_0p5b",
            ),
            gpu_required=_parse_bool_env("SIR_TTS_SIDECAR_GPU_REQUIRED", default=True),
            model_repo_id=os.environ.get(
                "SIR_TTS_SIDECAR_MODEL_REPO_ID",
                "ResembleAI/chatterbox",
            ),
            hf_cache_host_root=os.environ.get(
                "SIR_TTS_SIDECAR_HF_CACHE_HOST_ROOT",
                "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            ),
            hf_cache_container_root=os.environ.get(
                "SIR_TTS_SIDECAR_HF_CACHE_CONTAINER_ROOT",
                "/cache/huggingface",
            ),
            network_scope=NetworkScope.INTERNAL_ONLY,
            exaggeration=_parse_float_env(
                "SIR_TTS_SIDECAR_CHATTERBOX_EXAGGERATION",
                default=0.5,
            ),
            cfg_weight=_parse_float_env(
                "SIR_TTS_SIDECAR_CHATTERBOX_CFG_WEIGHT",
                default=0.5,
            ),
        )


class ChatterboxSidecarBackend:
    """Chatterbox-backed implementation of the normalized TTS sidecar contract."""

    def __init__(self, settings: ChatterboxSidecarSettings) -> None:
        self._settings = settings
        self._ready = False
        self._python_version = sys.version.split()[0]
        self._supports_rocm = False
        self._sample_rate_hz = 24000
        self._supported_languages: dict[str, str] = {}
        self._package_versions: dict[str, str | None] = {}
        self._generate: Callable[..., torch.Tensor] | None = None

    def startup(self) -> None:
        """Load the official Chatterbox Multilingual model onto the configured GPU."""
        from importlib import metadata

        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        if self._settings.gpu_required and not torch.cuda.is_available():
            raise RuntimeError(
                "Chatterbox sidecar requires GPU access, but torch.cuda is unavailable."
            )

        LOGGER.info(
            "Loading Chatterbox Multilingual model: repo_id=%s exaggeration=%s cfg_weight=%s",
            self._settings.model_repo_id,
            self._settings.exaggeration,
            self._settings.cfg_weight,
        )
        model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
        self._generate = model.generate
        self._sample_rate_hz = int(model.sr)
        self._supported_languages = {
            code.lower(): name for code, name in model.get_supported_languages().items()
        }
        self._supports_rocm = getattr(torch.version, "hip", None) is not None
        self._package_versions = {
            "chatterbox-tts": _package_version_or_none(metadata, "chatterbox-tts"),
            "torch": _package_version_or_none(metadata, "torch"),
            "torchaudio": _package_version_or_none(metadata, "torchaudio"),
            "transformers": _package_version_or_none(metadata, "transformers"),
            "diffusers": _package_version_or_none(metadata, "diffusers"),
        }
        self._ready = True
        LOGGER.info(
            "Chatterbox sidecar ready: sample_rate_hz=%s supported_languages=%s",
            self._sample_rate_hz,
            len(self._supported_languages),
        )

    def health(self) -> HealthResponse:
        """Return readiness state for the Chatterbox sidecar."""
        return HealthResponse(
            status=SidecarStatus.OK if self._ready else SidecarStatus.DEGRADED,
            backend_id=self._settings.backend_id,
            backend_version=self._settings.backend_version,
            backend_profile=self._settings.backend_profile,
            ready=self._ready,
        )

    def capabilities(self) -> CapabilityResponse:
        """Return the ADR-0007 capability document for the Chatterbox adapter."""
        languages = [
            LanguageCapability(
                code=code,
                support_level=LanguageSupportLevel.OFFICIAL,
                notes=name,
            )
            for code, name in sorted(self._supported_languages.items())
        ]
        return CapabilityResponse(
            backend_id=self._settings.backend_id,
            backend_version=self._settings.backend_version,
            backend_profile=self._settings.backend_profile,
            runtime=RuntimeCapability(
                python_version=self._python_version,
                gpu_required=self._settings.gpu_required,
                supports_rocm=self._supports_rocm,
                network_scope=self._settings.network_scope,
            ),
            cache=CacheCapability(
                cache_family="huggingface",
                host_root=self._settings.hf_cache_host_root,
                container_root=self._settings.hf_cache_container_root,
                reuse_strategy="persistent_host_cache",
            ),
            auxiliary_caches=[],
            synthesis=SynthesisCapability(
                output_formats=[OutputFormat.WAV],
                sample_rates_hz=[self._sample_rate_hz],
                supports_streaming=False,
            ),
            voice=VoiceCapability(
                modes=[VoiceMode.PRESET, VoiceMode.REFERENCE_CLONE],
                reference_transcript_required=False,
                reference_audio_required=False,
            ),
            languages=languages,
        )

    def voices(self) -> VoicesResponse:
        """Return the bounded preset voice listing for the Chatterbox adapter."""
        return VoicesResponse(
            voices=[
                VoiceDescriptor(
                    voice_id=_DEFAULT_PRESET_VOICE_ID,
                    display_name="Built-in default",
                    mode=VoiceMode.PRESET,
                    language_codes=sorted(self._supported_languages),
                )
            ]
        )

    def synthesize(
        self,
        request: SynthesizeRequest,
        *,
        reference_audio: ReferenceAudio | None,
    ) -> SynthesizeResult:
        """Synthesize audio with the official Chatterbox Multilingual generate method."""
        self._ensure_ready()
        if request.output_format is not OutputFormat.WAV:
            raise SidecarRequestError(
                code="unsupported_output_format",
                message="Chatterbox Task 86 currently supports `wav` output only.",
                status_code=422,
            )
        if request.style_instructions is not None:
            raise SidecarRequestError(
                code="unsupported_style_instructions",
                message="Chatterbox Task 86 does not expose style-instruction overrides.",
                status_code=422,
            )
        if request.reference_transcript is not None:
            raise SidecarRequestError(
                code="reference_transcript_not_supported",
                message="Chatterbox Task 86 does not use reference transcripts.",
                status_code=422,
            )
        normalized_text = _normalize_text(request.text, profile=request.normalization_profile)
        if normalized_text == "":
            raise SidecarRequestError(
                code="empty_text",
                message="The synthesis request text is empty after normalization.",
                status_code=422,
            )
        normalized_language = _normalize_language_code(request.language)
        if normalized_language not in self._supported_languages:
            raise SidecarRequestError(
                code="unsupported_language",
                message=f"Unsupported Chatterbox language: {request.language}.",
                status_code=422,
            )

        generate_kwargs = {
            "text": normalized_text,
            "language_id": normalized_language,
            "exaggeration": self._settings.exaggeration,
            "cfg_weight": self._settings.cfg_weight,
        }
        if request.voice_mode is VoiceMode.PRESET:
            preset_voice_id = request.preset_voice_id or _DEFAULT_PRESET_VOICE_ID
            if preset_voice_id != _DEFAULT_PRESET_VOICE_ID:
                raise SidecarRequestError(
                    code="unknown_preset_voice",
                    message=f"Unsupported preset voice `{preset_voice_id}`.",
                    status_code=404,
                )
            if reference_audio is not None:
                raise SidecarRequestError(
                    code="reference_audio_not_allowed",
                    message="Preset synthesis does not accept reference audio.",
                    status_code=422,
                )
        elif request.voice_mode is VoiceMode.REFERENCE_CLONE:
            if request.preset_voice_id is not None:
                raise SidecarRequestError(
                    code="preset_voice_not_allowed",
                    message="Reference cloning does not accept `preset_voice_id`.",
                    status_code=422,
                )
            if reference_audio is None or len(reference_audio.data) == 0:
                raise SidecarRequestError(
                    code="missing_reference_audio",
                    message="Reference audio is required for Chatterbox cloning.",
                    status_code=422,
                )
            with TemporaryDirectory(prefix="chatterbox-ref-") as temp_dir_raw:
                temp_dir = Path(temp_dir_raw)
                source_reference_path = (
                    temp_dir / f"reference{_normalized_suffix(reference_audio.filename)}"
                )
                prepared_reference_path = temp_dir / "reference_prompt.wav"
                source_reference_path.write_bytes(reference_audio.data)
                _prepare_reference_audio(
                    source_path=source_reference_path,
                    target_path=prepared_reference_path,
                )
                generate_kwargs["audio_prompt_path"] = prepared_reference_path.as_posix()
                audio_bytes = _run_generate(self._generate, self._sample_rate_hz, generate_kwargs)
        else:
            raise SidecarRequestError(
                code="unsupported_voice_mode",
                message=f"Unsupported voice mode `{request.voice_mode}`.",
                status_code=422,
            )
        if request.voice_mode is VoiceMode.PRESET:
            audio_bytes = _run_generate(self._generate, self._sample_rate_hz, generate_kwargs)
        return SynthesizeResult(
            audio_bytes=audio_bytes,
            content_type="audio/wav",
            filename="synthesized.wav",
            sample_rate_hz=self._sample_rate_hz,
        )

    @property
    def package_versions(self) -> dict[str, str | None]:
        """Expose package versions for runtime-truth reporting."""
        return dict(self._package_versions)

    def _ensure_ready(self) -> None:
        if not self._ready or self._generate is None:
            raise SidecarRequestError(
                code="backend_not_ready",
                message="The Chatterbox sidecar is not ready yet.",
                status_code=503,
            )


def _run_generate(
    generate_fn: Callable[..., torch.Tensor] | None,
    sample_rate_hz: int,
    generate_kwargs: dict[str, object],
) -> bytes:
    """Run the official generate function and serialize the returned waveform."""
    if generate_fn is None:
        raise RuntimeError("Chatterbox generate function was not initialized.")
    try:
        waveform = generate_fn(**generate_kwargs)
    except ValueError as exc:
        raise SidecarRequestError(
            code="invalid_generation_request",
            message=str(exc),
            status_code=422,
        ) from exc
    except AssertionError as exc:
        raise SidecarRequestError(
            code="missing_conditionals",
            message=str(exc),
            status_code=422,
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive runtime envelope
        raise SidecarRequestError(
            code="chatterbox_generate_failed",
            message=f"Chatterbox generation failed: {exc}",
            status_code=500,
        ) from exc
    return _wave_bytes_from_tensor(waveform, sample_rate_hz=sample_rate_hz)


def _wave_bytes_from_tensor(waveform: torch.Tensor, *, sample_rate_hz: int) -> bytes:
    """Serialize one mono float waveform tensor into deterministic WAV bytes."""
    tensor = getattr(waveform, "detach", lambda: waveform)()
    tensor = getattr(tensor, "cpu", lambda: tensor)()
    tensor = getattr(tensor, "float", lambda: tensor)()
    if getattr(tensor, "ndim", None) == 1:
        tensor = tensor.unsqueeze(0)
    if getattr(tensor, "ndim", None) != 2:
        raise RuntimeError("Expected a 2D waveform tensor from Chatterbox generate().")
    if tensor.shape[0] > 1:
        tensor = tensor[:1, :]
    clipped = tensor.clamp(-1.0, 1.0)
    pcm16 = (clipped.squeeze(0).numpy() * 32767.0).round().astype("<i2")
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate_hz)
            wav_file.writeframes(pcm16.tobytes())
        return buffer.getvalue()


def _normalize_language_code(language: str) -> str:
    """Map human-friendly language identifiers to official Chatterbox codes."""
    normalized = language.strip().lower()
    return _SUPPORTED_LANGUAGE_ALIASES.get(normalized, normalized)


def _normalize_text(text: str, *, profile: NormalizationProfile) -> str:
    """Apply one small deterministic normalization policy before generation."""
    stripped = text.strip()
    if profile is NormalizationProfile.NONE:
        return stripped
    return re.sub(r"\s+", " ", stripped)


def _normalized_suffix(filename: str) -> str:
    """Return a safe suffix that preserves the file extension when present."""
    suffix = Path(filename).suffix.lower()
    return suffix if suffix != "" else ".bin"


def _prepare_reference_audio(*, source_path: Path, target_path: Path) -> None:
    """Convert one uploaded reference clip into a stable Chatterbox prompt WAV."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            source_path.as_posix(),
            "-ac",
            "1",
            "-ar",
            "24000",
            "-sample_fmt",
            "s16",
            target_path.as_posix(),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SidecarRequestError(
            code="reference_audio_prepare_failed",
            message=(
                "Failed to convert reference audio for Chatterbox.\n"
                f"stdout:\n{result.stdout.strip()}\n"
                f"stderr:\n{result.stderr.strip()}"
            ).strip(),
            status_code=422,
        )


def _parse_bool_env(name: str, *, default: bool) -> bool:
    """Return one boolean environment variable with a deterministic fallback."""
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean-like value, got `{value}`.")


def _parse_float_env(name: str, *, default: float) -> float:
    """Return one float environment variable with validation and fallback."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a float-like value, got `{value}`.") from exc


def _package_version_or_none(metadata_module: object, distribution_name: str) -> str | None:
    """Return one installed package version or `None` when not installed."""
    version_fn = getattr(metadata_module, "version")
    package_not_found_error = getattr(metadata_module, "PackageNotFoundError")
    try:
        return str(version_fn(distribution_name))
    except package_not_found_error:
        return None
