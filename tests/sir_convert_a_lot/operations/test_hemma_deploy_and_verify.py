"""Tests for Hemma deploy-and-verify orchestration behavior.

Purpose:
    Lock command orchestration behavior that protects live deploy verification,
    including Docker permission fallback on remote recreate.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify`.
    - Complements Hemma deploy verification contract tests.
"""

from __future__ import annotations

import json
import socket
import ssl
from pathlib import Path

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

    hemma_deploy_and_verify._remote_recreate_service("verified-revision")

    assert calls[0] == [
        "env",
        "SIR_CONVERT_A_LOT_SERVICE_REVISION=verified-revision",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION=verified-revision",
        "pdm",
        "run",
        "prod-recreate",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
    ]
    assert calls[1] == [
        "sudo",
        "-n",
        "env",
        "PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "SIR_CONVERT_A_LOT_SERVICE_REVISION=verified-revision",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION=verified-revision",
        "/home/paunchygent/.local/bin/pdm",
        "run",
        "prod-recreate",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
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

    hemma_deploy_and_verify._remote_recreate_service("verified-revision")

    assert calls[0] == [
        "env",
        "SIR_CONVERT_A_LOT_SERVICE_REVISION=verified-revision",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION=verified-revision",
        "pdm",
        "run",
        "prod-recreate",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
    ]
    assert calls[1] == [
        "sudo",
        "-n",
        "env",
        "PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY=/home/paunchygent/apps/skill-repository",
        "SIR_CONVERT_A_LOT_SERVICE_REVISION=verified-revision",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION=verified-revision",
        "/home/paunchygent/.local/bin/pdm",
        "run",
        "prod-recreate",
        "sir_convert_a_lot_gpu_worker",
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
        hemma_deploy_and_verify._remote_recreate_service("verified-revision")

    assert calls == [
        [
            "env",
            "SIR_CONVERT_A_LOT_SERVICE_REVISION=verified-revision",
            "SIR_CONVERT_A_LOT_EXPECTED_REVISION=verified-revision",
            "pdm",
            "run",
            "prod-recreate",
            "sir_convert_a_lot_gpu_worker",
            "sir_convert_a_lot_prod",
        ]
    ]


def test_remote_recreate_service_injects_verified_revision(
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
        return ""

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    hemma_deploy_and_verify._remote_recreate_service("verified-revision")

    assert calls == [
        [
            "env",
            "SIR_CONVERT_A_LOT_SERVICE_REVISION=verified-revision",
            "SIR_CONVERT_A_LOT_EXPECTED_REVISION=verified-revision",
            "pdm",
            "run",
            "prod-recreate",
            "sir_convert_a_lot_gpu_worker",
            "sir_convert_a_lot_prod",
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


PRIVATE_ARTIFACTS = {"report.json", "report.md", "readyz.json", "metrics.prom", "remote_head.txt"}
PRIVATE_CHECKS = {
    "expected_revision_matches_remote",
    "service_revision_matches_remote",
    "live_smoke_passed",
    "live_smoke_required",
    "metrics_scan_passed",
    "metrics_forbidden_substrings",
}


@pytest.fixture(autouse=True)
def reject_public_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail on direct DNS, socket or certificate access outside command fakes."""

    def reject(*args: object, **kwargs: object) -> None:
        raise AssertionError("deploy verification must not inspect public DNS or TLS")

    monkeypatch.setattr(socket, "gethostbyname", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(ssl, "create_default_context", reject)


def assert_private_artifacts(output_root: Path, report: dict[str, object]) -> None:
    assert {path.name for path in output_root.iterdir()} == PRIVATE_ARTIFACTS
    checks = report["checks"]
    assert isinstance(checks, dict)
    assert set(checks) == PRIVATE_CHECKS
    assert "public_edge" not in report
    assert json.loads((output_root / "report.json").read_text()) == report
    markdown = (output_root / "report.md").read_text()
    for name in PRIVATE_ARTIFACTS:
        assert f"`{name}`" in markdown
    for retired in ("public_", "nginx", "unknown_host", "default_host", "convert.hule.education"):
        assert retired not in markdown


@pytest.mark.parametrize(
    "scenario,expected_status",
    [
        ("success", "passed"),
        ("smoke_failure", "passed"),
        ("pull_failure", "failed"),
        ("revision_mismatch", "failed"),
        ("service_mismatch", "failed"),
        ("unsafe_metrics", "failed"),
    ],
)
def test_execute_workflow_uses_only_published_source_and_private_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    expected_status: str,
) -> None:
    remote_calls: list[list[str]] = []
    pull = ["git", "pull", "--ff-only"]
    revision = ["git", "rev-parse", "HEAD"]
    recreate = [
        "env",
        "SIR_CONVERT_A_LOT_SERVICE_REVISION=abc",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION=abc",
        "pdm",
        "run",
        "prod-recreate",
        "sir_convert_a_lot_gpu_worker",
        "sir_convert_a_lot_prod",
    ]
    readyz = ["curl", "-sS", "http://127.0.0.1:28085/readyz"]
    smoke = [
        "pdm",
        "run",
        "python",
        "-m",
        "scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions",
        "--lane",
        "host",
        "--api-key",
        "secret",
        "--output-root",
        "build/verification/hemma-deploy-verify/v2-smoke",
    ]
    metrics = ["curl", "-fsS", "http://127.0.0.1:28085/metrics"]

    def reject_local(
        command: list[str],
        *,
        label: str,
        env: dict[str, str] | None = None,
        redactions: tuple[str, ...] = (),
    ) -> str:
        raise AssertionError(f"unexpected local/publication command: {command!r}")

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
        redactions: tuple[str, ...] = (),
    ) -> str:
        remote_calls.append(remote_args)
        if remote_args == pull:
            if scenario == "pull_failure":
                raise hemma_deploy_and_verify.CommandExecutionError("pull failed")
            return ""
        if remote_args == revision:
            return "wrong\n" if scenario == "revision_mismatch" else "abc\n"
        if remote_args == recreate:
            return ""
        if remote_args == readyz:
            return json.dumps(
                {
                    "ready": True,
                    "service_revision": "wrong" if scenario == "service_mismatch" else "abc",
                }
            )
        if remote_args == smoke:
            assert redactions == ("secret",)
            if scenario == "smoke_failure":
                raise hemma_deploy_and_verify.CommandExecutionError("gpu_not_available")
            return ""
        if remote_args == metrics:
            return 'jobs{job_id="unsafe"} 1\n' if scenario == "unsafe_metrics" else "# safe\n"
        raise AssertionError(f"unexpected public/publication/remote command: {remote_args!r}")

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_command", reject_local)
    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)
    report = hemma_deploy_and_verify.execute_workflow(
        hemma_deploy_and_verify.WorkflowSettings(
            expected_revision="abc",
            lane="host",
            service_url="http://127.0.0.1:28085",
            output_root=tmp_path,
            api_key="secret",
            api_key_source="cli",
            allow_dev_key=False,
        )
    )

    assert report["status"] == expected_status
    assert_private_artifacts(tmp_path, report)
    expected_calls = [pull, revision, recreate, readyz, smoke, metrics]
    count = {"pull_failure": 1, "revision_mismatch": 2, "service_mismatch": 4}.get(scenario, 6)
    assert remote_calls == expected_calls[:count]
    checks = report["checks"]
    assert isinstance(checks, dict)
    assert checks["live_smoke_required"] is False
    if scenario in ("success", "smoke_failure"):
        assert report["failure"] is None
        assert checks["expected_revision_matches_remote"] is True
        assert checks["service_revision_matches_remote"] is True
        assert checks["metrics_scan_passed"] is True
        assert checks["live_smoke_passed"] is (scenario == "success")
    else:
        assert report["failure"]
    if scenario == "smoke_failure":
        assert report["live_smoke_failure"] == "gpu_not_available"
        assert "## Non-Blocking Evidence" in (tmp_path / "report.md").read_text()


def test_main_settings_failure_writes_only_private_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_command(
        command: list[str],
        *,
        label: str,
        env: dict[str, str] | None = None,
        redactions: tuple[str, ...] = (),
    ) -> str:
        if command == ["git", "rev-parse", "HEAD^{commit}"]:
            return "abc\n"
        raise AssertionError(f"unexpected publication/public/remote command: {command!r}")

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_command", fake_run_command)
    monkeypatch.delenv("SIR_CONVERT_A_LOT_V2_API_KEY", raising=False)
    assert (
        hemma_deploy_and_verify.main(
            [
                "--expected-revision",
                "HEAD",
                "--output-root",
                str(tmp_path),
            ]
        )
        == 1
    )
    report = json.loads((tmp_path / "report.json").read_text())
    assert "Missing API key" in report["failure"]
    assert_private_artifacts(tmp_path, report)
    assert json.loads((tmp_path / "readyz.json").read_text()) == {}
    assert (tmp_path / "metrics.prom").read_text() == "# metrics not captured\n"
    assert (tmp_path / "remote_head.txt").read_text() == "unavailable\n"
