"""Readiness and terminal-outcome boundaries for bounded production startup."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import bounded_production_startup as startup
from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    ContainerSnapshot,
    StartupFailure,
)
from tests.sir_convert_a_lot.operations.bounded_startup_fakes import (
    HEAD,
    FakeResponse,
    FakeRunner,
    container,
)


def _ready_payload(**updates: str | bool) -> str:
    payload: dict[str, str | bool] = {
        "ready": True,
        "service_revision": HEAD,
        "expected_revision": HEAD,
        "service_profile": "prod",
        "expected_service_profile": "prod",
        "data_root": "/var/lib/sir-convert-a-lot/prod",
    }
    payload.update(updates)
    return json.dumps(payload)


def test_readiness_accepts_exact_200_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRunner(api_port="127.0.0.1:28085\n")
    seen_urls: list[str] = []

    def urlopen(url: str, *, timeout: float) -> FakeResponse:
        assert timeout == 5.0
        seen_urls.append(url)
        return FakeResponse(status=200, body=_ready_payload())

    monkeypatch.setattr(startup.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(startup.time, "monotonic", lambda: 0.0)

    startup._poll_ready(runner, head=HEAD)

    assert seen_urls == ["http://127.0.0.1:28085/readyz"]


def test_readiness_retries_transient_connection_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRunner(deadline=10.0, api_port="127.0.0.1:28085\n")
    responses: list[OSError | FakeResponse] = [
        ConnectionResetError(104, "Connection reset by peer"),
        FakeResponse(status=200, body=_ready_payload()),
    ]

    def urlopen(url: str, *, timeout: float) -> FakeResponse:
        del url, timeout
        response = responses.pop(0)
        if isinstance(response, OSError):
            raise response
        return response

    monkeypatch.setattr(startup.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(startup.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(startup.time, "sleep", lambda seconds: None)

    startup._poll_ready(runner, head=HEAD)

    assert responses == []


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (503, _ready_payload()),
        (200, _ready_payload(ready=False)),
        (200, _ready_payload(service_revision="old")),
        (200, _ready_payload(expected_service_profile="dev")),
        (200, _ready_payload(data_root="/tmp/data")),
    ],
)
def test_readiness_rejects_every_nonexact_payload_with_last_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    payload: str,
) -> None:
    times = iter((0.0, 10.0))
    runner = FakeRunner(deadline=10.0, api_port="127.0.0.1:28085\n")
    monkeypatch.setattr(
        startup.urllib.request,
        "urlopen",
        lambda url, timeout: FakeResponse(status=status, body=payload),
    )
    monkeypatch.setattr(startup.time, "monotonic", lambda: next(times))

    with pytest.raises(StartupFailure, match="API readiness timed out") as captured:
        startup._poll_ready(runner, head=HEAD)

    assert captured.value.outcome == "timed_out"
    assert payload in str(captured.value)


def test_gpu_readiness_targets_only_worker_rocm_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRunner(
        gpu_probe='{"available":true,"count":1,"rocm":"7.1","torch":"2.10.0+rocm7.1"}\n'
    )
    monkeypatch.setattr(startup, "_read_pinned_torch_version", lambda: "2.10.0+rocm7.1")

    startup._prove_gpu_readiness(runner)

    commands = [call[0] for call in runner.calls]
    assert commands[-1] == ["rocm-smi", "--showuse"]
    for command in commands[:-1]:
        assert command[command.index("exec") + 1] == startup.WORKER_SERVICE
    assert commands[0][-3:] == ["test", "-e", "/dev/kfd"]
    assert commands[1][-3:] == ["test", "-d", "/dev/dri"]
    joined = " ".join(" ".join(command) for command in commands)
    assert "conversion" not in joined.lower()
    assert "cpu fallback" not in joined.lower()


def test_restart_update_and_inspection_require_no_for_both_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner()
    inspected: list[str] = []

    def inspect_container(runner: FakeRunner, name: str) -> ContainerSnapshot:
        del runner
        inspected.append(name)
        return container(name, restart_policy="no")

    monkeypatch.setattr(startup, "inspect_container", inspect_container)

    startup._apply_restart_truth(runner)

    update_command = runner.calls[0][0]
    assert update_command[-3:] == [
        "--restart=no",
        startup.API_SERVICE,
        startup.WORKER_SERVICE,
    ]
    assert "update" in update_command
    assert inspected == [startup.API_SERVICE, startup.WORKER_SERVICE]


def test_empty_gpu_probe_is_failed_outcome_with_one_terminal_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(startup, "_read_pinned_torch_version", lambda: "2.10.0+rocm7.1")

    def execute(project_root: Path) -> None:
        del project_root
        startup._prove_gpu_readiness(FakeRunner(gpu_probe=""))

    monkeypatch.setattr(startup, "execute", execute)

    assert startup.main() == 1
    captured = capsys.readouterr()
    assert captured.out == "outcome=failed\n"
    assert "returned no payload" in captured.err


@pytest.mark.parametrize("outcome", [None, "dependency_unhealthy", "timed_out", "failed"])
def test_main_emits_one_terminal_outcome_and_only_succeeds_with_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str | None,
) -> None:
    def execute(project_root: Path) -> None:
        del project_root
        if outcome is not None:
            raise StartupFailure("diagnostic", outcome=outcome)

    monkeypatch.setattr(startup, "execute", execute)

    result = startup.main()
    captured = capsys.readouterr()
    expected = "succeeded" if outcome is None else outcome

    assert result == (0 if expected == "succeeded" else 1)
    assert captured.out == f"outcome={expected}\n"
    assert captured.err == ("" if outcome is None else "prod-start-bounded: diagnostic\n")
