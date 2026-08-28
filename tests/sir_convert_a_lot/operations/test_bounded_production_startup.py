"""Behavioral boundaries for the bounded Hemma production startup coordinator."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import TracebackType

import pytest

from scripts.sir_convert_a_lot.devops import bounded_production_startup as startup
from scripts.sir_convert_a_lot.devops import bounded_production_startup_runtime as runtime
from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    CommandResult,
    CommandRunner,
    ContainerSnapshot,
    RuntimeSnapshot,
    StartupFailure,
)

HEAD = "a" * 40
DEPENDENCY_IMAGE_HASH = "dependency-image-hash"
DEPENDENCY_IMAGE = f"sir-convert-a-lot-deps-rocm:{DEPENDENCY_IMAGE_HASH}"
APPLICATION_IMAGE_ID = "sha256:application"


class _Runner(CommandRunner):
    def __init__(self, *, deadline: float = 10.0, api_port: str = "", gpu_probe: str = "") -> None:
        super().__init__(project_root=Path("."), deadline=deadline)
        self.calls: list[tuple[list[str], dict[str, str] | None, bool]] = []
        self.api_port = api_port
        self.gpu_probe = gpu_probe

    def run(
        self,
        command: Sequence[str],
        *,
        environment: Mapping[str, str] | None = None,
        dependency_boundary: bool = False,
    ) -> CommandResult:
        copied_environment = None if environment is None else dict(environment)
        command_vector = list(command)
        self.calls.append((command_vector, copied_environment, dependency_boundary))
        if command_vector == ["docker", "port", startup.API_SERVICE, "8085/tcp"]:
            return CommandResult(stdout=self.api_port, stderr="")
        if "/app/.venv/bin/python" in command_vector:
            return CommandResult(stdout=self.gpu_probe, stderr="")
        return CommandResult(stdout="", stderr="")


class _Response:
    def __init__(self, *, status: int, body: str) -> None:
        self.status = status
        self.body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback

    def read(self) -> bytes:
        return self.body.encode("utf-8")


def _container(
    name: str,
    *,
    identity: str = "container-id",
    status: str | None = "running",
    image_id: str = APPLICATION_IMAGE_ID,
    restart_policy: str = "no",
    state_record: str = '{"Status":"running"}',
) -> ContainerSnapshot:
    return ContainerSnapshot(
        name=name,
        identity=identity,
        status=status,
        state_record=state_record,
        image_id=image_id,
        configured_image=f"sir-convert-a-lot-runtime:{HEAD}",
        restart_policy=restart_policy,
    )


def _before(
    *,
    api_image_id: str = APPLICATION_IMAGE_ID,
    worker_image_id: str = APPLICATION_IMAGE_ID,
    worker_status: str | None = "running",
) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        containers={
            startup.API_SERVICE: _container(startup.API_SERVICE, image_id=api_image_id),
            startup.WORKER_SERVICE: _container(
                startup.WORKER_SERVICE,
                identity="current-worker-id",
                image_id=worker_image_id,
                status=worker_status,
            ),
        },
        excluded_names=frozenset(),
        volumes={},
    )


def test_stale_api_recreates_only_api_and_preserves_current_worker_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _Runner()
    before = _before(api_image_id="sha256:stale")
    environment = startup._compose_environment(head=HEAD, dependency_image=DEPENDENCY_IMAGE)
    monkeypatch.setattr(
        startup,
        "inspect_container",
        lambda runner, name: before.containers[name],
    )

    startup._start_selected(
        runner,
        before=before,
        application_image_id=APPLICATION_IMAGE_ID,
        environment=environment,
    )
    startup._assert_running_worker_identity_preserved(
        runner,
        before=before,
        application_image_id=APPLICATION_IMAGE_ID,
    )

    assert [call[0] for call in runner.calls] == [
        [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "up",
            "-d",
            "--no-deps",
            "--no-build",
            "--force-recreate",
            startup.API_SERVICE,
        ]
    ]


@pytest.mark.parametrize("worker_status", [None, "created", "exited"])
def test_absent_or_stopped_worker_starts_separately(worker_status: str | None) -> None:
    runner = _Runner()

    startup._start_selected(
        runner,
        before=_before(worker_status=worker_status),
        application_image_id=APPLICATION_IMAGE_ID,
        environment={},
    )

    assert [call[0][-1] for call in runner.calls] == [startup.API_SERVICE, startup.WORKER_SERVICE]
    assert "--no-deps" in runner.calls[1][0]
    assert "--no-build" in runner.calls[1][0]


@pytest.mark.parametrize(
    "worker_status",
    ["paused", "restarting", "removing", "dead", "unrecognized"],
)
def test_transitional_or_unknown_worker_state_refuses_before_selected_mutation(
    worker_status: str,
) -> None:
    runner = _Runner()

    with pytest.raises(StartupFailure, match="state is not admissible"):
        startup._start_selected(
            runner,
            before=_before(worker_status=worker_status),
            application_image_id=APPLICATION_IMAGE_ID,
            environment={},
        )

    assert runner.calls == []


def test_changed_current_worker_identity_refuses_after_selected_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _before()
    monkeypatch.setattr(
        startup,
        "inspect_container",
        lambda runner, name: _container(name, identity="replaced-worker-id"),
    )

    with pytest.raises(StartupFailure, match="container identity changed"):
        startup._assert_running_worker_identity_preserved(
            _Runner(),
            before=before,
            application_image_id=APPLICATION_IMAGE_ID,
        )


def test_stale_running_worker_refuses_before_selected_mutation() -> None:
    runner = _Runner()

    with pytest.raises(StartupFailure, match="stale application provenance"):
        startup._start_selected(
            runner,
            before=_before(worker_image_id="sha256:stale"),
            application_image_id=APPLICATION_IMAGE_ID,
            environment={},
        )

    assert runner.calls == []


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
    runner = _Runner(api_port="127.0.0.1:28085\n")
    seen_urls: list[str] = []

    def urlopen(url: str, *, timeout: float) -> _Response:
        assert timeout == 5.0
        seen_urls.append(url)
        return _Response(status=200, body=_ready_payload())

    monkeypatch.setattr(startup.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(startup.time, "monotonic", lambda: 0.0)

    startup._poll_ready(runner, head=HEAD)

    assert seen_urls == ["http://127.0.0.1:28085/readyz"]


def test_readiness_retries_transient_connection_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _Runner(deadline=10.0, api_port="127.0.0.1:28085\n")
    responses: list[OSError | _Response] = [
        ConnectionResetError(104, "Connection reset by peer"),
        _Response(status=200, body=_ready_payload()),
    ]

    def urlopen(url: str, *, timeout: float) -> _Response:
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
    runner = _Runner(deadline=10.0, api_port="127.0.0.1:28085\n")
    monkeypatch.setattr(
        startup.urllib.request,
        "urlopen",
        lambda url, timeout: _Response(status=status, body=payload),
    )
    monkeypatch.setattr(startup.time, "monotonic", lambda: next(times))

    with pytest.raises(StartupFailure, match="API readiness timed out") as captured:
        startup._poll_ready(runner, head=HEAD)

    assert captured.value.outcome == "timed_out"
    assert payload in str(captured.value)


def test_gpu_readiness_targets_only_worker_rocm_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _Runner(
        gpu_probe='{"available":true,"count":1,"rocm":"7.1","torch":"2.10.0+rocm7.1"}\n'
    )
    monkeypatch.setattr(startup, "_read_pinned_torch_version", lambda: "2.10.0+rocm7.1")

    startup._prove_gpu_readiness(runner)

    commands = [call[0] for call in runner.calls]
    assert commands[-1] == ["rocm-smi", "--showuse"]
    assert commands[:2] == [
        ["docker", "exec", startup.WORKER_SERVICE, "test", "-e", "/dev/kfd"],
        ["docker", "exec", startup.WORKER_SERVICE, "test", "-d", "/dev/dri"],
    ]
    assert all(command[2] == startup.WORKER_SERVICE for command in commands[:-1])
    assert "conversion" not in " ".join(" ".join(command) for command in commands).lower()
    assert "cpu fallback" not in " ".join(" ".join(command) for command in commands).lower()


def test_restart_update_and_inspection_require_no_for_both_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _Runner()
    inspected: list[str] = []

    def inspect_container(runner: _Runner, name: str) -> ContainerSnapshot:
        del runner
        inspected.append(name)
        return _container(name, restart_policy="no")

    monkeypatch.setattr(startup, "inspect_container", inspect_container)

    startup._apply_restart_truth(runner)

    assert runner.calls[0][0] == [
        "docker",
        "update",
        "--restart=no",
        startup.API_SERVICE,
        startup.WORKER_SERVICE,
    ]
    assert inspected == [startup.API_SERVICE, startup.WORKER_SERVICE]


@pytest.mark.parametrize(
    "failure",
    [
        "changed-container",
        "changed-lifecycle",
        "changed-restart",
        "changed-volume",
        "new-container",
    ],
)
def test_excluded_container_and_volume_identity_mismatches_fail(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    excluded = _container(next(iter(startup.EXPLICIT_EXCLUDED_NAMES)))
    before = RuntimeSnapshot(
        containers={excluded.name: excluded},
        excluded_names=frozenset((excluded.name,)),
        volumes={"prod-data": "before-volume"},
    )
    after_names = {excluded.name}
    if failure == "new-container":
        after_names.add("sir_convert_a_lot_new_excluded")
    monkeypatch.setattr(runtime, "container_names", lambda runner: after_names)
    monkeypatch.setattr(
        runtime,
        "inspect_container",
        lambda runner, name: (
            _container(name, identity="changed")
            if failure == "changed-container"
            else _container(name, state_record='{"Status":"exited"}')
            if failure == "changed-lifecycle"
            else _container(name, restart_policy="unless-stopped")
            if failure == "changed-restart"
            else excluded
        ),
    )
    monkeypatch.setattr(
        runtime,
        "inspect_volume",
        lambda runner, name: "changed-volume" if failure == "changed-volume" else "before-volume",
    )

    with pytest.raises(StartupFailure):
        runtime.assert_preserved(_Runner(), before=before, selected_names=startup.SELECTED_NAMES)


def test_excluded_preservation_accepts_health_history_churn_with_unchanged_stable_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    excluded = _container(next(iter(startup.EXPLICIT_EXCLUDED_NAMES)))
    before = RuntimeSnapshot(
        containers={excluded.name: excluded},
        excluded_names=frozenset((excluded.name,)),
        volumes={"prod-data": "before-volume"},
    )
    monkeypatch.setattr(runtime, "container_names", lambda runner: {excluded.name})
    monkeypatch.setattr(runtime, "inspect_container", lambda runner, name: excluded)
    monkeypatch.setattr(runtime, "inspect_volume", lambda runner, name: "before-volume")

    runtime.assert_preserved(_Runner(), before=before, selected_names=startup.SELECTED_NAMES)


def test_empty_gpu_probe_is_failed_outcome_with_one_terminal_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(startup, "_read_pinned_torch_version", lambda: "2.10.0+rocm7.1")

    def execute(project_root: Path) -> None:
        del project_root
        startup._prove_gpu_readiness(_Runner(gpu_probe=""))

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
