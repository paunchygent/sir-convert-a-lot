"""Tests for canonical answer-key provider environment rendering."""

from __future__ import annotations

from pytest import CaptureFixture

from scripts.sir_convert_a_lot.devops import render_answer_key_provider_env


def test_cli_defaults_to_the_governed_luna_primary_catalog(capsys: CaptureFixture[str]) -> None:
    exit_code = render_answer_key_provider_env.main([])

    rendered = dict(line.split("=", maxsplit=1) for line in capsys.readouterr().out.splitlines())

    assert exit_code == 0
    assert rendered["SIR_CONVERT_A_LOT_STRUCTURED_LLM_PROVIDER_PROFILE"] == "openai-gpt-5.6-luna"
    assert rendered["SIR_CONVERT_A_LOT_STRUCTURED_LLM_PRIMARY_PROVIDER_ID"] == "openai-gpt-5.6-luna"
    assert rendered["SIR_CONVERT_A_LOT_STRUCTURED_LLM_FALLBACK_PROVIDER_ID"] == (
        "openrouter-glm-5.3-flash"
    )
