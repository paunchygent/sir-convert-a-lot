"""Tests for Hemma deploy-and-verify orchestration behavior.

Purpose:
    Lock command orchestration behavior that protects live deploy verification,
    including the single, unretried remote recreate call.

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


def test_remote_recreate_service_does_not_retry_on_docker_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    diagnostic = "permission denied while trying to connect to the Docker daemon socket"

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
    ) -> str:
        del label
        calls.append(remote_args)
        raise hemma_deploy_and_verify.CommandExecutionError(diagnostic)

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    with pytest.raises(hemma_deploy_and_verify.CommandExecutionError) as excinfo:
        hemma_deploy_and_verify._remote_recreate_service("verified-revision")

    assert str(excinfo.value) == diagnostic
    assert len(calls) == 1
    assert "sudo" not in calls[0]
    assert "prod-recreate" in calls[0]


def test_remote_recreate_service_raises_on_non_permission_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
    ) -> str:
        del label
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


def test_remote_recreate_service_propagates_claim_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claim_line = json.dumps(
        {
            "outcome": "queued",
            "reason": "queued position 1 awaiting huleedu-research",
            "target_identity": "sir-production",
            "transaction_id": "txn-1",
        },
        sort_keys=True,
    )

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
    ) -> str:
        del remote_args, label
        raise hemma_deploy_and_verify.CommandExecutionError(
            "remote pdm run prod-recreate private services failed (exit=3).",
            returncode=3,
            stdout=f"some compose output\n{claim_line}\n",
        )

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    with pytest.raises(hemma_deploy_and_verify.RecreateClaimOutcome) as excinfo:
        hemma_deploy_and_verify._remote_recreate_service("verified-revision")

    assert excinfo.value.outcome == "queued"
    assert excinfo.value.reason == "queued position 1 awaiting huleedu-research"
    assert excinfo.value.exit_code == 3


def test_remote_recreate_service_propagates_refusal_without_transaction_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claim_line = json.dumps(
        {
            "outcome": "refused",
            "reason": "claim sir-production is suspended",
            "target_identity": "sir-production",
            "transaction_id": None,
        },
        sort_keys=True,
    )

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
    ) -> str:
        del remote_args, label
        raise hemma_deploy_and_verify.CommandExecutionError(
            "remote pdm run prod-recreate private services failed (exit=1).",
            returncode=1,
            stdout=f"{claim_line}\n",
        )

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)

    with pytest.raises(hemma_deploy_and_verify.RecreateClaimOutcome) as excinfo:
        hemma_deploy_and_verify._remote_recreate_service("verified-revision")

    assert excinfo.value.outcome == "refused"
    assert excinfo.value.reason == "claim sir-production is suspended"
    assert excinfo.value.exit_code == 1


def test_remote_recreate_service_injects_verified_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
    ) -> str:
        del label
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
    ) -> str:
        del remote_args, label
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
        ("queued_recreate", "failed"),
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
        "bash",
        "scripts/devops/verify-hemma-v2-conversions.sh",
        "--remote",
        "--lane",
        "host",
        "--output-root",
        "build/verification/hemma-deploy-verify/v2-smoke",
    ]
    metrics = ["curl", "-fsS", "http://127.0.0.1:28085/metrics"]

    def reject_local(
        command: list[str],
        *,
        label: str,
        env: dict[str, str] | None = None,
    ) -> str:
        raise AssertionError(f"unexpected local/publication command: {command!r}")

    def fake_run_remote(
        remote_args: list[str],
        *,
        label: str,
    ) -> str:
        remote_calls.append(remote_args)
        if remote_args == pull:
            if scenario == "pull_failure":
                raise hemma_deploy_and_verify.CommandExecutionError("pull failed")
            return ""
        if remote_args == revision:
            return "wrong\n" if scenario == "revision_mismatch" else "abc\n"
        if remote_args == recreate:
            if scenario == "queued_recreate":
                raise hemma_deploy_and_verify.CommandExecutionError(
                    "remote pdm run prod-recreate private services failed (exit=3).",
                    returncode=3,
                    stdout=json.dumps(
                        {
                            "outcome": "queued",
                            "reason": "queued position 1 awaiting huleedu-research",
                            "target_identity": "sir-production",
                            "transaction_id": "txn-queued",
                        },
                        sort_keys=True,
                    ),
                )
            return ""
        if remote_args == readyz:
            return json.dumps(
                {
                    "ready": True,
                    "service_revision": "wrong" if scenario == "service_mismatch" else "abc",
                }
            )
        if remote_args == smoke:
            if scenario == "smoke_failure":
                raise hemma_deploy_and_verify.CommandExecutionError("gpu_not_available")
            return ""
        if remote_args == metrics:
            return 'jobs{job_id="unsafe"} 1\n' if scenario == "unsafe_metrics" else "# safe\n"
        raise AssertionError(f"unexpected public/publication/remote command: {remote_args!r}")

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_command", reject_local)
    monkeypatch.setattr(hemma_deploy_and_verify, "_run_remote", fake_run_remote)
    report, claim_outcome = hemma_deploy_and_verify.execute_workflow(
        hemma_deploy_and_verify.WorkflowSettings(
            expected_revision="abc",
            lane="host",
            service_url="http://127.0.0.1:28085",
            output_root=tmp_path,
        )
    )

    assert report["status"] == expected_status
    assert_private_artifacts(tmp_path, report)
    expected_calls = [pull, revision, recreate, readyz, smoke, metrics]
    count = {
        "pull_failure": 1,
        "revision_mismatch": 2,
        "queued_recreate": 3,
        "service_mismatch": 4,
    }.get(scenario, 6)
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
    if scenario == "queued_recreate":
        assert claim_outcome is not None
        assert claim_outcome.outcome == "queued"
        assert claim_outcome.exit_code == 3
        assert report["failure"] == "queued position 1 awaiting huleedu-research"
    else:
        assert claim_outcome is None
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
    ) -> str:
        raise hemma_deploy_and_verify.CommandExecutionError(
            f"resolve expected revision failed for {command!r}"
        )

    monkeypatch.setattr(hemma_deploy_and_verify, "_run_command", fake_run_command)
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
    assert "resolve expected revision failed" in report["failure"]
    assert_private_artifacts(tmp_path, report)
    assert json.loads((tmp_path / "readyz.json").read_text()) == {}
    assert (tmp_path / "metrics.prom").read_text() == "# metrics not captured\n"
    assert (tmp_path / "remote_head.txt").read_text() == "unavailable\n"


@pytest.mark.parametrize(
    "outcome,reason,expected_code",
    [
        ("queued", "queued position 1 awaiting huleedu-research", 3),
        ("refused", "claim sir-production is suspended", 1),
    ],
)
def test_main_prints_claim_reason_and_returns_claim_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
    reason: str,
    expected_code: int,
) -> None:
    settings = hemma_deploy_and_verify.WorkflowSettings(
        expected_revision="abc",
        lane="host",
        service_url="http://127.0.0.1:28085",
        output_root=tmp_path,
    )
    report: dict[str, object] = {"status": "failed", "failure": reason}
    claim = hemma_deploy_and_verify.RecreateClaimOutcome(outcome=outcome, reason=reason)

    monkeypatch.setattr(hemma_deploy_and_verify, "_load_workflow_settings", lambda args: settings)
    monkeypatch.setattr(
        hemma_deploy_and_verify,
        "execute_workflow",
        lambda resolved: (report, claim),
    )

    assert (
        hemma_deploy_and_verify.main(
            [
                "--expected-revision",
                "abc",
                "--output-root",
                str(tmp_path),
            ]
        )
        == expected_code
    )
    captured = capsys.readouterr()
    assert reason in captured.err
    assert (tmp_path / "report.md").as_posix() in captured.out
