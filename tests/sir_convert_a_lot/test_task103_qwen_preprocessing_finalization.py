"""Tests for governed Qwen audio-code finalization runtime helpers.

Purpose:
    Verify that the shared audio-code tokenizer runtime fails closed without
    GPU/flash-attn support and records the expected governed GPU posture when
    initialization succeeds.

Relationships:
    - Tests `task103_qwen_preprocessing_finalization.py`.
    - Protects the GPU-backed Task 101 bundle finalization contract introduced
      after `T149`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import numpy as np
import pytest
import torch

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    AudioCodesRuntimeRequest,
    WarmAudioCodesEncoder,
    _load_audio_arrays_for_tokenizer,
)


class _FakeParameter:
    """Small tensor-like parameter stub for runtime introspection tests."""

    def __init__(self) -> None:
        self.device: object = torch.device("cpu")
        self.dtype: object = torch.float32


class _FakeModel:
    """Minimal tokenizer-model stub that tracks `.to(...)` calls."""

    def __init__(self) -> None:
        self.config = SimpleNamespace(_attn_implementation="flash_attention_2")
        self._parameter = _FakeParameter()

    def parameters(self) -> list[_FakeParameter]:
        """Return one deterministic parameter list."""
        return [self._parameter]

    def to(
        self,
        device: object | None = None,
        *,
        dtype: object | None = None,
    ) -> "_FakeModel":
        """Simulate moving the model to one device/dtype pair."""
        if device is not None:
            self._parameter.device = device
        if dtype is not None:
            self._parameter.dtype = dtype
        return self


class _FakeAudioCodesTensor:
    """Minimal encoded-audio tensor stub."""

    def __init__(self, values: list[list[int]]) -> None:
        self._values = values

    def tolist(self) -> list[list[int]]:
        """Return the nested integer values."""
        return self._values


class _FakeTokenizer:
    """Minimal tokenizer stub with recorded initialization kwargs."""

    last_call: dict[str, object] | None = None

    def __init__(self) -> None:
        self.model = _FakeModel()
        self.device: object = torch.device("cpu")
        self.feature_extractor = SimpleNamespace(sampling_rate=24_000)
        self.last_encode_inputs: list[object] | None = None

    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path: str,
        **kwargs: object,
    ) -> "_FakeTokenizer":
        """Record the initialization request and return one tokenizer stub."""
        cls.last_call = {
            "pretrained_model_name_or_path": pretrained_model_name_or_path,
            **kwargs,
        }
        return cls()

    def encode(
        self,
        audio_paths: list[object],
        *,
        sr: int,
    ) -> object:
        """Return one encoded-audio payload per requested path."""
        assert sr == 24_000
        self.last_encode_inputs = audio_paths
        return SimpleNamespace(
            audio_codes=[
                _FakeAudioCodesTensor([[index, len(audio_paths)]])
                for index, _ in enumerate(audio_paths)
            ]
        )


def _install_fake_qwen_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expose one fake `qwen_tts` module for tokenizer runtime tests."""
    fake_module = ModuleType("qwen_tts")
    setattr(fake_module, "Qwen3TTSTokenizer", _FakeTokenizer)
    monkeypatch.setitem(sys.modules, "qwen_tts", fake_module)


def _runtime_request() -> AudioCodesRuntimeRequest:
    """Return one deterministic governed runtime request."""
    return AudioCodesRuntimeRequest(
        runtime_kind="task101_task103_qwen_audio_codes_gpu_v1",
        device="cuda:0",
        dtype="bfloat16",
        attn_implementation="flash_attention_2",
        require_gpu=True,
        require_flash_attn=True,
    )


