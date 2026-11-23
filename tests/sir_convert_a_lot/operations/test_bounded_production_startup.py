"""Provenance and startup-selection boundaries for bounded production startup."""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.devops import bounded_production_startup as startup
from scripts.sir_convert_a_lot.devops import bounded_production_startup_runtime as runtime
from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    RuntimeSnapshot,
    StartupFailure,
)
from tests.sir_convert_a_lot.operations.bounded_startup_fakes import (
    APPLICATION_IMAGE_ID,
    DEPENDENCY_IMAGE,
    HEAD,
    FakeRunner,
    before_snapshot,
    container,
)


def _wrapped_up_boundary(command: list[str]) -> None:
    assert command[0:2] == ["agent-secrets", "run"]
    assert command[2:4] == ["--set", "sir-convert-a-lot-prod"]
    payload = command[command.index("--") + 1 :]
    assert "compose" in payload
    assert "up" in payload
    for flag in ("-d", "--no-deps", "--no-build"):
        assert flag in payload
    assert payload.count("-f") == 2
    assert "compose.yaml" in payload
    assert "compose.secrets.yaml" in payload
    assert "start" not in payload


def test_stale_api_recreates_only_api_and_preserves_current_worker_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_DOCKER_USE_SUDO", raising=False)
    runner = FakeRunner()
    before = before_snapshot(api_image_id="sha256:stale")
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

    assert len(runner.calls) == 1
    command = runner.calls[0][0]
    _wrapped_up_boundary(command)
    assert "--force-recreate" in command
    assert command[-1] == startup.API_SERVICE
    assert runner.calls[0][1] == environment


def test_wrapped_up_under_sudo_preserves_agent_secrets_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCKER_USE_SUDO", "1")
    runner = FakeRunner()
    before = before_snapshot(api_image_id="sha256:stale")
    environment = startup._compose_environment(head=HEAD, dependency_image=DEPENDENCY_IMAGE)

    startup._start_selected(
        runner,
        before=before,
        application_image_id=APPLICATION_IMAGE_ID,
        environment=environment,
    )

    assert len(runner.calls) == 1
    command = runner.calls[0][0]
    _wrapped_up_boundary(command)
    bash_index = command.index("bash", command.index("--"))
    child_command = command[bash_index + 2]
    assert child_command.startswith("exec sudo -n --preserve-env=")
    assert "AGENT_SECRETS_VARIABLES" in child_command
    assignments = command[command.index("env") + 1 : command.index("docker")]
    assert f"SIR_CONVERT_A_LOT_SERVICE_REVISION={HEAD}" in assignments
    assert all(assignment.count("=") == 1 for assignment in assignments)
    assert runner.calls[0][1] == environment


def test_absent_api_and_worker_are_created_through_wrapped_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_DOCKER_USE_SUDO", raising=False)
    runner = FakeRunner()
    before = before_snapshot(worker_status=None)
    before.containers[startup.API_SERVICE] = container(
        startup.API_SERVICE,
        status=None,
        image_id=None,
    )

    startup._start_selected(
        runner,
        before=before,
        application_image_id=APPLICATION_IMAGE_ID,
        environment={},
    )

    commands = [call[0] for call in runner.calls]
    assert len(commands) == 2
    for command in commands:
        _wrapped_up_boundary(command)
    assert commands[0][-1] == startup.API_SERVICE
    assert "--force-recreate" in commands[0]
    assert commands[1][-1] == startup.WORKER_SERVICE
    assert "--force-recreate" not in commands[1]


