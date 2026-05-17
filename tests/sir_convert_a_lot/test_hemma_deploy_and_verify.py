"""Tests for Hemma deploy-and-verify orchestration behavior.

Purpose:
    Lock command orchestration behavior that protects live deploy verification,
    including Docker permission fallback on remote recreate.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify`.
    - Complements Task 76 contract tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import hemma_deploy_and_verify, public_edge_verification


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

    assert calls[0] == [
        "pdm",
        "run",
        "prod-recreate",
        "sir_convert_qwen_answer_key",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
        "sir_convert_a_lot_public_reserved",
    ]
    assert calls[1] == [
        "sudo",
        "-n",
        "env",
        "PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "/home/paunchygent/.local/bin/pdm",
        "run",
        "prod-recreate",
        "sir_convert_qwen_answer_key",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
        "sir_convert_a_lot_public_reserved",
    ]


def test_remote_recreate_service_retries_with_sudo_on_docker_api_permission_error(
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
                "permission denied while trying to connect to the docker API"
            )
        return ""

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    hemma_deploy_and_verify._remote_recreate_service()

    assert calls[1] == [
        "sudo",
        "-n",
        "env",
        "PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "/home/paunchygent/.local/bin/pdm",
        "run",
        "prod-recreate",
        "sir_convert_qwen_answer_key",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
        "sir_convert_a_lot_public_reserved",
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

    assert calls == [
        [
            "pdm",
            "run",
            "prod-recreate",
            "sir_convert_qwen_answer_key",
            "sir_convert_a_lot_gpu_worker",
            "sir_convert_a_lot_prod",
            "sir_convert_a_lot_public_reserved",
        ]
    ]


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


def test_execute_workflow_records_public_edge_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote_calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        label: str,
        env: dict[str, str] | None = None,
        redactions: tuple[str, ...] = (),
    ) -> str:
        del label, env, redactions
        if command == ["git", "push", "origin", "HEAD"]:
            return ""
        raise AssertionError(f"unexpected local command: {command!r}")

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
        redactions: tuple[str, ...] = (),
    ) -> str:
        del label, redactions
        remote_calls.append(remote_args)
        if remote_args == ["git", "pull", "--ff-only"]:
            return ""
        if remote_args == ["git", "rev-parse", "HEAD"]:
            return "abc\n"
        if remote_args[:4] == ["pdm", "run", "python", "-m"]:
            return ""
        if remote_args == ["curl", "-fsS", "http://127.0.0.1:28085/metrics"]:
            return "# safe metrics\n"
        raise AssertionError(f"unexpected remote command: {remote_args!r}")

    def fake_verify_public_edge(
        *,
        paths: public_edge_verification.PublicEdgeArtifactPaths,
        remote_revision: str,
        run_local: public_edge_verification.CommandRunner,
        run_remote: public_edge_verification.CommandRunner,
    ) -> dict[str, object]:
        del run_local, run_remote
        assert remote_revision == "abc"
        return {
            "status": "passed",
            "public_host": "convert.hule.education",
            "nginx_proxy": {
                "convert_server_name_registered": True,
                "reserved_default_host_configured": True,
            },
            "unknown_host_probe": {
                "allowed_status_observed": True,
                "reserved_placeholder_observed": True,
            },
            "public_edge_artifact": paths.public_edge_json.name,
        }

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_command", fake_run_command)
    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)
    monkeypatch.setattr(hemma_deploy_and_verify, "_remote_recreate_service", lambda: None)
    monkeypatch.setattr(
        hemma_deploy_and_verify,
        "_fetch_readyz_with_retry",
        lambda service_url: {"ready": True, "service_revision": "abc"},
    )
    monkeypatch.setattr(
        hemma_deploy_and_verify,
        "verify_structured_llm_provider",
        lambda run_remote: {
            "models_reachable": True,
            "structured_probe_passed": True,
            "provider_url": "http://sir_convert_qwen_answer_key:8082",
        },
    )
    monkeypatch.setattr(
        hemma_deploy_and_verify,
        "verify_public_edge",
        fake_verify_public_edge,
    )

    settings = hemma_deploy_and_verify.WorkflowSettings(
        expected_revision="abc",
        lane="host",
        service_url="http://127.0.0.1:28085",
        output_root=tmp_path,
        api_key="secret",
        api_key_source="cli",
        allow_dev_key=False,
    )

    report = hemma_deploy_and_verify.execute_workflow(settings)

    assert report["status"] == "passed"
    checks = report["checks"]
    assert isinstance(checks, dict)
    assert checks["public_https_reserved_passed"] is True
    assert checks["public_tls_certificate_passed"] is True
    assert checks["nginx_proxy_public_host_registered"] is True
    assert checks["default_host_reserved_placeholder_passed"] is True
    assert checks["structured_llm_models_reachable"] is True
    assert checks["structured_llm_microprobe_passed"] is True
    assert report["public_edge"] is not None
    assert report["structured_llm"] is not None

    report_payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report_payload["checks"]["default_host_reserved_placeholder_passed"] is True
    assert report_payload["checks"]["structured_llm_microprobe_passed"] is True
    report_md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "public_edge.json" in report_md
    assert (tmp_path / "public_edge.json").exists()
    assert remote_calls[-1] == ["curl", "-fsS", "http://127.0.0.1:28085/metrics"]


def test_execute_workflow_records_structured_llm_failure_before_ocr_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote_calls: list[list[str]] = []

    def fake_run_command(
        command: list[str],
        *,
        label: str,
        env: dict[str, str] | None = None,
        redactions: tuple[str, ...] = (),
    ) -> str:
        del label, env, redactions
        if command == ["git", "push", "origin", "HEAD"]:
            return ""
        raise AssertionError(f"unexpected local command: {command!r}")

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
        redactions: tuple[str, ...] = (),
    ) -> str:
        del label, redactions
        remote_calls.append(remote_args)
        if remote_args == ["git", "pull", "--ff-only"]:
            return ""
        if remote_args == ["git", "rev-parse", "HEAD"]:
            return "abc\n"
        raise AssertionError(f"unexpected remote command: {remote_args!r}")

    def fail_structured_llm(run_remote: object) -> dict[str, object]:
        del run_remote
        raise hemma_deploy_and_verify.VerificationContractError("provider not reachable")

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_command", fake_run_command)
    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)
    monkeypatch.setattr(hemma_deploy_and_verify, "_remote_recreate_service", lambda: None)
    monkeypatch.setattr(
        hemma_deploy_and_verify,
        "_fetch_readyz_with_retry",
        lambda service_url: {"ready": True, "service_revision": "abc"},
    )
    monkeypatch.setattr(
        hemma_deploy_and_verify, "verify_structured_llm_provider", fail_structured_llm
    )

    settings = hemma_deploy_and_verify.WorkflowSettings(
        expected_revision="abc",
        lane="host",
        service_url="http://127.0.0.1:28085",
        output_root=tmp_path,
        api_key="secret",
        api_key_source="cli",
        allow_dev_key=False,
    )

    report = hemma_deploy_and_verify.execute_workflow(settings)

    checks = report["checks"]
    assert isinstance(checks, dict)
    assert report["status"] == "failed"
    assert report["failure"] == "provider not reachable"
    assert checks["structured_llm_models_reachable"] is False
    assert checks["structured_llm_microprobe_passed"] is False
    assert checks["live_smoke_passed"] is False