def test_governed_audio_codes_runtime_requires_gpu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The governed runtime should fail closed when torch reports no GPU."""
    _install_fake_qwen_tts(monkeypatch)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    encoder = WarmAudioCodesEncoder(_runtime_request())

    with pytest.raises(RuntimeError, match="requires `torch.cuda.is_available\\(\\)`"):
        encoder(tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz", audio_paths=[Path("/tmp/a.wav")])


def test_governed_audio_codes_runtime_requires_flash_attn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The governed runtime should fail closed when `flash_attn` is unavailable."""
    _install_fake_qwen_tts(monkeypatch)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization.importlib.util.find_spec",
        lambda name: None if name == "flash_attn" else object(),
    )

    encoder = WarmAudioCodesEncoder(_runtime_request())

    with pytest.raises(RuntimeError, match="requires `flash_attn`"):
        encoder(tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz", audio_paths=[Path("/tmp/a.wav")])


def test_governed_audio_codes_runtime_uses_requested_gpu_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The governed runtime should initialize the tokenizer with explicit GPU posture."""
    _install_fake_qwen_tts(monkeypatch)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization.importlib.util.find_spec",
        lambda name: object() if name == "flash_attn" else None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization._package_version",
        lambda package_name: "2.8.3" if package_name == "flash-attn" else None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization._load_audio_arrays_for_tokenizer",
        lambda *, audio_paths, target_sample_rate: [
            np.asarray([float(index), float(target_sample_rate)], dtype=np.float32)
            for index, _ in enumerate(audio_paths)
        ],
    )

    encoder = WarmAudioCodesEncoder(_runtime_request())

    codes = encoder(
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        audio_paths=[Path("/tmp/a.wav"), Path("/tmp/longer-b.wav")],
    )
    report = encoder.describe("Qwen/Qwen3-TTS-Tokenizer-12Hz")

    assert _FakeTokenizer.last_call is not None
    assert _FakeTokenizer.last_call["pretrained_model_name_or_path"] == (
        "Qwen/Qwen3-TTS-Tokenizer-12Hz"
    )
    assert _FakeTokenizer.last_call["dtype"] == torch.bfloat16
    assert _FakeTokenizer.last_call["attn_implementation"] == "flash_attention_2"
    assert codes == [[[0, 2]], [[1, 2]]]
    assert report.observed_device == "cuda:0"
    assert report.observed_dtype == "torch.bfloat16"
    assert report.observed_attn_implementation == "flash_attention_2"
    assert report.flash_attn_importable is True
    assert report.flash_attn_version == "2.8.3"


def test_governed_audio_codes_runtime_preloads_waveforms_before_encode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The governed runtime should pass waveform arrays instead of file paths."""
    _install_fake_qwen_tts(monkeypatch)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization.importlib.util.find_spec",
        lambda name: object() if name == "flash_attn" else None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization._load_audio_arrays_for_tokenizer",
        lambda *, audio_paths, target_sample_rate: [
            np.asarray([float(index), float(target_sample_rate)], dtype=np.float32)
            for index, _ in enumerate(audio_paths)
        ],
    )

    encoder = WarmAudioCodesEncoder(_runtime_request())

    encoder(
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        audio_paths=[Path("/tmp/a.wav"), Path("/tmp/b.wav")],
    )

    assert _FakeTokenizer.last_call is not None
    tokenizer = cast(_FakeTokenizer | None, encoder._tokenizer)
    assert tokenizer is not None
    assert tokenizer.last_encode_inputs is not None
    assert all(isinstance(item, np.ndarray) for item in tokenizer.last_encode_inputs)


def test_load_audio_arrays_for_tokenizer_uses_parallel_loader_results() -> None:
    """Audio array preloading should preserve order across the bounded chunk."""
    audio_paths = [Path("/tmp/a.wav"), Path("/tmp/b.wav"), Path("/tmp/c.wav")]

    arrays = _load_audio_arrays_for_tokenizer(
        audio_paths=audio_paths,
        target_sample_rate=24_000,
        loader=lambda path, target_sample_rate: np.asarray(
            [len(path.as_posix()), target_sample_rate],
            dtype=np.float32,
        ),
    )

    assert [array.tolist() for array in arrays] == [
        [10.0, 24_000.0],
        [10.0, 24_000.0],
        [10.0, 24_000.0],
    ]
