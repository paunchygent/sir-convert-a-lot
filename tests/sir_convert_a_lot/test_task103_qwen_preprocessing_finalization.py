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

import pytest
import torch

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    AudioCodesRuntimeRequest,
    WarmAudioCodesEncoder,
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
        audio_paths: list[str],
        *,
        sr: int,
    ) -> object:
        """Return one encoded-audio payload per requested path."""
        assert sr == 24_000
        return SimpleNamespace(
            audio_codes=[
                _FakeAudioCodesTensor([[index, len(path)]])
                for index, path in enumerate(audio_paths)
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
    assert codes == [[[0, len("/tmp/a.wav")]], [[1, len("/tmp/longer-b.wav")]]]
    assert report.observed_device == "cuda:0"
    assert report.observed_dtype == "torch.bfloat16"
    assert report.observed_attn_implementation == "flash_attention_2"
    assert report.flash_attn_importable is True
    assert report.flash_attn_version == "2.8.3"
