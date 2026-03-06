"""OpenVoice V2 backend adapter for the normalized internal TTS sidecar contract.

Purpose:
    Wrap OpenVoice V2 voice conversion plus a Swedish MMS base synthesizer behind
    the reusable ADR-0007 sidecar contract so Hemma benchmarks can evaluate a
    cloning-capable backend without exposing backend-native APIs.

Relationships:
    - Uses the generic FastAPI surface built by `app_factory.py`.
    - Depends on OpenVoice V2 for tone-color conversion and `facebook/mms-tts-swe`
      as the Swedish base speaker generator for the Task 81 benchmark.
"""

from __future__ import annotations

import importlib.metadata
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, ContextManager, Iterator, Protocol

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

_SUPPORTED_LANGUAGE_ALIASES = {
    "sv": "sv",
    "sv-se": "sv",
    "swedish": "sv",
}


class _TensorLike(Protocol):
    """Minimal tensor surface used by the OpenVoice adapter."""

    def to(self, device: object) -> "_TensorLike":
        """Move one tensor to a device."""

    def squeeze(self) -> "_TensorLike":
        """Return one squeezed tensor."""

    def detach(self) -> "_TensorLike":
        """Detach one tensor from autograd."""

    def cpu(self) -> "_TensorLike":
        """Move one tensor to CPU."""

    def numpy(self) -> object:
        """Convert one tensor to a NumPy-compatible array."""


class _TokenizerBatch(Protocol):
    """Minimal tokenized-input container used by the OpenVoice adapter."""

    def __getitem__(self, key: str) -> _TensorLike:
        """Return one required tensor by key."""

    def get(self, key: str) -> _TensorLike | None:
        """Return one optional tensor by key."""


class _Tokenizer(Protocol):
    """Minimal tokenizer callable used by the OpenVoice adapter."""

    def __call__(self, *, text: str, return_tensors: str) -> _TokenizerBatch:
        """Tokenize one text input into tensors."""


class _ModelParameter(Protocol):
    """Minimal model-parameter surface used to discover a device."""

    @property
    def device(self) -> object:
        """Return the device that owns this parameter."""


class _WaveformOutput(Protocol):
    """Minimal model output surface used by the OpenVoice adapter."""

    waveform: _TensorLike


class _BaseModel(Protocol):
    """Minimal Swedish base-model surface used by the OpenVoice adapter."""

    def to(self, device: str) -> "_BaseModel":
        """Move the model to the requested device."""

    def eval(self) -> None:
        """Switch the model into evaluation mode."""

    def parameters(self) -> Iterator[_ModelParameter]:
        """Return one iterator over model parameters."""

    def __call__(
        self,
        *,
        input_ids: _TensorLike,
        attention_mask: _TensorLike | None = None,
    ) -> _WaveformOutput:
        """Run one forward pass and return waveform output."""


class _OpenVoiceDataConfig(Protocol):
    """Minimal OpenVoice hparams data surface used by the adapter."""

    sampling_rate: int


class _OpenVoiceHParams(Protocol):
    """Minimal OpenVoice hparams surface used by the adapter."""

    data: _OpenVoiceDataConfig


class _OpenVoiceConverter(Protocol):
    """Minimal OpenVoice converter surface used by the adapter."""

    hps: _OpenVoiceHParams

    def load_ckpt(self, ckpt_path: str) -> None:
        """Load one converter checkpoint from disk."""

    def extract_se(self, ref_wav_list: list[str], se_save_path: str | None = None) -> object:
        """Extract one speaker embedding from reference audio."""

    def convert(
        self,
        audio_src_path: str,
        src_se: object,
        tgt_se: object,
        output_path: str | None = None,
        tau: float = 0.3,
        message: str = "default",
    ) -> object:
        """Convert one source audio file into the target tone color."""