@pytest.mark.parametrize("worker_status", ["created", "exited"])
def test_existing_stopped_containers_start_exact_containers_without_compose(
    monkeypatch: pytest.MonkeyPatch,
    worker_status: str,
) -> None:
    monkeypatch.delenv("SIR_CONVERT_A_LOT_DOCKER_USE_SUDO", raising=False)
    runner = FakeRunner()

    startup._start_selected(
        runner,
        before=before_snapshot(worker_status=worker_status),
        application_image_id=APPLICATION_IMAGE_ID,
        environment={},
    )

    commands = [call[0] for call in runner.calls]
    assert [command[:2] for command in commands] == [["docker", "start"], ["docker", "start"]]
    assert [command[-1] for command in commands] == [
        startup.API_SERVICE,
        startup.WORKER_SERVICE,
    ]
    for command in commands:
        assert "compose" not in command
        assert "-f" not in command
        assert "agent-secrets" not in command


def test_stopped_containers_start_exact_containers_under_sudo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DOCKER_USE_SUDO", "1")
    runner = FakeRunner()

    startup._start_selected(
        runner,
        before=before_snapshot(worker_status="exited"),
        application_image_id=APPLICATION_IMAGE_ID,
        environment={},
    )

    commands = [call[0] for call in runner.calls]
    assert [command[:4] for command in commands] == [
        ["sudo", "-n", "docker", "start"],
        ["sudo", "-n", "docker", "start"],
    ]
    assert [command[-1] for command in commands] == [
        startup.API_SERVICE,
        startup.WORKER_SERVICE,
    ]


@pytest.mark.parametrize(
    "worker_status",
    ["paused", "restarting", "removing", "dead", "unrecognized"],
)
def test_transitional_or_unknown_worker_state_refuses_before_selected_mutation(
    worker_status: str,
) -> None:
    runner = FakeRunner()

    with pytest.raises(StartupFailure, match="state is not admissible"):
        startup._start_selected(
            runner,
            before=before_snapshot(worker_status=worker_status),
            application_image_id=APPLICATION_IMAGE_ID,
            environment={},
        )

    assert runner.calls == []


def test_changed_current_worker_identity_refuses_after_selected_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = before_snapshot()
    monkeypatch.setattr(
        startup,
        "inspect_container",
        lambda runner, name: container(name, identity="replaced-worker-id"),
    )

    with pytest.raises(StartupFailure, match="container identity changed"):
        startup._assert_running_worker_identity_preserved(
            FakeRunner(),
            before=before,
            application_image_id=APPLICATION_IMAGE_ID,
        )


@pytest.mark.parametrize("worker_status", ["running", "created", "exited"])
def test_stale_existing_worker_refuses_with_redeploy_remedy(worker_status: str) -> None:
    runner = FakeRunner()

    with pytest.raises(StartupFailure, match="stale application provenance") as captured:
        startup._start_selected(
            runner,
            before=before_snapshot(
                worker_image_id="sha256:stale",
                worker_status=worker_status,
            ),
            application_image_id=APPLICATION_IMAGE_ID,
            environment={},
        )

    assert "prod-recreate" in str(captured.value)
    assert runner.calls == []


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
    excluded = container(next(iter(startup.EXPLICIT_EXCLUDED_NAMES)))
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
            container(name, identity="changed")
            if failure == "changed-container"
            else container(name, state_record='{"Status":"exited"}')
            if failure == "changed-lifecycle"
            else container(name, restart_policy="unless-stopped")
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
        runtime.assert_preserved(FakeRunner(), before=before, selected_names=startup.SELECTED_NAMES)


def test_excluded_preservation_accepts_health_history_churn_with_unchanged_stable_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    excluded = container(next(iter(startup.EXPLICIT_EXCLUDED_NAMES)))
    before = RuntimeSnapshot(
        containers={excluded.name: excluded},
        excluded_names=frozenset((excluded.name,)),
        volumes={"prod-data": "before-volume"},
    )
    monkeypatch.setattr(runtime, "container_names", lambda runner: {excluded.name})
    monkeypatch.setattr(runtime, "inspect_container", lambda runner, name: excluded)
    monkeypatch.setattr(runtime, "inspect_volume", lambda runner, name: "before-volume")

    runtime.assert_preserved(FakeRunner(), before=before, selected_names=startup.SELECTED_NAMES)
