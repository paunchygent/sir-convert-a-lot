"""Regression tests for Hemma deploy and live-verification contracts.

Purpose:
    Lock expected remediation messaging and guardrail behavior for revision
    parity, key resolution, lane mapping, and metrics safety scans.

Relationships:
    - Exercises
      `scripts.sir_convert_a_lot.devops.hemma_deploy_verification_contracts`.
    - Required by Hemma deploy verification acceptance criteria.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.devops.hemma_deploy_verification_contracts import (
    VerificationContractError,
    assert_expected_revision_matches_remote,
    assert_service_revision_matches_remote,
    port_for_lane,
    resolve_api_key,
    scan_metrics_forbidden_substrings,
    service_url_for_lane,
)


def test_expected_revision_mismatch_prints_remediation() -> None:
    with pytest.raises(VerificationContractError) as exc_info:
        assert_expected_revision_matches_remote(
            expected_revision="1111111111111111111111111111111111111111",
            remote_revision="2222222222222222222222222222222222222222",
        )
    message = str(exc_info.value)
    assert "Expected revision does not match remote repository HEAD" in message
    assert "Remediation:" in message


def test_service_revision_mismatch_prints_remediation() -> None:
    with pytest.raises(VerificationContractError) as exc_info:
        assert_service_revision_matches_remote(
            service_revision="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            remote_revision="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
    message = str(exc_info.value)
    assert "Service revision reported by /readyz does not match remote repository HEAD" in message
    assert "Remediation:" in message


def test_key_resolution_missing_key_fails() -> None:
    with pytest.raises(VerificationContractError, match="Missing API key"):
        resolve_api_key(api_key_arg=None, environ={}, allow_dev_key=False)


def test_dev_only_key_refused_without_allow_flag() -> None:
    with pytest.raises(VerificationContractError, match="Refusing implicit dev-only-key"):
        resolve_api_key(
            api_key_arg=None,
            environ={"SIR_CONVERT_A_LOT_V2_API_KEY": "dev-only-key"},
            allow_dev_key=False,
        )


def test_lane_port_mapping_host_and_docker() -> None:
    assert port_for_lane("host") == 28085
    assert port_for_lane("docker") == 8085
    assert service_url_for_lane("host") == "http://127.0.0.1:28085"
    assert service_url_for_lane("docker") == "http://127.0.0.1:8085"


def test_metrics_scan_rejects_forbidden_job_id_substrings() -> None:
    metrics = (
        "# HELP sample\n"
        'sir_convert_a_lot_jobs_total{status="succeeded",job_id="abc"} 1\n'
        "jobv2_runtime_counter 1\n"
    )
    assert scan_metrics_forbidden_substrings(metrics) == ["job_id=", "jobv2_"]
