"""Reference-input helpers shared by Qwen bundle materialization and training.

Purpose:
    Provide one canonical implementation for extracting, persisting, and loading
    precomputed Task 101 reference-mel inputs.

Relationships:
    - Imported by `dataset.py` to load persisted precomputed ref-mel tensors.
    - Imported by training-bundle helpers to materialize bundle-owned ref-mel artifacts.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import TypeAlias

import numpy as np
import numpy.typing as npt
import soundfile
import torch

from scripts.devops.qwen_finetuning_patches import sft_12hz_ref_input_contract

AudioArray: TypeAlias = npt.NDArray[np.float32]
PRECOMPUTED_REF_INPUT_KIND = sft_12hz_ref_input_contract.PRECOMPUTED_REF_INPUT_KIND
PRECOMPUTED_REF_INPUT_VERSION = sft_12hz_ref_input_contract.PRECOMPUTED_REF_INPUT_VERSION
PRECOMPUTED_REF_INPUT_SOURCE_FIELD = sft_12hz_ref_input_contract.PRECOMPUTED_REF_INPUT_SOURCE_FIELD


def _load_mel_spectrogram():
    """Import the Qwen mel extractor lazily so metadata-only paths stay lightweight."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from qwen_tts.core.models.modeling_qwen3_tts import mel_spectrogram

    return mel_spectrogram


def load_audio_to_np(path: Path) -> tuple[AudioArray, int]:
    """Load one mono waveform into float32 numpy form."""
    audio, sample_rate = soundfile.read(path.as_posix(), dtype="float32")
    if audio.ndim > 1:
        audio = np.mean(audio, axis=-1)
    return audio.astype(np.float32, copy=False), int(sample_rate)


@torch.inference_mode()
def extract_ref_mel(audio: AudioArray, *, sample_rate: int) -> torch.Tensor:
    """Extract one canonical Task 101 reference-mel tensor from 24 kHz audio."""
    if sample_rate != 24000:
        raise ValueError("Only support 24kHz audio for precomputed reference inputs.")
    mel_spectrogram = _load_mel_spectrogram()
    mel_output = mel_spectrogram(
        torch.from_numpy(audio).unsqueeze(0),
        n_fft=1024,
        num_mels=128,
        sampling_rate=24000,
        hop_size=256,
        win_size=1024,
        fmin=0,
        fmax=12000,
    ).transpose(1, 2)
    if not isinstance(mel_output, torch.Tensor):
        raise ValueError("Expected mel_spectrogram to return a torch.Tensor.")
    return mel_output.detach().to(dtype=torch.float32, device="cpu")


def extract_ref_mel_from_audio_path(audio_path: Path) -> torch.Tensor:
    """Load one audio path and return its canonical reference-mel tensor."""
    audio, sample_rate = load_audio_to_np(audio_path)
    return extract_ref_mel(audio, sample_rate=sample_rate)


def save_persisted_ref_mel(path: Path, ref_mel: torch.Tensor) -> None:
    """Persist one ref-mel tensor deterministically under the bundle root."""
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(ref_mel.detach().to(dtype=torch.float32, device="cpu"), path)


def load_persisted_ref_mel(path: Path) -> torch.Tensor:
    """Load one persisted ref-mel tensor from disk."""
    ref_mel = torch.load(path, map_location="cpu")
    if not isinstance(ref_mel, torch.Tensor):
        raise ValueError(f"Persisted ref-mel `{path.as_posix()}` did not contain a tensor.")
    return ref_mel.to(dtype=torch.float32, device="cpu")
