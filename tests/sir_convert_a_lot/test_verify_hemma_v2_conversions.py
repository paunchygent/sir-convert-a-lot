"""Unit tests for Hemma v2 verifier trusted-bundle preconditions.

Purpose:
    Lock the fail-closed behavior for trusted-bundle verification so the
    verifier cannot silently skip the internal-lane proof and still emit a
    misleading success report.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions`.
    - Complements helper tests in `test_verify_hemma_v2_conversions_helpers.py`.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.devops import verify_hemma_v2_conversions


def test_require_internal_api_key_rejects_blank_value() -> None:
    with pytest.raises(SystemExit, match="Missing --internal-api-key"):
        verify_hemma_v2_conversions._require_internal_api_key("   ")


def test_require_internal_api_key_returns_trimmed_value() -> None:
    assert (
        verify_hemma_v2_conversions._require_internal_api_key(" internal-secret-key \n")
        == "internal-secret-key"
    )