@dataclass(frozen=True)
class OpenVoiceSidecarSettings:
    """Environment-driven settings for the OpenVoice Task 81 sidecar."""

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
    base_model_id: str
    supported_language_codes: tuple[str, ...]
    enable_watermark: bool
    watermark_message: str
    network_scope: NetworkScope

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
            base_model_id=os.environ.get("SIR_TTS_SIDECAR_BASE_MODEL_ID", "facebook/mms-tts-swe"),
            supported_language_codes=supported_codes,
            enable_watermark=_parse_bool_env(
                "SIR_TTS_SIDECAR_OPENVOICE_ENABLE_WATERMARK", default=False
            ),
            watermark_message=os.environ.get("SIR_TTS_SIDECAR_OPENVOICE_WATERMARK_MESSAGE", ""),
            network_scope=NetworkScope.INTERNAL_ONLY,
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
        self._package_versions: dict[str, str | None] = {}

    def startup(self) -> None:
        """Load OpenVoice and the Swedish MMS base model onto the configured GPU."""
        import torch
        from openvoice.api import ToneColorConverter
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

        converter: _OpenVoiceConverter = ToneColorConverter(
            config_path.as_posix(),
            device=device,
            enable_watermark=self._settings.enable_watermark,
        )
        converter.load_ckpt(checkpoint_path.as_posix())
        tokenizer: _Tokenizer = AutoTokenizer.from_pretrained(self._settings.base_model_id)
        base_model: _BaseModel = VitsModel.from_pretrained(self._settings.base_model_id).to(device)
        base_model.eval()

        sample_rate_hz = _positive_int(
            converter.hps.data.sampling_rate, label="OpenVoice converter sampling rate"
        )
        self._converter = converter
        self._tokenizer = tokenizer
        self._base_model = base_model
        self._manual_seed = torch.manual_seed
        self._inference_mode_factory = torch.inference_mode
        self._sample_rate_hz = sample_rate_hz
        self._supports_rocm = getattr(torch.version, "hip", None) is not None
        self._package_versions = {
            "openvoice": _package_version_or_none("openvoice"),
            "transformers": _package_version_or_none("transformers"),
            "torch": _package_version_or_none("torch"),
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
                )
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
                        "this Task 81 adapter uses facebook/mms-tts-swe as the Swedish base model."
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
                message="OpenVoice Task 81 currently supports `wav` output only.",
                status_code=422,
            )
        if request.voice_mode is not VoiceMode.REFERENCE_CLONE:
            raise SidecarRequestError(
                code="unsupported_voice_mode",
                message="OpenVoice Task 81 requires `reference_clone` voice mode.",
                status_code=422,
            )
        if request.preset_voice_id is not None:
            raise SidecarRequestError(
                code="preset_voice_not_supported",
                message="OpenVoice Task 81 does not expose preset voices.",
                status_code=422,
            )
        normalized_language = _normalize_language_code(request.language)
        if normalized_language not in self._settings.supported_language_codes:
            raise SidecarRequestError(
                code="unsupported_language",
                message=(
                    "OpenVoice Task 81 only supports the configured benchmark languages: "
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
            reference_path = temp_dir / f"reference{_normalized_suffix(reference_audio.filename)}"
            source_path = temp_dir / "source.wav"
            output_path = temp_dir / "output.wav"
            reference_path.write_bytes(reference_audio.data)
            self._synthesize_base_audio(
                text=normalized_text,
                tokenizer=tokenizer,
                base_model=base_model,
                manual_seed=manual_seed,
                inference_mode_factory=inference_mode_factory,
                output_path=source_path,
            )
            source_se = converter.extract_se([source_path.as_posix()])
            target_se = converter.extract_se([reference_path.as_posix()])
            converter.convert(
                audio_src_path=source_path.as_posix(),
                src_se=source_se,
                tgt_se=target_se,
                output_path=output_path.as_posix(),
                message=self._settings.watermark_message,
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

    def _synthesize_base_audio(
        self,
        *,
        text: str,
        tokenizer: _Tokenizer,
        base_model: _BaseModel,
        manual_seed: Callable[[int], object],
        inference_mode_factory: Callable[[], ContextManager[object]],
        output_path: Path,
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
        soundfile.write(output_path.as_posix(), waveform, self._sample_rate_hz)


def _package_version_or_none(name: str) -> str | None:
    """Return one installed package version when available."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _parse_bool_env(name: str, *, default: bool) -> bool:
    """Parse one boolean environment variable with a deterministic default."""
    value = os.environ.get(name)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean-like value.")


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


def _normalized_suffix(filename: str) -> str:
    """Return one safe suffix for a temporary reference-audio file."""
    suffix = Path(filename).suffix.strip()
    if suffix == "":
        return ".wav"
    if len(suffix) > 10:
        return ".wav"
    return suffix


def _positive_int(value: object, *, label: str) -> int:
    """Convert one runtime value to a strictly positive integer."""
    if not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"{label} must be a positive integer, got {value!r}.")
    return value
