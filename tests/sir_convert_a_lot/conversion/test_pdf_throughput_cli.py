"""Key resolution tests for the PDF throughput benchmark CLI.

Purpose:
    Prove that `production_service` mode reads its key only from the injected
    environment variable and that local lanes keep explicit and synthetic keys.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.benchmarking.pdf_throughput_cli`.
"""

from __future__ import annotations

import argparse

import pytest

from scripts.sir_convert_a_lot.benchmarking.pdf_throughput_cli import (
    LOCAL_SYNTHETIC_API_KEY,
    PRODUCTION_API_KEY_ENV_VAR,
    _resolve_api_key,
)

SYNTHETIC_SENTINEL = "synthetic-sentinel-not-a-key"


def _args(*, runtime_mode: str, api_key: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(runtime_mode=runtime_mode, api_key=api_key)


def test_production_mode_uses_injected_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRODUCTION_API_KEY_ENV_VAR, SYNTHETIC_SENTINEL)

    assert _resolve_api_key(_args(runtime_mode="production_service")) == SYNTHETIC_SENTINEL


def test_production_mode_refuses_command_line_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRODUCTION_API_KEY_ENV_VAR, "injected-synthetic-value")

    with pytest.raises(SystemExit) as excinfo:
        _resolve_api_key(_args(runtime_mode="production_service", api_key=SYNTHETIC_SENTINEL))

    message = str(excinfo.value)
    assert f"only from the {PRODUCTION_API_KEY_ENV_VAR}" in message
    assert SYNTHETIC_SENTINEL not in message


def test_production_mode_without_variable_points_at_hemma_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(PRODUCTION_API_KEY_ENV_VAR, raising=False)

    with pytest.raises(SystemExit) as excinfo:
        _resolve_api_key(_args(runtime_mode="production_service"))

    message = str(excinfo.value)
    assert "benchmark:pdf-throughput-hemma" in message
    assert "--api-key" not in message


def test_local_mode_keeps_explicit_and_synthetic_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRODUCTION_API_KEY_ENV_VAR, "injected-synthetic-value")

    assert _resolve_api_key(_args(runtime_mode="in_process_app")) == LOCAL_SYNTHETIC_API_KEY
    assert (
        _resolve_api_key(_args(runtime_mode="in_process_app", api_key=SYNTHETIC_SENTINEL))
        == SYNTHETIC_SENTINEL
    )
