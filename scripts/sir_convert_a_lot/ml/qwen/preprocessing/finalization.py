"""Finalization and report helpers for the staged Qwen preprocessing pipeline.

Purpose:
    Consume durable spool rows to emit curated manifests, raw/prepared Qwen
    manifests, chunked `audio_codes`, and deterministic report artifacts.

Relationships:
    - Called by the preprocessing pipeline facade during the `all` and
      `finalization` stages.
    - Reads durable spool output produced by the row-processing stage.
    - Reuses contracts from `ml.qwen.common.models` and
      `ml.qwen.preprocessing.models`.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import shutil
import time
from collections import Counter
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Protocol, Sequence, TypeAlias, TypeGuard

import numpy as np
import numpy.typing as npt

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    CANONICAL_MANIFEST_FAMILIES,
    FinalizationHeartbeat,
    ManifestFamily,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    CuratedRow,
    FinalizationHeartbeatCallback,
    PreparedManifestRow,
    PreprocessingReport,
    PreprocessingSettings,
    RawManifestRow,
    SpoolRow,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    JsonlAtomicWriter,
    iter_jsonl_objects,
    iter_spool_rows,
    write_json,
)

# --- Governed Runtime Defaults ---
DEFAULT_GOVERNED_DEVICE_MAP = "cuda:0"
DEFAULT_GOVERNED_DTYPE = "bfloat16"
DEFAULT_GOVERNED_ATTN_IMPLEMENTATION = "flash_attention_2"


class AudioCodesEncoderProtocol(Protocol):
    """Minimal callable surface for chunked `audio_codes` generation."""

    def __call__(
        self,
        *,
        tokenizer_model: str,
        audio_paths: list[Path],
    ) -> list[list[list[int]]]:
        """Encode one bounded chunk of audio paths into Qwen audio codes."""


WaveformArray: TypeAlias = npt.NDArray[np.float32]


class _AudioCodesTensorProtocol(Protocol):
    """Audio-code tensor-like object that can render to nested integer lists."""

    def tolist(self) -> list[list[int]]:
        """Render the audio-code tensor into nested integer lists."""


class _EncodedAudioCodesProtocol(Protocol):
    """Minimal encode result surface returned by the Qwen tokenizer."""

    @property
    def audio_codes(self) -> Sequence[_AudioCodesTensorProtocol]:
        """Return the encoded audio-code tensors."""


class _QwenTokenizerProtocol(Protocol):
    """Minimal Qwen tokenizer surface used by finalization."""

    @property
    def feature_extractor(self) -> "_FeatureExtractorProtocol":
        """Return the feature extractor used to determine tokenizer sample rate."""

    def encode(
        self,
        audio_paths: list[WaveformArray],
        *,
        sr: int,
    ) -> _EncodedAudioCodesProtocol:
        """Encode one audio-path batch into Qwen audio codes."""


class _InputTensorProtocol(Protocol):
    """Minimal tensor-like input surface for Qwen feature batches."""

    def squeeze(self, dim: int) -> object:
        """Return the squeezed input tensor passed into `model.encode(...)`."""


class _FeatureBatchProtocol(Protocol):
    """Minimal feature-batch surface returned by the tokenizer extractor."""

    def to(self, destination: object) -> "_FeatureBatchProtocol":
        """Move or cast the batch to one destination and return the same batch."""

    def __getitem__(self, key: str) -> _InputTensorProtocol:
        """Return one tensor-like batch field by key."""


class _FeatureExtractorProtocol(Protocol):
    """Minimal feature-extractor surface used for tokenizer sample-rate access."""

    @property
    def sampling_rate(self) -> int | float:
        """Return the sample rate expected by the tokenizer feature extractor."""

    def __call__(
        self,
        *,
        raw_audio: list[WaveformArray],
        sampling_rate: int,
        return_tensors: str,
    ) -> _FeatureBatchProtocol:
        """Convert one waveform batch into model-ready tensors."""


class _TensorParameterProtocol(Protocol):
    """Minimal tensor-parameter surface used for runtime introspection."""

    @property
    def device(self) -> object:
        """Return the current device placement for one model parameter."""

    @property
    def dtype(self) -> object:
        """Return the current dtype for one model parameter."""


class _QwenModelConfigProtocol(Protocol):
    """Minimal model-config surface used for attention introspection."""

    @property
    def _attn_implementation(self) -> str | None:
        """Return the configured attention implementation when exposed."""


class _QwenTokenizerModelProtocol(Protocol):
    """Minimal tokenizer-model surface used for device-aware runtime setup."""

    config: _QwenModelConfigProtocol

    def parameters(self) -> Iterable[_TensorParameterProtocol]:
        """Return the model parameters for runtime introspection."""

    def to(
        self,
        device: object | None = None,
        *,
        dtype: object | None = None,
    ) -> _QwenTokenizerModelProtocol:
        """Move the tokenizer model to one device/dtype combination."""


class _DirectEncodeQwenTokenizerModelProtocol(_QwenTokenizerModelProtocol, Protocol):
    """Tokenizer-model surface needed for direct preloaded waveform encoding."""

    @property
    def dtype(self) -> object:
        """Return the current model dtype."""

    def encode(
        self,
        input_values: object,
        padding_mask: object,
        *,
        return_dict: bool,
    ) -> _EncodedAudioCodesProtocol:
        """Encode one feature-extracted waveform batch."""


class _ConfiguredQwenTokenizerProtocol(_QwenTokenizerProtocol, Protocol):
    """Minimal tokenizer surface that exposes model/device fields."""

    model: _QwenTokenizerModelProtocol
    device: object


class _DirectEncodeConfiguredQwenTokenizerProtocol(_ConfiguredQwenTokenizerProtocol, Protocol):
    """Configured tokenizer surface needed for direct waveform encode calls."""

    model: _DirectEncodeQwenTokenizerModelProtocol
    feature_extractor: _FeatureExtractorProtocol


@dataclass(frozen=True)
class AudioCodesRuntimeRequest:
    """Governed runtime settings for one warm audio-code tokenizer instance."""

    runtime_kind: str
    device: str
    dtype: str
    attn_implementation: str
    require_gpu: bool
    require_flash_attn: bool


@dataclass(frozen=True)
class AudioCodesRuntimeReport:
    """Observed runtime posture for one warm audio-code tokenizer instance."""

    runtime_kind: str
    tokenizer_model: str
    requested_device: str
    observed_device: str
    requested_dtype: str
    observed_dtype: str
    requested_attn_implementation: str
    observed_attn_implementation: str | None
    require_gpu: bool
    require_flash_attn: bool
    torch_cuda_available: bool
    torch_hip_version: str | None
    flash_attn_importable: bool
    flash_attn_version: str | None


@dataclass(frozen=True)
class AudioCodesChunkTiming:
    """Per-chunk timing evidence for governed audio-code generation."""

    row_count: int
    preload_seconds: float
    feature_extract_seconds: float | None
    model_encode_seconds: float | None
    encode_call_seconds: float
    render_seconds: float
    total_seconds: float


DEFAULT_GOVERNED_GPU_AUDIO_CODES_RUNTIME = AudioCodesRuntimeRequest(
    runtime_kind="preprocessing_qwen_audio_codes_gpu_v1",
    device=DEFAULT_GOVERNED_DEVICE_MAP,
    dtype=DEFAULT_GOVERNED_DTYPE,
    attn_implementation=DEFAULT_GOVERNED_ATTN_IMPLEMENTATION,
    require_gpu=True,
    require_flash_attn=True,
)
DEFAULT_CPU_AUDIO_CODES_RUNTIME = AudioCodesRuntimeRequest(
    runtime_kind="preprocessing_qwen_audio_codes_cpu_default_v1",
    device="cpu",
    dtype="float32",
    attn_implementation="eager",
    require_gpu=False,
    require_flash_attn=False,
)


def _package_version(package_name: str) -> str | None:
    """Return one installed package version when available."""
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _runtime_request_dtype(runtime_request: AudioCodesRuntimeRequest) -> object:
    """Resolve the requested torch dtype for the governed tokenizer runtime."""
    import torch

    if runtime_request.dtype == "bfloat16":
        return torch.bfloat16
    if runtime_request.dtype == "float16":
        return torch.float16
    if runtime_request.dtype == "float32":
        return torch.float32
    raise ValueError(f"Unsupported audio-codes runtime dtype `{runtime_request.dtype}`.")


def _first_model_parameter(
    model: _QwenTokenizerModelProtocol,
) -> _TensorParameterProtocol:
    """Return the first model parameter for device/dtype introspection."""
    try:
        return next(iter(model.parameters()))
    except StopIteration as exc:
        raise RuntimeError(
            "Qwen tokenizer model exposed no parameters for runtime introspection."
        ) from exc


class WarmAudioCodesEncoder:
    """Reuse one Qwen tokenizer instance for all chunks in one finalization process."""

    def __init__(self, runtime_request: AudioCodesRuntimeRequest) -> None:
        self._runtime_request = runtime_request
        self._tokenizer_model: str | None = None
        self._tokenizer: _ConfiguredQwenTokenizerProtocol | None = None
        self._runtime_report: AudioCodesRuntimeReport | None = None
        self._last_chunk_timing: AudioCodesChunkTiming | None = None

    def __call__(
        self,
        *,
        tokenizer_model: str,
        audio_paths: list[Path],
    ) -> list[list[list[int]]]:
        """Generate Qwen `audio_codes` for one bounded audio-path chunk."""
        started_at = time.perf_counter()
        tokenizer = self._ensure_tokenizer(tokenizer_model)
        target_sample_rate = int(tokenizer.feature_extractor.sampling_rate)
        preload_started_at = time.perf_counter()
        waveforms = _load_audio_arrays_for_tokenizer(
            audio_paths=audio_paths,
            target_sample_rate=target_sample_rate,
        )
        preload_seconds = time.perf_counter() - preload_started_at
        rendered_codes: list[list[list[int]]] = []
        feature_extract_seconds: float | None = None
        model_encode_seconds: float | None = None
        encode_started_at = time.perf_counter()
        if _supports_direct_preloaded_waveform_encode(tokenizer):
            encoded, feature_extract_seconds, model_encode_seconds = (
                _encode_preloaded_waveforms_directly(
                    tokenizer,
                    waveforms,
                    target_sample_rate=target_sample_rate,
                )
            )
        else:
            encoded = tokenizer.encode(waveforms, sr=target_sample_rate)
        encode_call_seconds = time.perf_counter() - encode_started_at
        render_started_at = time.perf_counter()
        for audio_codes in encoded.audio_codes:
            rendered_codes.append(audio_codes.tolist())
        render_seconds = time.perf_counter() - render_started_at
        self._last_chunk_timing = AudioCodesChunkTiming(
            row_count=len(audio_paths),
            preload_seconds=preload_seconds,
            feature_extract_seconds=feature_extract_seconds,
            model_encode_seconds=model_encode_seconds,
            encode_call_seconds=encode_call_seconds,
            render_seconds=render_seconds,
            total_seconds=time.perf_counter() - started_at,
        )
        return rendered_codes

    def describe(self, tokenizer_model: str) -> AudioCodesRuntimeReport:
        """Return the observed runtime posture for the requested tokenizer model."""
        self._ensure_tokenizer(tokenizer_model)
        if self._runtime_report is None:
            raise RuntimeError("Audio-codes runtime report was not initialized.")
        return self._runtime_report

    def take_last_chunk_timing(self) -> AudioCodesChunkTiming | None:
        """Return and clear the latest per-chunk timing payload."""
        timing = self._last_chunk_timing
        self._last_chunk_timing = None
        return timing

    def reset(self) -> None:
        """Drop the cached tokenizer so the next call reinitializes cleanly."""
        self._tokenizer_model = None
        self._tokenizer = None
        self._runtime_report = None
        self._last_chunk_timing = None

    def _ensure_tokenizer(self, tokenizer_model: str) -> _ConfiguredQwenTokenizerProtocol:
        """Load the Qwen tokenizer once per finalization process."""
        if self._tokenizer is not None and self._tokenizer_model == tokenizer_model:
            return self._tokenizer
        import torch
        from qwen_tts import Qwen3TTSTokenizer

        if self._runtime_request.require_gpu and not torch.cuda.is_available():
            raise RuntimeError(
                "Governed audio-codes finalization requires `torch.cuda.is_available()` to be true."
            )

        flash_attn_importable = importlib.util.find_spec("flash_attn") is not None
        if self._runtime_request.require_flash_attn and not flash_attn_importable:
            raise RuntimeError(
                "Governed audio-codes finalization requires `flash_attn` inside the runtime."
            )

        tokenizer: _ConfiguredQwenTokenizerProtocol = Qwen3TTSTokenizer.from_pretrained(
            tokenizer_model,
            dtype=_runtime_request_dtype(self._runtime_request),
            attn_implementation=self._runtime_request.attn_implementation,
        )
        if self._runtime_request.require_gpu:
            target_device = torch.device(self._runtime_request.device)
            tokenizer.model = tokenizer.model.to(
                device=target_device,
                dtype=_runtime_request_dtype(self._runtime_request),
            )
            tokenizer.device = target_device
            observed_device = str(_first_model_parameter(tokenizer.model).device)
            if not observed_device.startswith("cuda"):
                raise RuntimeError(
                    "Governed audio-codes finalization expected the tokenizer model on GPU, "
                    f"but observed `{observed_device}`."
                )
        first_parameter = _first_model_parameter(tokenizer.model)
        self._runtime_report = AudioCodesRuntimeReport(
            runtime_kind=self._runtime_request.runtime_kind,
            tokenizer_model=tokenizer_model,
            requested_device=self._runtime_request.device,
            observed_device=str(first_parameter.device),
            requested_dtype=self._runtime_request.dtype,
            observed_dtype=str(first_parameter.dtype),
            requested_attn_implementation=self._runtime_request.attn_implementation,
            observed_attn_implementation=tokenizer.model.config._attn_implementation,
            require_gpu=self._runtime_request.require_gpu,
            require_flash_attn=self._runtime_request.require_flash_attn,
            torch_cuda_available=bool(torch.cuda.is_available()),
            torch_hip_version=None if torch.version.hip is None else str(torch.version.hip),
            flash_attn_importable=flash_attn_importable,
            flash_attn_version=_package_version("flash-attn"),
        )
        self._tokenizer_model = tokenizer_model
        self._tokenizer = tokenizer
        return tokenizer


_DEFAULT_GOVERNED_GPU_AUDIO_CODES_ENCODER = WarmAudioCodesEncoder(
    DEFAULT_GOVERNED_GPU_AUDIO_CODES_RUNTIME
)
_DEFAULT_CPU_AUDIO_CODES_ENCODER = WarmAudioCodesEncoder(DEFAULT_CPU_AUDIO_CODES_RUNTIME)


def encode_audio_codes_with_governed_gpu_runtime(
    *,
    tokenizer_model: str,
    audio_paths: list[Path],
) -> list[list[list[int]]]:
    """Generate Qwen `audio_codes` with the governed GPU-backed tokenizer runtime."""
    return _DEFAULT_GOVERNED_GPU_AUDIO_CODES_ENCODER(
        tokenizer_model=tokenizer_model,
        audio_paths=audio_paths,
    )


def describe_governed_audio_codes_runtime(tokenizer_model: str) -> AudioCodesRuntimeReport:
    """Return one machine-readable report describing the governed tokenizer runtime."""
    return _DEFAULT_GOVERNED_GPU_AUDIO_CODES_ENCODER.describe(tokenizer_model)


def take_governed_audio_codes_chunk_timing() -> AudioCodesChunkTiming | None:
    """Return the latest governed audio-code chunk timing payload when available."""
    return _DEFAULT_GOVERNED_GPU_AUDIO_CODES_ENCODER.take_last_chunk_timing()


def encode_audio_codes(
    *,
    tokenizer_model: str,
    audio_paths: list[Path],
) -> list[list[list[int]]]:
    """Generate Qwen `audio_codes` for one bounded audio-path chunk."""
    return _DEFAULT_CPU_AUDIO_CODES_ENCODER(
        tokenizer_model=tokenizer_model,
        audio_paths=audio_paths,
    )


def take_cpu_audio_codes_chunk_timing() -> AudioCodesChunkTiming | None:
    """Return the latest CPU audio-code chunk timing payload when available."""
    return _DEFAULT_CPU_AUDIO_CODES_ENCODER.take_last_chunk_timing()


def take_audio_codes_chunk_timing_for_encoder(
    encoder: AudioCodesEncoderProtocol,
) -> AudioCodesChunkTiming | None:
    """Return the latest timing payload for one known audio-code encoder surface."""
    if isinstance(encoder, WarmAudioCodesEncoder):
        return encoder.take_last_chunk_timing()
    if encoder is encode_audio_codes_with_governed_gpu_runtime:
        return take_governed_audio_codes_chunk_timing()
    if encoder is encode_audio_codes:
        return take_cpu_audio_codes_chunk_timing()
    return None


def reset_audio_codes_encoder_after_failure(
    encoder: AudioCodesEncoderProtocol,
) -> None:
    """Reset one known audio-code encoder after a failed chunk attempt."""
    if isinstance(encoder, WarmAudioCodesEncoder):
        encoder.reset()
        return
    if encoder is encode_audio_codes_with_governed_gpu_runtime:
        _DEFAULT_GOVERNED_GPU_AUDIO_CODES_ENCODER.reset()
        return
    if encoder is encode_audio_codes:
        _DEFAULT_CPU_AUDIO_CODES_ENCODER.reset()


def _load_audio_arrays_for_tokenizer(
    *,
    audio_paths: list[Path],
    target_sample_rate: int,
    loader: Callable[[Path, int], WaveformArray] | None = None,
) -> list[WaveformArray]:
    """Load one bounded audio chunk into arrays before tokenizer feature extraction."""
    if not audio_paths:
        return []
    effective_loader = loader or _load_audio_array
    max_workers = min(len(audio_paths), max(1, min(8, os.cpu_count() or 1)))
    if max_workers <= 1:
        return [effective_loader(path, target_sample_rate) for path in audio_paths]

    def _load_path(path: Path) -> WaveformArray:
        """Load one path at the requested tokenizer sample rate."""
        return effective_loader(path, target_sample_rate)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_load_path, audio_paths))


def _load_audio_array(path: Path, target_sample_rate: int) -> WaveformArray:
    """Load one waveform quickly, resampling only when the source rate differs."""
    import librosa
    import soundfile as sf

    waveform, source_sample_rate = sf.read(
        path,
        dtype="float32",
        always_2d=False,
    )
    if isinstance(waveform, np.ndarray) and waveform.ndim > 1:
        waveform = np.mean(waveform, axis=-1)
    if int(source_sample_rate) != target_sample_rate:
        waveform = librosa.resample(
            y=np.asarray(waveform, dtype=np.float32),
            orig_sr=int(source_sample_rate),
            target_sr=target_sample_rate,
        )
    return np.asarray(waveform, dtype=np.float32)


def _supports_direct_preloaded_waveform_encode(
    tokenizer: _ConfiguredQwenTokenizerProtocol,
) -> TypeGuard[_DirectEncodeConfiguredQwenTokenizerProtocol]:
    """Return whether the tokenizer exposes the direct encode surfaces we need."""
    return callable(getattr(tokenizer.feature_extractor, "__call__", None)) and callable(
        getattr(tokenizer.model, "encode", None)
    )


def _encode_preloaded_waveforms_directly(
    tokenizer: _DirectEncodeConfiguredQwenTokenizerProtocol,
    waveforms: list[WaveformArray],
    *,
    target_sample_rate: int,
) -> tuple[_EncodedAudioCodesProtocol, float, float]:
    """Encode already-normalized waveforms without re-entering tokenizer input normalization."""
    import torch

    feature_extract_started_at = time.perf_counter()
    inputs = tokenizer.feature_extractor(
        raw_audio=waveforms,
        sampling_rate=target_sample_rate,
        return_tensors="pt",
    )
    inputs = inputs.to(tokenizer.device).to(tokenizer.model.dtype)
    feature_extract_seconds = time.perf_counter() - feature_extract_started_at
    model_encode_started_at = time.perf_counter()
    with torch.inference_mode():
        encoded = tokenizer.model.encode(
            inputs["input_values"].squeeze(1),
            inputs["padding_mask"].squeeze(1),
            return_dict=True,
        )
    model_encode_seconds = time.perf_counter() - model_encode_started_at
    return encoded, feature_extract_seconds, model_encode_seconds


def _curated_row_from_spool(
    spool_row: SpoolRow,
    manifest_target: ManifestFamily,
    *,
    reference_audio_24k_path: str,
) -> CuratedRow:
    """Project one spool row into one family-specific curated row."""
    return CuratedRow(
        dataset=spool_row.dataset,
        source_split=spool_row.source_split,
        dataset_row_id=spool_row.dataset_row_id,
        speaker_id=spool_row.speaker_id,
        speaker_name=spool_row.speaker_name,
        speaker_from_id=spool_row.speaker_from_id,
        source_audio_path=spool_row.source_audio_path,
        audio_24k_path=spool_row.audio_24k_path,
        duration_seconds=spool_row.duration_seconds,
        text_normalized=spool_row.text_normalized,
        reference_audio_24k_path=reference_audio_24k_path,
        asr_model=spool_row.asr_model,
        asr_revision=spool_row.asr_revision,
        asr_transcript=spool_row.asr_transcript,
        asr_wer=spool_row.asr_wer,
        quality_tier=spool_row.quality_tier,
        speaker_quality_gate=spool_row.speaker_quality_gate,
        dedup_applied=spool_row.dedup_applied,
        admission_decision=spool_row.admission_decision,
        manifest_target=manifest_target,
    )


def _canonical_reference_audio_path(
    *,
    family: ManifestFamily,
    speaker_id: str,
) -> Path:
    """Return the canonical relative reference-audio path for one family speaker."""
    return Path("refs", family, speaker_id, "ref.wav")


def _build_reference_audio_paths(output_root: Path) -> dict[tuple[ManifestFamily, str], str]:
    """Materialize and index one deterministic reference clip per family speaker."""
    reference_audio_paths: dict[tuple[ManifestFamily, str], str] = {}
    for spool_row in iter_spool_rows(output_root):
        source_audio_path = output_root / spool_row.audio_24k_path
        for family in spool_row.manifest_targets:
            speaker_key = (family, spool_row.speaker_id)
            if speaker_key in reference_audio_paths:
                continue
            relative_reference_path = _canonical_reference_audio_path(
                family=family,
                speaker_id=spool_row.speaker_id,
            )
            absolute_reference_path = output_root / relative_reference_path
            absolute_reference_path.parent.mkdir(parents=True, exist_ok=True)
            if not absolute_reference_path.exists():
                shutil.copyfile(source_audio_path, absolute_reference_path)
            reference_audio_paths[speaker_key] = relative_reference_path.as_posix()
    return reference_audio_paths


def _raw_manifest_row_from_curated(curated_row: CuratedRow) -> RawManifestRow:
    """Project one curated row into one raw Qwen manifest row."""
    return RawManifestRow(
        audio=curated_row.audio_24k_path,
        text=curated_row.text_normalized,
        ref_audio=curated_row.reference_audio_24k_path,
        speaker_id=curated_row.speaker_id,
        dataset=curated_row.dataset,
        source_split=curated_row.source_split,
        quality_tier=curated_row.quality_tier,
    )


def _flush_audio_codes_chunk(
    *,
    output_root: Path,
    raw_writer: JsonlAtomicWriter,
    prepared_writer: JsonlAtomicWriter,
    raw_rows: list[RawManifestRow],
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    tokenizer_model: str,
) -> int:
    """Encode one bounded raw-row chunk and write raw/prepared manifest rows."""
    if not raw_rows:
        return 0
    audio_codes_list = encode_audio_codes_fn(
        tokenizer_model=tokenizer_model,
        audio_paths=[output_root / raw_row["audio"] for raw_row in raw_rows],
    )
    prepared_count = 0
    for raw_row, audio_codes in zip(raw_rows, audio_codes_list, strict=True):
        raw_writer.write_row(raw_row)
        prepared_writer.write_row(
            PreparedManifestRow(
                audio=raw_row["audio"],
                text=raw_row["text"],
                ref_audio=raw_row["ref_audio"],
                speaker_id=raw_row["speaker_id"],
                dataset=raw_row["dataset"],
                source_split=raw_row["source_split"],
                quality_tier=raw_row["quality_tier"],
                audio_codes=audio_codes,
            )
        )
        prepared_count += 1
    raw_rows.clear()
    return prepared_count


def finalize_from_spool(
    settings: PreprocessingSettings,
    *,
    output_root: Path,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    finalization_heartbeat_callback: FinalizationHeartbeatCallback | None = None,
) -> None:
    """Project durable spool rows into curated/raw/prepared manifest artifacts."""
    if settings.audio_codes_chunk_size <= 0:
        raise ValueError("`audio_codes_chunk_size` must be positive.")
    selected_families = set(settings.finalization_families)
    reference_audio_paths = _build_reference_audio_paths(output_root)
    curated_dir = output_root / "curated"
    manifests_dir = output_root / "manifests"
    completed_families: list[ManifestFamily] = []
    for family in CANONICAL_MANIFEST_FAMILIES:
        if family not in selected_families:
            continue
        admitted_row_count = sum(
            1
            for spool_row in iter_spool_rows(output_root)
            if family in spool_row.manifest_targets and spool_row.admission_decision == "admit"
        )
        total_chunk_count = (
            0
            if admitted_row_count == 0
            else ceil(admitted_row_count / settings.audio_codes_chunk_size)
        )
        completed_chunk_count = 0
        raw_chunk: list[RawManifestRow] = []
        with (
            JsonlAtomicWriter(curated_dir / f"{family}.jsonl") as curated_writer,
            JsonlAtomicWriter(manifests_dir / f"{family}.raw.jsonl") as raw_writer,
            JsonlAtomicWriter(manifests_dir / f"{family}.prepared.jsonl") as prepared_writer,
        ):
            for spool_row in iter_spool_rows(output_root):
                if family not in spool_row.manifest_targets:
                    continue
                curated_row = _curated_row_from_spool(
                    spool_row,
                    family,
                    reference_audio_24k_path=reference_audio_paths[(family, spool_row.speaker_id)],
                )
                curated_writer.write_row(curated_row)
                if curated_row.admission_decision == "admit":
                    raw_chunk.append(_raw_manifest_row_from_curated(curated_row))
                    if len(raw_chunk) >= settings.audio_codes_chunk_size:
                        if finalization_heartbeat_callback is not None:
                            finalization_heartbeat_callback(
                                FinalizationHeartbeat(
                                    current_family=family,
                                    completed_families=tuple(completed_families),
                                    current_chunk_index=completed_chunk_count + 1,
                                    completed_chunk_count=completed_chunk_count,
                                    total_chunk_count=total_chunk_count,
                                )
                            )
                        _flush_audio_codes_chunk(
                            output_root=output_root,
                            raw_writer=raw_writer,
                            prepared_writer=prepared_writer,
                            raw_rows=raw_chunk,
                            encode_audio_codes_fn=encode_audio_codes_fn,
                            tokenizer_model=settings.tokenizer_model,
                        )
                        completed_chunk_count += 1
            if raw_chunk:
                if finalization_heartbeat_callback is not None:
                    finalization_heartbeat_callback(
                        FinalizationHeartbeat(
                            current_family=family,
                            completed_families=tuple(completed_families),
                            current_chunk_index=completed_chunk_count + 1,
                            completed_chunk_count=completed_chunk_count,
                            total_chunk_count=total_chunk_count,
                        )
                    )
                _flush_audio_codes_chunk(
                    output_root=output_root,
                    raw_writer=raw_writer,
                    prepared_writer=prepared_writer,
                    raw_rows=raw_chunk,
                    encode_audio_codes_fn=encode_audio_codes_fn,
                    tokenizer_model=settings.tokenizer_model,
                )
                completed_chunk_count += 1
        completed_families.append(family)
        if finalization_heartbeat_callback is not None:
            finalization_heartbeat_callback(
                FinalizationHeartbeat(
                    current_family=family,
                    completed_families=tuple(completed_families),
                    current_chunk_index=completed_chunk_count,
                    completed_chunk_count=completed_chunk_count,
                    total_chunk_count=total_chunk_count,
                )
            )


def _report_markdown(report: PreprocessingReport) -> str:
    """Render one concise markdown summary for the completed preprocessing pass."""
    manifest_lines = "\n".join(
        f"- `{family}`: `{count}`" for family, count in sorted(report.manifest_counts.items())
    )
    dataset_lines = "\n".join(f"- `{dataset}`" for dataset in report.datasets)
    speaker_lines = "\n".join(f"- `{speaker_id}`" for speaker_id in report.speaker_ids)
    return (
        "# Qwen Swedish Preprocessing Report\n\n"
        f"- output_root: `{report.output_root}`\n"
        f"- asr_model: `{report.asr_model}`\n"
        f"- asr_revision: `{report.asr_revision}`\n"
        f"- tokenizer_model: `{report.tokenizer_model}`\n"
        f"- inventory_rows: `{report.inventory_rows}`\n"
        f"- curated_rows: `{report.curated_rows}`\n"
        f"- admitted_rows: `{report.admitted_rows}`\n"
        f"- prepared_rows: `{report.prepared_rows}`\n\n"
        "## Datasets\n\n"
        f"{dataset_lines}\n\n"
        "## Speakers\n\n"
        f"{speaker_lines}\n\n"
        "## Manifest Counts\n\n"
        f"{manifest_lines}\n"
    )


def build_reports(
    settings: PreprocessingSettings,
    *,
    output_root: Path,
) -> PreprocessingReport:
    """Rebuild report artifacts from deterministic on-disk pipeline outputs."""
    inventory_dir = output_root / "inventory"
    curated_dir = output_root / "curated"
    manifests_dir = output_root / "manifests"
    reports_dir = output_root / "reports"

    inventory_dataset_split_counts: Counter[str] = Counter()
    datasets: set[str] = set()
    speaker_ids: set[str] = set()
    for inventory_path in sorted(inventory_dir.glob("*.jsonl")):
        for row in iter_jsonl_objects(inventory_path):
            dataset = _required_str(row, "dataset", inventory_path)
            source_split = _required_str(row, "source_split", inventory_path)
            speaker_id = _required_str(row, "speaker_id", inventory_path)
            inventory_dataset_split_counts[f"{dataset}-{source_split}"] += 1
            datasets.add(dataset)
            speaker_ids.add(speaker_id)

    curated_dataset_split_counts: Counter[str] = Counter()
    quality_tier_counts: Counter[str] = Counter()
    reference_paths: dict[str, str] = {}
    curated_rows = 0
    for curated_path in sorted(curated_dir.glob("*.jsonl")):
        for row in iter_jsonl_objects(curated_path):
            curated_rows += 1
            dataset = _required_str(row, "dataset", curated_path)
            source_split = _required_str(row, "source_split", curated_path)
            quality_tier = _required_str(row, "quality_tier", curated_path)
            manifest_target = _required_str(row, "manifest_target", curated_path)
            speaker_id = _required_str(row, "speaker_id", curated_path)
            reference_audio_24k_path = _required_str(row, "reference_audio_24k_path", curated_path)
            curated_dataset_split_counts[f"{dataset}-{source_split}"] += 1
            quality_tier_counts[quality_tier] += 1
            reference_paths[f"{manifest_target}:{speaker_id}"] = reference_audio_24k_path

    manifest_counts: dict[ManifestFamily, int] = {}
    admitted_rows = 0
    prepared_rows = 0
    admitted_speaker_ids: set[str] = set()
    for family in CANONICAL_MANIFEST_FAMILIES:
        raw_path = manifests_dir / f"{family}.raw.jsonl"
        prepared_path = manifests_dir / f"{family}.prepared.jsonl"
        raw_count = sum(1 for _ in iter_jsonl_objects(raw_path))
        prepared_count = sum(1 for _ in iter_jsonl_objects(prepared_path))
        manifest_counts[family] = prepared_count
        admitted_rows += raw_count
        prepared_rows += prepared_count
        for row in iter_jsonl_objects(raw_path):
            admitted_speaker_ids.add(_required_str(row, "speaker_id", raw_path))

    write_json(
        reports_dir / "inventory_summary.json",
        {
            "dataset_split_counts": dict(sorted(inventory_dataset_split_counts.items())),
            "speaker_ids": sorted(speaker_ids),
        },
    )
    write_json(
        reports_dir / "filter_summary.json",
        {
            "curated_rows": curated_rows,
            "admitted_rows": admitted_rows,
            "quality_tier_counts": {
                "high_trust": quality_tier_counts.get("high_trust", 0),
                "medium_trust": quality_tier_counts.get("medium_trust", 0),
                "rejected": quality_tier_counts.get("rejected", 0),
            },
            "dataset_split_counts": dict(sorted(curated_dataset_split_counts.items())),
        },
    )
    write_json(
        reports_dir / "reference_selection_summary.json",
        {"speaker_reference_paths": dict(sorted(reference_paths.items()))},
    )
    write_json(
        reports_dir / "manifest_summary.json",
        {
            "manifest_counts": manifest_counts,
            "admitted_speaker_ids": sorted(admitted_speaker_ids),
        },
    )

    report = PreprocessingReport(
        output_root=output_root.as_posix(),
        datasets=sorted(datasets),
        asr_model=settings.asr_model,
        asr_revision=settings.asr_revision,
        tokenizer_model=settings.tokenizer_model,
        inventory_rows=sum(inventory_dataset_split_counts.values()),
        curated_rows=curated_rows,
        admitted_rows=admitted_rows,
        prepared_rows=prepared_rows,
        speaker_ids=sorted(speaker_ids),
        manifest_counts=manifest_counts,
    )
    write_json(output_root / "report.json", report)
    (output_root / "report.md").write_text(_report_markdown(report) + "\n", encoding="utf-8")
    return report


def _required_str(payload: dict[str, object], key: str, path: Path) -> str:
    """Return one required string field from one JSONL report source."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in {path}.")
    return value
