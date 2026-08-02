"""Tests for deterministic torch GPU runtime probing.

Purpose:
    Validate runtime-kind classification and import-failure safety for
    `probe_torch_gpu_runtime`.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe`.
"""

from __future__ import annotations

import builtins
import sys
import types

import pytest

from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import probe_torch_gpu_runtime


class _FakeCuda:
    def __init__(self, *, available: bool, device_count: int, device_name: str) -> None:
        self._available = available
        self._device_count = device_count
        self._device_name = device_name

    def is_available(self) -> bool:
        return self._available

    def device_count(self) -> int:
        return self._device_count

    def get_device_name(self, index: int) -> str:
        if index != 0:
            raise ValueError("only index 0 is supported in fake runtime")
        return self._device_name


def _fake_torch_module(
    *,
    torch_version: str,
    hip_version: str | None,
    cuda_version: str | None,
    available: bool,
    device_count: int,
    device_name: str,
) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        __version__=torch_version,
        version=types.SimpleNamespace(hip=hip_version, cuda=cuda_version),
        cuda=_FakeCuda(
            available=available,
            device_count=device_count,
            device_name=device_name,
        ),
    )


def test_probe_classifies_rocm_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_torch = _fake_torch_module(
        torch_version="2.10.0+rocm7.2",
        hip_version="7.2.0",
        cuda_version=None,
        available=True,
        device_count=1,
        device_name="AMD Radeon AI PRO R9700",
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    probe = probe_torch_gpu_runtime()

    assert probe.runtime_kind == "rocm"
    assert probe.is_available is True
    assert probe.device_count == 1
    assert probe.device_name == "AMD Radeon AI PRO R9700"
    assert probe.hip_version == "7.2.0"


def test_probe_classifies_cuda_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_torch = _fake_torch_module(
        torch_version="2.10.0+cu128",
        hip_version=None,
        cuda_version="12.8",
        available=True,
        device_count=1,
        device_name="NVIDIA RTX",
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    probe = probe_torch_gpu_runtime()

    assert probe.runtime_kind == "cuda"
    assert probe.is_available is True
    assert probe.cuda_version == "12.8"
    assert probe.hip_version is None


def test_probe_returns_none_when_runtime_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_torch = _fake_torch_module(
        torch_version="2.10.0",
        hip_version=None,
        cuda_version=None,
        available=False,
        device_count=0,
        device_name="",
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    probe = probe_torch_gpu_runtime()

    assert probe.runtime_kind == "none"
    assert probe.is_available is False
    assert probe.device_count == 0
    assert probe.device_name is None


def test_probe_handles_torch_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    real_import = builtins.__import__

    def _fake_import(name: str, globals_obj=None, locals_obj=None, fromlist=(), level: int = 0):
        if name == "torch":
            raise ModuleNotFoundError("torch missing")
        return real_import(name, globals_obj, locals_obj, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    probe = probe_torch_gpu_runtime()

    assert probe.runtime_kind == "none"
    assert probe.is_available is False
    assert probe.torch_version is None
