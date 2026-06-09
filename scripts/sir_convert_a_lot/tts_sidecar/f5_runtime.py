"""F5-TTS backend adapter for the normalized internal TTS sidecar contract.

Purpose:
    Wrap the ChiliOlavi `swedish-tts` F5-TTS CLI inference plus the Swedish
    F5-TTS benchmark fine-tune behind the reusable ADR-0007 sidecar contract so Hemma
    can validate a minimal cloning-capable Swedish backend through the
    service-container path.

Relationships:
    - Uses the generic FastAPI surface built by `app_factory.py`.
    - Depends on the `ChiliOlavi/F5-TTS@swedish-tts` `f5-tts_infer-cli`
      command plus the `EkhoCollective/f5-tts-swedish` model assets mounted
      into the sidecar.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from huggingface_hub import snapshot_download

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
_DEFAULT_REFERENCE_MAX_SECONDS = 12.0


@dataclass(frozen=True)
class F5TtsSidecarSettings:
    """Environment-driven settings for the F5-TTS F5-TTS benchmark sidecar."""

    backend_id: str
    backend_version: str
    backend_profile: str
    gpu_required: bool
    model_name: str
    model_repo_id: str
    model_root: Path
    model_cfg_path: str | None
    hf_cache_host_root: str
    hf_cache_container_root: str
    model_cache_host_root: str
    model_cache_container_root: str
    supported_language_codes: tuple[str, ...]
    network_scope: NetworkScope
    remove_silence: bool
    nfe_step: int
    cfg_strength: float
    sway_sampling_coef: float
    speed: float
    fix_duration: float | None
    cross_fade_duration: float
    target_rms: float
    vocoder_name: str
    load_vocoder_from_local: bool
    reference_max_seconds: float

    @classmethod
    def from_env(cls) -> "F5TtsSidecarSettings":
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
            backend_id=os.environ.get("SIR_TTS_SIDECAR_BACKEND_ID", "f5_tts_swedish"),
            backend_version=os.environ.get("SIR_TTS_SIDECAR_BACKEND_VERSION", "swedish-tts"),
            backend_profile=os.environ.get(
                "SIR_TTS_SIDECAR_BACKEND_PROFILE",
                "f5tts_v1_base_swedish_finetune",
            ),
            gpu_required=_parse_bool_env("SIR_TTS_SIDECAR_GPU_REQUIRED", default=True),
            model_name=os.environ.get("SIR_TTS_SIDECAR_MODEL_NAME", "F5TTS_v1_Base"),
            model_repo_id=os.environ.get(
                "SIR_TTS_SIDECAR_MODEL_REPO_ID",
                "EkhoCollective/f5-tts-swedish",
            ),
            model_root=Path(
                os.environ.get(
                    "SIR_TTS_SIDECAR_MODEL_ROOT",
                    "/cache/f5-tts/swedish",
                )
            ),
            model_cfg_path=_optional_str_env("SIR_TTS_SIDECAR_MODEL_CFG_PATH"),
            hf_cache_host_root=os.environ.get(
                "SIR_TTS_SIDECAR_HF_CACHE_HOST_ROOT",
                "/srv/scratch/sir-convert-a-lot/cache/huggingface",
            ),
            hf_cache_container_root=os.environ.get(
                "SIR_TTS_SIDECAR_HF_CACHE_CONTAINER_ROOT",
                "/cache/huggingface",
            ),
            model_cache_host_root=os.environ.get(
                "SIR_TTS_SIDECAR_MODEL_CACHE_HOST_ROOT",
                "/srv/scratch/sir-convert-a-lot/cache/f5-tts-swedish",
            ),
            model_cache_container_root=os.environ.get(
                "SIR_TTS_SIDECAR_MODEL_CACHE_CONTAINER_ROOT",
                "/cache/f5-tts",
            ),
            supported_language_codes=supported_codes,
            network_scope=NetworkScope.INTERNAL_ONLY,
            remove_silence=_parse_bool_env("SIR_TTS_SIDECAR_F5_REMOVE_SILENCE", default=True),
            nfe_step=_parse_int_env("SIR_TTS_SIDECAR_F5_NFE_STEP", default=64, minimum=1),
            cfg_strength=_parse_float_env(
                "SIR_TTS_SIDECAR_F5_CFG_STRENGTH",
                default=2.0,
            ),
            sway_sampling_coef=_parse_float_env(
                "SIR_TTS_SIDECAR_F5_SWAY_SAMPLING_COEF",
                default=-1.0,
            ),
            speed=_parse_float_env("SIR_TTS_SIDECAR_F5_SPEED", default=1.0),
            fix_duration=_optional_float_env("SIR_TTS_SIDECAR_F5_FIX_DURATION"),
            cross_fade_duration=_parse_float_env(
                "SIR_TTS_SIDECAR_F5_CROSS_FADE_DURATION",
                default=0.15,
            ),
            target_rms=_parse_float_env("SIR_TTS_SIDECAR_F5_TARGET_RMS", default=0.1),
            vocoder_name=os.environ.get("SIR_TTS_SIDECAR_F5_VOCODER_NAME", "vocos").strip(),
            load_vocoder_from_local=_parse_bool_env(
                "SIR_TTS_SIDECAR_F5_LOAD_VOCODER_FROM_LOCAL",
                default=False,
            ),
            reference_max_seconds=_parse_float_env(
                "SIR_TTS_SIDECAR_F5_REFERENCE_MAX_SECONDS",
                default=_DEFAULT_REFERENCE_MAX_SECONDS,
            ),
        )


class F5TtsSidecarBackend:
    """F5-TTS-backed implementation of the normalized TTS sidecar contract."""

    def __init__(self, settings: F5TtsSidecarSettings) -> None:
        self._settings = settings
        self._ready = False
        self._python_version = sys.version.split()[0]
        self._supports_rocm = False
        self._cli_path: str | None = None
        self._package_versions: dict[str, str | None] = {}
        self._sample_rate_hz = 24000

    def startup(self) -> None:
        """Validate runtime truth and ensure the Swedish model root is ready."""
        from importlib import metadata

        import torch

        if self._settings.gpu_required and not torch.cuda.is_available():
            raise RuntimeError("F5-TTS sidecar requires GPU access, but torch.cuda is unavailable.")
        cli_path = shutil.which("f5-tts_infer-cli")
        if cli_path is None:
            raise RuntimeError("`f5-tts_infer-cli` is not available in the F5 sidecar image.")
        self._cli_path = cli_path
        self._supports_rocm = getattr(torch.version, "hip", None) is not None
        self._ensure_model_snapshot_present()
        self._sample_rate_hz = _read_target_sample_rate_hz(self._settings.model_name)
        self._package_versions = {
            "f5-tts": _package_version_or_none(metadata, "f5-tts"),
            "transformers": _package_version_or_none(metadata, "transformers"),
            "huggingface-hub": _package_version_or_none(metadata, "huggingface-hub"),
            "torch": _package_version_or_none(metadata, "torch"),
            "torchaudio": _package_version_or_none(metadata, "torchaudio"),
        }
        self._ready = True

    def health(self) -> HealthResponse:
        """Return readiness state for the F5-TTS sidecar."""
        return HealthResponse(
            status=SidecarStatus.OK if self._ready else SidecarStatus.DEGRADED,
            backend_id=self._settings.backend_id,
            backend_version=self._settings.backend_version,
            backend_profile=self._settings.backend_profile,
            ready=self._ready,
        )

    def capabilities(self) -> CapabilityResponse:
        """Return the ADR-0007 capability document for the F5-TTS adapter."""
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
            auxiliary_caches=[
                CacheCapability(
                    cache_family="f5_model_assets",
                    host_root=self._settings.model_cache_host_root,
                    container_root=self._settings.model_cache_container_root,
                    reuse_strategy="persistent_host_cache",
                )
            ],
            synthesis=SynthesisCapability(
                output_formats=[OutputFormat.WAV],
                sample_rates_hz=[self._sample_rate_hz],
                supports_streaming=False,
            ),
            voice=VoiceCapability(
                modes=[VoiceMode.REFERENCE_CLONE],
                reference_transcript_required=True,
                reference_audio_required=True,
            ),
            languages=[
                LanguageCapability(
                    code="sv",
                    support_level=LanguageSupportLevel.EXPERIMENTAL,
                    notes=(
                        "Uses the community Swedish fine-tune "
                        "`EkhoCollective/f5-tts-swedish` on top of `F5TTS_v1_Base`."
                    ),
                )
            ],
        )

    def voices(self) -> VoicesResponse:
        """Return the bounded preset-voice listing for the F5-TTS adapter."""
        return VoicesResponse(voices=[])

    def synthesize(
        self,
        request: SynthesizeRequest,
        *,
        reference_audio: ReferenceAudio | None,
    ) -> SynthesizeResult:
        """Synthesize Swedish audio via the installed F5-TTS CLI."""
        self._ensure_ready()
        if request.output_format is not OutputFormat.WAV:
            raise SidecarRequestError(
                code="unsupported_output_format",
                message="F5-TTS F5-TTS benchmark currently supports `wav` output only.",
                status_code=422,
            )
        if request.voice_mode is not VoiceMode.REFERENCE_CLONE:
            raise SidecarRequestError(
                code="unsupported_voice_mode",
                message="F5-TTS F5-TTS benchmark requires `reference_clone` voice mode.",
                status_code=422,
            )
        if request.preset_voice_id is not None:
            raise SidecarRequestError(
                code="preset_voice_not_supported",
                message="F5-TTS F5-TTS benchmark does not expose preset voices.",
                status_code=422,
            )
        normalized_language = _normalize_language_code(request.language)
        if normalized_language not in self._settings.supported_language_codes:
            raise SidecarRequestError(
                code="unsupported_language",
                message=(
                    "F5-TTS F5-TTS benchmark only supports the configured benchmark languages: "
                    f"{', '.join(self._settings.supported_language_codes)}."
                ),
                status_code=422,
            )
        if reference_audio is None or len(reference_audio.data) == 0:
            raise SidecarRequestError(
                code="missing_reference_audio",
                message="Reference audio is required for F5-TTS cloning.",
                status_code=422,
            )
        if request.reference_transcript is None or request.reference_transcript.strip() == "":
            raise SidecarRequestError(
                code="missing_reference_transcript",
                message="Reference transcript is required for F5-TTS F5-TTS benchmark.",
                status_code=422,
            )
        normalized_text = _normalize_text(request.text, profile=request.normalization_profile)
        if normalized_text == "":
            raise SidecarRequestError(
                code="empty_text",
                message="The synthesis request text is empty after normalization.",
                status_code=422,
            )

        model_files = _resolve_model_files(self._settings.model_root)
        if model_files is None:
            raise RuntimeError("F5-TTS model files were not resolved during synthesis.")
        cli_path = self._require_cli_path()
        with TemporaryDirectory(prefix="f5-sidecar-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            source_reference_path = (
                temp_dir / f"reference{_normalized_suffix(reference_audio.filename)}"
            )
            prepared_reference_path = temp_dir / "reference_sv_24k.wav"
            output_dir = temp_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = "synthesized.wav"
            config_path = temp_dir / "f5_f5-tts.toml"
            gen_file_path = temp_dir / "gen_text.txt"
            source_reference_path.write_bytes(reference_audio.data)
            _prepare_reference_audio(
                source_path=source_reference_path,
                target_path=prepared_reference_path,
                max_seconds=self._settings.reference_max_seconds,
            )
            gen_file_path.write_text(normalized_text + "\n", encoding="utf-8")
            config_path.write_text(
                _render_infer_toml(
                    model_name=self._settings.model_name,
                    ckpt_file=model_files.checkpoint_path,
                    vocab_file=model_files.vocab_path,
                    ref_audio=prepared_reference_path,
                    ref_text=request.reference_transcript.strip(),
                    gen_text=None,
                    gen_file=gen_file_path,
                    output_dir=output_dir,
                    output_file=output_file,
                    model_cfg_path=self._settings.model_cfg_path,
                    remove_silence=self._settings.remove_silence,
                    nfe_step=self._settings.nfe_step,
                    cfg_strength=self._settings.cfg_strength,
                    sway_sampling_coef=self._settings.sway_sampling_coef,
                    speed=self._settings.speed,
                    fix_duration=self._settings.fix_duration,
                    cross_fade_duration=self._settings.cross_fade_duration,
                    target_rms=self._settings.target_rms,
                    vocoder_name=self._settings.vocoder_name,
                    load_vocoder_from_local=self._settings.load_vocoder_from_local,
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [cli_path, "-c", config_path.as_posix()],
                check=False,
                capture_output=True,
                text=True,
                env=_infer_env(self._settings),
                timeout=900,
            )
            if result.returncode != 0:
                raise SidecarRequestError(
                    code="f5_infer_failed",
                    message=(
                        "F5-TTS inference failed.\n"
                        f"stdout:\n{result.stdout.strip()}\n"
                        f"stderr:\n{result.stderr.strip()}"
                    ).strip(),
                    status_code=500,
                )
            output_path = output_dir / output_file
            if not output_path.exists():
                raise SidecarRequestError(
                    code="missing_output_audio",
                    message="F5-TTS completed without producing the expected WAV output.",
                    status_code=500,
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
                message="The F5-TTS sidecar is not ready yet.",
                status_code=503,
            )

    def _require_cli_path(self) -> str:
        if self._cli_path is None:
            raise RuntimeError("F5-TTS CLI path was not initialized.")
        return self._cli_path

    def _ensure_model_snapshot_present(self) -> None:
        model_files = _resolve_model_files(self._settings.model_root, required=False)
        if model_files is not None:
            return
        self._settings.model_root.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=self._settings.model_repo_id,
            local_dir=self._settings.model_root.as_posix(),
            local_dir_use_symlinks=False,
        )
        if _resolve_model_files(self._settings.model_root, required=False) is None:
            raise RuntimeError(
                "F5-TTS Swedish model snapshot did not materialize checkpoint and vocab files."
            )


@dataclass(frozen=True)
class _ModelFiles:
    """Resolved Swedish model artifact paths for F5-TTS benchmark."""

    checkpoint_path: Path
    vocab_path: Path


def _resolve_model_files(model_root: Path, *, required: bool = True) -> _ModelFiles | None:
    """Return the F5-TTS benchmark checkpoint and vocab paths under the mounted model root."""
    vocab_path = model_root / "vocab.txt"
    checkpoint_candidates = sorted(model_root.glob("*.safetensors")) + sorted(
        model_root.glob("*.pt")
    )
    if checkpoint_candidates and vocab_path.exists():
        return _ModelFiles(checkpoint_path=checkpoint_candidates[0], vocab_path=vocab_path)
    if required:
        raise RuntimeError(
            "Expected F5-TTS Swedish model assets under "
            f"{model_root.as_posix()} with one checkpoint and `vocab.txt`."
        )
    return None


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
    """Return a safe suffix that preserves the file extension when present."""
    suffix = Path(filename).suffix.lower()
    return suffix if suffix != "" else ".bin"


def _prepare_reference_audio(*, source_path: Path, target_path: Path, max_seconds: float) -> None:
    """Convert one uploaded reference clip into the F5-TTS benchmark WAV format."""
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
            "-t",
            str(max_seconds),
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
                "Failed to convert reference audio for F5-TTS.\n"
                f"stdout:\n{result.stdout.strip()}\n"
                f"stderr:\n{result.stderr.strip()}"
            ).strip(),
            status_code=422,
        )


def _render_infer_toml(
    *,
    model_name: str,
    ckpt_file: Path,
    vocab_file: Path,
    ref_audio: Path,
    ref_text: str,
    gen_text: str | None,
    gen_file: Path | None,
    output_dir: Path,
    output_file: str,
    model_cfg_path: str | None,
    remove_silence: bool,
    nfe_step: int,
    cfg_strength: float,
    sway_sampling_coef: float,
    speed: float,
    fix_duration: float | None,
    cross_fade_duration: float,
    target_rms: float,
    vocoder_name: str,
    load_vocoder_from_local: bool,
) -> str:
    """Render one small TOML config file for `f5-tts_infer-cli`."""
    lines = [
        f'model = "{_escape_toml(model_name)}"',
        f'ckpt_file = "{_escape_toml(ckpt_file.as_posix())}"',
        f'vocab_file = "{_escape_toml(vocab_file.as_posix())}"',
        f'ref_audio = "{_escape_toml(ref_audio.as_posix())}"',
        f'ref_text = "{_escape_toml(ref_text)}"',
        f'gen_text = "{_escape_toml(gen_text or "")}"',
        f'output_dir = "{_escape_toml(output_dir.as_posix())}"',
        f'output_file = "{_escape_toml(output_file)}"',
        f"remove_silence = {'true' if remove_silence else 'false'}",
        f"nfe_step = {nfe_step}",
        f"cfg_strength = {cfg_strength}",
        f"sway_sampling_coef = {sway_sampling_coef}",
        f"speed = {speed}",
        f"cross_fade_duration = {cross_fade_duration}",
        f"target_rms = {target_rms}",
        f'vocoder_name = "{_escape_toml(vocoder_name)}"',
        f"load_vocoder_from_local = {'true' if load_vocoder_from_local else 'false'}",
    ]
    if gen_file is not None:
        lines.append(f'gen_file = "{_escape_toml(gen_file.as_posix())}"')
    if fix_duration is not None:
        lines.append(f"fix_duration = {fix_duration}")
    if model_cfg_path is not None:
        lines.append(f'model_cfg = "{_escape_toml(model_cfg_path)}"')
    return "\n".join(lines) + "\n"


def _escape_toml(value: str) -> str:
    """Escape one string value for a small generated TOML file."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _infer_env(settings: F5TtsSidecarSettings) -> dict[str, str]:
    """Build the environment used for F5-TTS CLI inference."""
    env = dict(os.environ)
    env["HF_HUB_DISABLE_XET"] = "1"
    env.setdefault("HF_HOME", settings.hf_cache_container_root)
    env.setdefault("HUGGINGFACE_HUB_CACHE", settings.hf_cache_container_root)
    env.setdefault("TRANSFORMERS_CACHE", settings.hf_cache_container_root)
    return env


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


