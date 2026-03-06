"""Support utilities for the OpenVoice Task 81 sidecar adapter.

Purpose:
    Isolate the OpenVoice-specific runtime helpers that are needed by the
    normalized ADR-0007 sidecar backend without forcing the main adapter module
    to carry upstream compatibility details and heavy audio preprocessing logic.

Relationships:
    - Imported by `openvoice_runtime.py` for converter construction, bounded
      reference-audio preprocessing, and small runtime utility helpers.
    - Mirrors only the VAD-based reference-speaker flow from the official
      OpenVoice benchmark path so Hemma can avoid the broken
      `faster-whisper`/PyAV build chain on Python 3.12.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import os
import shutil
from pathlib import Path
from typing import Iterator, Protocol


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
    device: str
    watermark_model: object | None
    version: str

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


def _package_version_or_none(name: str) -> str | None:
    """Return one installed package version when available."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _create_tone_color_converter(config_path: Path, *, device: str) -> _OpenVoiceConverter:
    """Create a no-watermark converter for Task 81 without unsupported kwargs."""
    from openvoice.api import OpenVoiceBaseClass, ToneColorConverter

    converter: _OpenVoiceConverter = ToneColorConverter.__new__(ToneColorConverter)
    OpenVoiceBaseClass.__init__(converter, config_path.as_posix(), device=device)
    converter.watermark_model = None
    converter.version = getattr(converter.hps, "_version_", "v1")
    return converter


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


def _optional_path_env(name: str) -> Path | None:
    """Return one optional path-valued environment setting."""
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    return Path(stripped)


def _positive_int(value: object, *, label: str) -> int:
    """Convert one runtime value to a strictly positive integer."""
    if not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"{label} must be a positive integer, got {value!r}.")
    return value


def _normalized_suffix(filename: str) -> str:
    """Return one safe suffix for a temporary reference-audio file."""
    suffix = Path(filename).suffix.strip()
    if suffix == "":
        return ".wav"
    if len(suffix) > 10:
        return ".wav"
    return suffix


def _resample_audio_file(
    *,
    source_path: Path,
    target_path: Path,
    target_sample_rate_hz: int,
) -> None:
    """Resample one WAV artifact explicitly to the converter input rate."""
    import librosa
    import soundfile

    waveform, source_sample_rate_hz = librosa.load(source_path.as_posix(), sr=None, mono=True)
    resampled_waveform = librosa.resample(
        waveform,
        orig_sr=source_sample_rate_hz,
        target_sr=target_sample_rate_hz,
    )
    soundfile.write(target_path.as_posix(), resampled_waveform, target_sample_rate_hz)


def extract_target_speaker_embedding(
    *,
    reference_path: Path,
    converter: _OpenVoiceConverter,
    temp_dir: Path,
    debug_artifact_dir: Path | None,
) -> object:
    """Prepare one reference speaker embedding using OpenVoice's VAD flow only."""
    processed_reference_root = temp_dir / "processed_reference"
    audio_name = _build_reference_audio_name(reference_path, version=converter.version)
    processed_reference_dir = processed_reference_root / audio_name
    wavs_dir = _split_audio_vad(
        audio_path=reference_path,
        audio_name=audio_name,
        target_dir=processed_reference_root,
    )
    reference_segments = sorted(path.as_posix() for path in wavs_dir.glob("*.wav"))
    if not reference_segments:
        raise RuntimeError("OpenVoice reference preprocessing produced no WAV segments.")
    se_path = processed_reference_dir / "se.pth"
    target_se = converter.extract_se(reference_segments, se_save_path=se_path.as_posix())
    if debug_artifact_dir is not None and processed_reference_dir.exists():
        shutil.copytree(
            processed_reference_dir,
            debug_artifact_dir / "processed_reference",
            dirs_exist_ok=True,
        )
    return target_se


def _build_reference_audio_name(reference_path: Path, *, version: str) -> str:
    """Return the OpenVoice-style deterministic directory name for one reference clip."""
    return f"{reference_path.stem}_{version}_{_hash_audio_content(reference_path)}"


def _hash_audio_content(reference_path: Path) -> str:
    """Hash one audio waveform in the same shape OpenVoice uses for reference prep."""
    import librosa

    waveform, _ = librosa.load(reference_path.as_posix(), sr=None, mono=True)
    digest = hashlib.sha256(waveform.tobytes()).digest()
    return base64.b64encode(digest).decode("utf-8")[:16].replace("/", "_^")


def _split_audio_vad(
    *,
    audio_path: Path,
    audio_name: str,
    target_dir: Path,
    split_seconds: float = 10.0,
) -> Path:
    """Split one reference clip with the upstream VAD-only OpenVoice strategy."""
    import numpy as np
    from pydub import AudioSegment
    from whisper_timestamped.transcribe import get_audio_tensor, get_vad_segments

    sample_rate_hz = 16000
    audio_vad = get_audio_tensor(audio_path.as_posix())
    sample_segments = get_vad_segments(
        audio_vad,
        output_sample=True,
        min_speech_duration=0.1,
        min_silence_duration=1,
        method="silero",
    )
    speech_segments = [
        (float(segment["start"]) / sample_rate_hz, float(segment["end"]) / sample_rate_hz)
        for segment in sample_segments
    ]
    audio = AudioSegment.from_file(audio_path.as_posix())
    active_audio = AudioSegment.silent(duration=0)
    for start_time, end_time in speech_segments:
        active_audio += audio[int(start_time * 1000) : int(end_time * 1000)]

    audio_duration_seconds = active_audio.duration_seconds
    target_folder = target_dir / audio_name
    wavs_folder = target_folder / "wavs"
    wavs_folder.mkdir(parents=True, exist_ok=True)
    if audio_duration_seconds <= 0:
        raise RuntimeError("Reference clip did not contain usable speech after VAD.")

    split_count = int(np.round(audio_duration_seconds / split_seconds))
    if split_count <= 0:
        raise RuntimeError("Reference clip is too short for OpenVoice reference preprocessing.")
    interval_seconds = audio_duration_seconds / split_count

    start_time = 0.0
    for index in range(split_count):
        end_time = min(start_time + interval_seconds, audio_duration_seconds)
        if index == split_count - 1:
            end_time = audio_duration_seconds
        segment_path = wavs_folder / f"{audio_name}_seg{index}.wav"
        segment_audio = active_audio[int(start_time * 1000) : int(end_time * 1000)]
        segment_audio.export(segment_path.as_posix(), format="wav")
        start_time = end_time

    return wavs_folder
