"""Tests for governed Qwen audio-code finalization helpers.

Purpose:
    Verify that the shared audio-code tokenizer runtime fails closed without
    GPU/flash-attn support and records the expected governed GPU posture when
    initialization succeeds.

Relationships:
    - Tests `ml.qwen.preprocessing.finalization`.
    - Protects the governed GPU-backed audio-code finalization contract.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import numpy as np
import pytest
import torch

from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
    AudioCodesRuntimeRequest,
    WarmAudioCodesEncoder,
    _load_audio_arrays_for_tokenizer,
    take_audio_codes_chunk_timing_for_encoder,
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
        self.encode_call_count = 0

    def parameters(self) -> list[_FakeParameter]:
        """Return one deterministic parameter list."""
        return [self._parameter]

    @property
    def dtype(self) -> object:
        """Return the current dtype of the fake model."""
        return self._parameter.dtype

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

    def encode(
        self,
        input_values: object,
        padding_mask: object,
        *,
        return_dict: bool,
    ) -> object:
        """Return one encoded-audio payload per batch item."""
        del padding_mask
        assert return_dict is True
        assert isinstance(input_values, torch.Tensor)
        self.encode_call_count += 1
        batch_size = int(input_values.shape[0])
        return SimpleNamespace(
            audio_codes=[
                _FakeAudioCodesTensor([[index, batch_size]]) for index in range(batch_size)
            ]
        )


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
    last_instance: "_FakeTokenizer | None" = None

    def __init__(self) -> None:
        self.model = _FakeModel()
        self.device: object = torch.device("cpu")
        self.feature_extractor = _FakeFeatureExtractor(self)
        self.last_encode_inputs: list[object] | None = None
        self.encode_call_count = 0

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
        cls.last_instance = cls()
        return cls.last_instance

    def encode(
        self,
        audio_paths: list[object],
        *,
        sr: int,
    ) -> object:
        """Return one encoded-audio payload per requested path."""
        assert sr == 24_000
        self.encode_call_count += 1
        self.last_encode_inputs = audio_paths
        return SimpleNamespace(
            audio_codes=[
                _FakeAudioCodesTensor([[index, len(audio_paths)]])
                for index, _ in enumerate(audio_paths)
            ]
        )


class _FakeFeatureBatch:
    """Minimal feature-batch stub for direct encode tests."""

    def __init__(self, batch_size: int) -> None:
        self._payload = {
            "input_values": torch.zeros((batch_size, 1, 2), dtype=torch.float32),
            "padding_mask": torch.ones((batch_size, 1, 2), dtype=torch.float32),
        }

    def to(self, destination: object) -> "_FakeFeatureBatch":
        """Accept one device or dtype move and keep the same fake batch."""
        del destination
        return self

    def __getitem__(self, key: str) -> torch.Tensor:
        """Return one tensor payload by key."""
        return self._payload[key]


class _FakeFeatureExtractor:
    """Minimal feature extractor that records waveform-array input."""

    def __init__(self, tokenizer: _FakeTokenizer) -> None:
        self._tokenizer = tokenizer
        self.sampling_rate = 24_000
        self.call_count = 0

    def __call__(
        self,
        *,
        raw_audio: list[object],
        sampling_rate: int,
        return_tensors: str,
    ) -> _FakeFeatureBatch:
        """Return one deterministic feature batch for the supplied audio arrays."""
        assert sampling_rate == 24_000
        assert return_tensors == "pt"
        self.call_count += 1
        self._tokenizer.last_encode_inputs = raw_audio
        return _FakeFeatureBatch(len(raw_audio))


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
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization.importlib.util.find_spec",
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
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization.importlib.util.find_spec",
        lambda name: object() if name == "flash_attn" else None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization._package_version",
        lambda package_name: "2.8.3" if package_name == "flash-attn" else None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization._load_audio_arrays_for_tokenizer",
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
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization.importlib.util.find_spec",
        lambda name: object() if name == "flash_attn" else None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization._load_audio_arrays_for_tokenizer",
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
    assert tokenizer.encode_call_count == 0
    assert tokenizer.feature_extractor.call_count == 1
    assert tokenizer.model.encode_call_count == 1
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


def test_governed_audio_codes_runtime_records_chunk_timing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The governed runtime should expose one timing payload for the last chunk."""
    _install_fake_qwen_tts(monkeypatch)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization.importlib.util.find_spec",
        lambda name: object() if name == "flash_attn" else None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization._load_audio_arrays_for_tokenizer",
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

    timing = take_audio_codes_chunk_timing_for_encoder(encoder)

    assert timing is not None
    assert timing.row_count == 2
    assert timing.preload_seconds >= 0.0
    assert timing.feature_extract_seconds is not None
    assert timing.feature_extract_seconds >= 0.0
    assert timing.model_encode_seconds is not None
    assert timing.model_encode_seconds >= 0.0
    assert timing.render_seconds >= 0.0
    assert timing.total_seconds >= 0.0