def _parse_int_env(name: str, *, default: int, minimum: int) -> int:
    """Return one integer environment variable with validation and fallback."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer-like value, got `{value}`.") from exc
    if parsed < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}, got `{parsed}`.")
    return parsed


def _parse_float_env(name: str, *, default: float) -> float:
    """Return one float environment variable with validation and fallback."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a float-like value, got `{value}`.") from exc


def _optional_str_env(name: str) -> str | None:
    """Return one optional non-empty string environment variable."""
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped != "" else None


def _optional_float_env(name: str) -> float | None:
    """Return one optional float environment variable."""
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    try:
        return float(stripped)
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


def _read_target_sample_rate_hz(model_name: str) -> int:
    """Read the target sample rate from the upstream bundled F5 config."""
    import importlib.resources

    config_path = importlib.resources.files("f5_tts").joinpath(f"configs/{model_name}.yaml")
    config_bytes = config_path.read_bytes()
    payload = tomllib.loads(_yaml_to_toml_like_string(config_bytes.decode("utf-8")))
    mel_spec = payload.get("model", {}).get("mel_spec", {})
    sample_rate = mel_spec.get("target_sample_rate")
    if isinstance(sample_rate, int) and sample_rate > 0:
        return sample_rate
    return 24000


def _yaml_to_toml_like_string(config_text: str) -> str:
    """Translate the one needed YAML scalar into a TOML-like string for parsing.

    The bundled F5 config is stable and we only need the nested
    `model.mel_spec.target_sample_rate` integer. Avoid adding a repo-wide YAML
    dependency just for this lookup in the sidecar.
    """
    sample_rate_match = re.search(r"target_sample_rate:\s*([0-9]+)", config_text)
    sample_rate = sample_rate_match.group(1) if sample_rate_match else "24000"
    return f"[model.mel_spec]\ntarget_sample_rate = {sample_rate}\n"
