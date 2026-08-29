"""Runtime configuration tests for the answer-key daily token lease."""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.infrastructure.runtime_config import service_config_from_env


def test_answer_key_daily_token_limit_defaults_to_five_million(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_ANSWER_KEY_DAILY_TOKEN_LIMIT", raising=False)

    assert service_config_from_env().answer_key_daily_token_limit == 5_000_000


def test_answer_key_daily_token_limit_accepts_positive_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_ANSWER_KEY_DAILY_TOKEN_LIMIT", "12345")

    assert service_config_from_env().answer_key_daily_token_limit == 12_345


def test_answer_key_daily_token_limit_rejects_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_ANSWER_KEY_DAILY_TOKEN_LIMIT", "0")

    with pytest.raises(ValueError, match="SIR_CONVERT_A_LOT_ANSWER_KEY_DAILY_TOKEN_LIMIT"):
        service_config_from_env()
