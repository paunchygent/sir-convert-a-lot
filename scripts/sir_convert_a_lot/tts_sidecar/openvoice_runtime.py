"""OpenVoice V2 backend adapter for the normalized internal TTS sidecar contract.

Purpose:
    Wrap OpenVoice V2 voice conversion plus a Swedish MMS base synthesizer behind
    the reusable ADR-0007 sidecar contract so Hemma benchmarks can evaluate a
    cloning-capable backend without exposing backend-native APIs.

Relationships:
    - Uses the generic FastAPI surface built by `app_factory.py`.
    - Depends on OpenVoice V2 for tone-color conversion and `facebook/mms-tts-swe`
      as the Swedish base speaker generator for the OpenVoice benchmark.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, ContextManager

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
from scripts.sir_convert_a_lot.tts_sidecar.openvoice_support import (
    _BaseModel,
    _create_tone_color_converter,
    _normalized_suffix,
    _OpenVoiceConverter,
    _optional_path_env,
    _package_version_or_none,
    _parse_bool_env,
    _positive_int,
    _resample_audio_file,
    _Tokenizer,
    extract_target_speaker_embedding,
)

_SUPPORTED_LANGUAGE_ALIASES = {
    "sv": "sv",
    "sv-se": "sv",
    "swedish": "sv",
}


@dataclass(frozen=True)
class OpenVoiceSidecarSettings:
    """Environment-driven settings for the OpenVoice OpenVoice benchmark sidecar."""

    backend_id: str
    backend_version: str
    backend_profile: str
    bind_host: str
    port: int
    gpu_required: bool
    openvoice_checkpoints_root: Path
    openvoice_cache_host_root: str
    openvoice_cache_container_root: str
    hf_cache_host_root: str
    hf_cache_container_root: str
    torch_cache_host_root: str
    torch_cache_container_root: str
    base_model_id: str
    supported_language_codes: tuple[str, ...]
    network_scope: NetworkScope
    debug_artifact_dir: Path | None

    @classmethod
    def from_env(cls) -> "OpenVoiceSidecarSettings":
        """Load one settings object from environment variables."""
        supported_codes = tuple(
            candidate.strip().lower()
            for candidate in os.environ.get("SIR_TTS_SIDECAR_ALLOWED_LANGUAGE_CODES", "sv").split(
                ","
            )
            if candidate.strip() != ""
        )
        if not supported_codes:
            raise RuntimeError("SIR_TTS_SIDECAR_ALLOWED_LANGUAGE_CODES must not be empty.")
        return cls(
            backend_id=os.environ.get("SIR_TTS_SIDECAR_BACKEND_ID", "openvoice_v2"),
            backend_version=os.environ.get("SIR_TTS_SIDECAR_BACKEND_VERSION", "unknown"),
            backend_profile=os.environ.get(
                "SIR_TTS_SIDECAR_BACKEND_PROFILE",
                "mms_tts_swe_base",
            ),
            bind_host=os.environ.get("SIR_TTS_SIDECAR_BIND_HOST", "0.0.0.0"),
            port=int(os.environ.get("SIR_TTS_SIDECAR_PORT", "8092")),
            gpu_required=_parse_bool_env("SIR_TTS_SIDECAR_GPU_REQUIRED", default=True),
            openvoice_checkpoints_root=Path(
                os.environ.get(
                    "SIR_TTS_SIDECAR_OPENVOICE_CHECKPOINTS_ROOT",
                    "/cache/openvoice/checkpoints_v2",
                )
            ),
            openvoice_cache_host_root=os.environ.get(
                "SIR_TTS_SIDECAR_OPENVOICE_CACHE_HOST_ROOT",
                "/srv/scratch/sir-convert-a-lot/cache/openvoice",
            ),
            openvoice_cache_container_root=os.environ.get(
                "SIR_TTS_SIDECAR_OPENVOICE_CACHE_CONTAINER_ROOT",
                "/cache/openvoice",
            ),
            hf_cache_host_root=os.environ.get(
                "SIR_TTS_SIDECAR_HF_CACHE_HOST_ROOT",
                "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            ),
            hf_cache_container_root=os.environ.get(
                "SIR_TTS_SIDECAR_HF_CACHE_CONTAINER_ROOT",
                "/cache/huggingface",
            ),
            torch_cache_host_root=os.environ.get(
                "SIR_TTS_SIDECAR_TORCH_CACHE_HOST_ROOT",
                "/srv/scratch/sir-convert-a-lot/cache/huggingface/torch",
            ),
            torch_cache_container_root=os.environ.get(
                "SIR_TTS_SIDECAR_TORCH_CACHE_CONTAINER_ROOT",
                "/cache/huggingface/torch",
            ),
            base_model_id=os.environ.get("SIR_TTS_SIDECAR_BASE_MODEL_ID", "facebook/mms-tts-swe"),
            supported_language_codes=supported_codes,
            network_scope=NetworkScope.INTERNAL_ONLY,
            debug_artifact_dir=_optional_path_env("SIR_TTS_SIDECAR_DEBUG_ARTIFACT_DIR"),
        )


class OpenVoiceSidecarBackend:
    """OpenVoice-backed implementation of the normalized TTS sidecar contract."""

    def __init__(self, settings: OpenVoiceSidecarSettings) -> None:
        self._settings = settings
        self._ready = False
        self._python_version = sys.version.split()[0]
        self._supports_rocm = False
        self._converter: _OpenVoiceConverter | None = None
        self._base_model: _BaseModel | None = None
        self._tokenizer: _Tokenizer | None = None
        self._manual_seed: Callable[[int], object] | None = None
        self._inference_mode_factory: Callable[[], ContextManager[object]] | None = None
        self._sample_rate_hz = 0
        self._converter_sample_rate_hz = 0
        self._base_model_sample_rate_hz = 0
        self._package_versions: dict[str, str | None] = {}

    def startup(self) -> None:
        """Load OpenVoice and the Swedish MMS base model onto the configured GPU."""
        import torch
        from transformers import AutoTokenizer, VitsModel

        if self._settings.gpu_required and not torch.cuda.is_available():
            raise RuntimeError(
                "OpenVoice sidecar requires GPU access, but torch.cuda is unavailable."
            )

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        checkpoints_root = self._settings.openvoice_checkpoints_root
        converter_root = checkpoints_root / "converter"
        config_path = converter_root / "config.json"
        checkpoint_path = converter_root / "checkpoint.pth"
        if not config_path.exists() or not checkpoint_path.exists():
            raise RuntimeError(
                "OpenVoice V2 checkpoints are missing. Expected converter assets under "
                f"{converter_root.as_posix()}."
            )

        converter = _create_tone_color_converter(config_path, device=device)
        converter.load_ckpt(checkpoint_path.as_posix())
        tokenizer: _Tokenizer = AutoTokenizer.from_pretrained(self._settings.base_model_id)
        base_model: _BaseModel = VitsModel.from_pretrained(self._settings.base_model_id).to(device)
        base_model.eval()

        converter_sample_rate_hz = _positive_int(
            converter.hps.data.sampling_rate, label="OpenVoice converter sampling rate"
        )
        base_model_sample_rate_hz = _positive_int(
            getattr(getattr(base_model, "config", None), "sampling_rate", None),
            label="Swedish base-model sampling rate",
        )
        self._converter = converter
        self._tokenizer = tokenizer
        self._base_model = base_model
        self._manual_seed = torch.manual_seed
        self._inference_mode_factory = torch.inference_mode
        self._sample_rate_hz = converter_sample_rate_hz
        self._converter_sample_rate_hz = converter_sample_rate_hz
        self._base_model_sample_rate_hz = base_model_sample_rate_hz
        self._supports_rocm = getattr(torch.version, "hip", None) is not None
        self._package_versions = {
            "openvoice": _package_version_or_none("openvoice"),
            "transformers": _package_version_or_none("transformers"),
            "torch": _package_version_or_none("torch"),
            "torchaudio": _package_version_or_none("torchaudio"),
            "onnxruntime": _package_version_or_none("onnxruntime"),
        }
        self._ready = True

    def health(self) -> HealthResponse:
        """Return readiness state for the OpenVoice sidecar."""
        return HealthResponse(
            status=SidecarStatus.OK if self._ready else SidecarStatus.DEGRADED,
            backend_id=self._settings.backend_id,
            backend_version=self._settings.backend_version,
            backend_profile=self._settings.backend_profile,
            ready=self._ready,
        )

    def capabilities(self) -> CapabilityResponse:
        """Return the ADR-0007 capability document for the OpenVoice adapter."""
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
                cache_family="openvoice_assets",
                host_root=self._settings.openvoice_cache_host_root,
                container_root=self._settings.openvoice_cache_container_root,
                reuse_strategy="persistent_host_cache",
            ),
            auxiliary_caches=[
                CacheCapability(
                    cache_family="huggingface",
                    host_root=self._settings.hf_cache_host_root,
                    container_root=self._settings.hf_cache_container_root,
                    reuse_strategy="persistent_host_cache",
                ),
                CacheCapability(
                    cache_family="torch_hub",
                    host_root=self._settings.torch_cache_host_root,
                    container_root=self._settings.torch_cache_container_root,
                    reuse_strategy="persistent_host_cache",
                ),
            ],
            synthesis=SynthesisCapability(
                output_formats=[OutputFormat.WAV],
                sample_rates_hz=[self._sample_rate_hz] if self._sample_rate_hz > 0 else [],
                supports_streaming=False,
            ),
            voice=VoiceCapability(
                modes=[VoiceMode.REFERENCE_CLONE],
                reference_transcript_required=False,
                reference_audio_required=True,
            ),
            languages=[
                LanguageCapability(
                    code="sv",
                    support_level=LanguageSupportLevel.CROSS_LINGUAL_CLAIMED,
                    notes=(
                        "OpenVoice claims any-language support with an appropriate base speaker; "
                        "this adapter uses facebook/mms-tts-swe as the Swedish base model."
                    ),
                )
            ],
        )

    def voices(self) -> VoicesResponse:
        """Return the bounded preset-voice listing for the OpenVoice adapter."""
        return VoicesResponse(voices=[])

    def synthesize(
        self,
        request: SynthesizeRequest,
        *,
        reference_audio: ReferenceAudio | None,
    ) -> SynthesizeResult:
        """Synthesize Swedish audio via MMS base generation plus OpenVoice cloning."""
        self._ensure_ready()
        if request.output_format is not OutputFormat.WAV:
            raise SidecarRequestError(
                code="unsupported_output_format",
                message="OpenVoice OpenVoice benchmark currently supports `wav` output only.",
                status_code=422,
            )
        if request.voice_mode is not VoiceMode.REFERENCE_CLONE:
            raise SidecarRequestError(
                code="unsupported_voice_mode",
                message="OpenVoice OpenVoice benchmark requires `reference_clone` voice mode.",
                status_code=422,
            )
        if request.preset_voice_id is not None:
            raise SidecarRequestError(
                code="preset_voice_not_supported",
                message="OpenVoice OpenVoice benchmark does not expose preset voices.",
                status_code=422,
            )
        normalized_language = _normalize_language_code(request.language)
        if normalized_language not in self._settings.supported_language_codes:
            raise SidecarRequestError(
                code="unsupported_language",
                message=(
                    "OpenVoice only supports the configured benchmark languages: "
                    f"{', '.join(self._settings.supported_language_codes)}."
                ),
                status_code=422,
            )
        if reference_audio is None or len(reference_audio.data) == 0:
            raise SidecarRequestError(
                code="missing_reference_audio",
                message="Reference audio is required for OpenVoice cloning.",
                status_code=422,
            )
        normalized_text = _normalize_text(request.text, profile=request.normalization_profile)
        if normalized_text == "":
            raise SidecarRequestError(
                code="empty_text",
                message="The synthesis request text is empty after normalization.",
                status_code=422,
            )

        converter = self._require_converter()
        manual_seed = self._require_manual_seed()
        inference_mode_factory = self._require_inference_mode_factory()
        tokenizer = self._require_tokenizer()
        base_model = self._require_base_model()

        with TemporaryDirectory(prefix="openvoice-sidecar-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            debug_artifact_dir = self._resolve_debug_artifact_dir()
            reference_path = temp_dir / f"reference{_normalized_suffix(reference_audio.filename)}"
            source_base_path = temp_dir / "source_base.wav"
            source_converter_path = temp_dir / "source_converter.wav"
            output_path = temp_dir / "output.wav"
            reference_path.write_bytes(reference_audio.data)
            target_se = self._extract_target_speaker_embedding(
                reference_path=reference_path,
                converter=converter,
                temp_dir=temp_dir,
                debug_artifact_dir=debug_artifact_dir,
            )
            self._synthesize_base_audio(
                text=normalized_text,
                tokenizer=tokenizer,
                base_model=base_model,
                manual_seed=manual_seed,
                inference_mode_factory=inference_mode_factory,
                output_path=source_base_path,
                sample_rate_hz=self._base_model_sample_rate_hz,
            )
            if debug_artifact_dir is not None:
                shutil.copy2(source_base_path, debug_artifact_dir / "base_sv.wav")
            if self._base_model_sample_rate_hz == self._converter_sample_rate_hz:
                source_path_for_converter = source_base_path
            else:
                _resample_audio_file(
                    source_path=source_base_path,
                    target_path=source_converter_path,
                    target_sample_rate_hz=self._converter_sample_rate_hz,
                )
                source_path_for_converter = source_converter_path
                if debug_artifact_dir is not None:
                    shutil.copy2(
                        source_converter_path,
                        debug_artifact_dir / "base_sv_converter_input.wav",
                    )
            source_se = converter.extract_se([source_path_for_converter.as_posix()])
            converter.convert(
                audio_src_path=source_path_for_converter.as_posix(),
                src_se=source_se,
                tgt_se=target_se,
                output_path=output_path.as_posix(),
                message="",
            )
            audio_bytes = output_path.read_bytes()

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
        if not self._ready:
            raise SidecarRequestError(
                code="backend_not_ready",
                message="The OpenVoice sidecar is not ready yet.",
                status_code=503,
            )

    def _require_converter(self) -> _OpenVoiceConverter:
        if self._converter is None:
            raise RuntimeError("OpenVoice converter was not initialized.")
        return self._converter

    def _require_base_model(self) -> _BaseModel:
        if self._base_model is None:
            raise RuntimeError("Base TTS model was not initialized.")
        return self._base_model

    def _require_tokenizer(self) -> _Tokenizer:
        if self._tokenizer is None:
            raise RuntimeError("Base TTS tokenizer was not initialized.")
        return self._tokenizer

    def _require_manual_seed(self) -> Callable[[int], object]:
        if self._manual_seed is None:
            raise RuntimeError("Torch manual_seed was not initialized.")
        return self._manual_seed

    def _require_inference_mode_factory(self) -> Callable[[], ContextManager[object]]:
        if self._inference_mode_factory is None:
            raise RuntimeError("Torch inference_mode was not initialized.")
        return self._inference_mode_factory

    def _resolve_debug_artifact_dir(self) -> Path | None:
        """Prepare one optional debug-artifact directory for benchmark reruns."""
        debug_artifact_dir = self._settings.debug_artifact_dir
        if debug_artifact_dir is None:
            return None
        if debug_artifact_dir.exists():
            for child in sorted(debug_artifact_dir.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child)
                    continue
                child.unlink()
        debug_artifact_dir.mkdir(parents=True, exist_ok=True)
        return debug_artifact_dir

    def _extract_target_speaker_embedding(
        self,
        *,
        reference_path: Path,
        converter: _OpenVoiceConverter,
        temp_dir: Path,
        debug_artifact_dir: Path | None,
    ) -> object:
        """Run the intended OpenVoice reference-speaker preprocessing path."""
        return extract_target_speaker_embedding(
            reference_path=reference_path,
            converter=converter,
            temp_dir=temp_dir,
            debug_artifact_dir=debug_artifact_dir,
        )

    def _synthesize_base_audio(
        self,
        *,
        text: str,
        tokenizer: _Tokenizer,
        base_model: _BaseModel,
        manual_seed: Callable[[int], object],
        inference_mode_factory: Callable[[], ContextManager[object]],
        output_path: Path,
        sample_rate_hz: int,
    ) -> None:
        import soundfile

        tokenized = tokenizer(text=text, return_tensors="pt")
        input_ids = tokenized["input_ids"]
        attention_mask = tokenized.get("attention_mask")
        manual_seed(7)
        with inference_mode_factory():
            model_device = next(base_model.parameters()).device
            waveform_tensor = base_model(
                input_ids=input_ids.to(model_device),
                attention_mask=attention_mask.to(model_device)
                if attention_mask is not None
                else None,
            ).waveform
        waveform = waveform_tensor.squeeze().detach().cpu().numpy()
        soundfile.write(output_path.as_posix(), waveform, sample_rate_hz)


def _normalize_language_code(language: str) -> str:
    """Map human-friendly or locale-style language values to canonical codes."""
    normalized = language.strip().lower()
    return _SUPPORTED_LANGUAGE_ALIASES.get(normalized, normalized)


def _normalize_text(text: str, *, profile: NormalizationProfile) -> str:
    """Apply one small deterministic text-normalization policy."""
    stripped = text.strip()
    if profile is NormalizationProfile.NONE:
        return stripped
    return re.sub(r"\s+", " ", stripped)
