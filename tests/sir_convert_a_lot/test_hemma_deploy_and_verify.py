"""Tests for Hemma deploy-and-verify orchestration behavior.

Purpose:
    Lock command orchestration behavior that protects live deploy verification,
    including Docker permission fallback on remote recreate.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify`.
    - Complements Task 76 contract tests.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.devops import hemma_deploy_and_verify


def test_remote_recreate_service_retries_with_sudo_on_docker_socket_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
        redactions: tuple[str, ...] = (),
    ) -> str:
        del label, redactions
        calls.append(remote_args)
        if len(calls) == 1:
            raise hemma_deploy_and_verify.CommandExecutionError(
                "permission denied while trying to connect to the Docker daemon socket"
            )
        return ""

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    hemma_deploy_and_verify._remote_recreate_service()

    assert calls[0] == ["pdm", "run", "dev-recreate", "sir_convert_a_lot_prod"]
    assert calls[1] == [
        "sudo",
        "-n",
        "/home/paunchygent/.local/bin/pdm",
        "run",
        "dev-recreate",
        "sir_convert_a_lot_prod",
    ]


def test_remote_recreate_service_raises_on_non_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
        redactions: tuple[str, ...] = (),
    ) -> str:
        del label, redactions
        calls.append(remote_args)
        raise hemma_deploy_and_verify.CommandExecutionError("unexpected recreate failure")

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    with pytest.raises(hemma_deploy_and_verify.CommandExecutionError, match="unexpected"):
        hemma_deploy_and_verify._remote_recreate_service()

    assert calls == [["pdm", "run", "dev-recreate", "sir_convert_a_lot_prod"]]


def test_fetch_readyz_with_retry_handles_transient_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses: list[str] = [
        "error",
        '{"ready": false, "reasons": ["warming"]}',
        '{"ready": true, "service_revision": "abc"}',
    ]

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
        redactions: tuple[str, ...] = (),
    ) -> str:
        del remote_args, label, redactions
        if not responses:
            raise AssertionError("unexpected extra readyz fetch")
        value = responses.pop(0)
        if value == "error":
            raise hemma_deploy_and_verify.CommandExecutionError("connection reset")
        return value

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    payload = hemma_deploy_and_verify._fetch_readyz_with_retry(
        service_url="http://127.0.0.1:28085",
        timeout_seconds=1.0,
        poll_interval_seconds=0.0,
    )

    assert payload["ready"] is True
