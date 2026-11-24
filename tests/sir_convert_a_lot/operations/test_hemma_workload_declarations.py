import json
import pwd
import subprocess
from pathlib import Path

import pytest
from repository_governance.hemma_workload import (
    ClaimKind,
    ExpectedState,
    LedgerStore,
    TerminalOutcome,
    WorkloadController,
    WorkloadTransactionError,
    products,
)
from repository_governance.hemma_workload.products import WORKER_COMMAND

from scripts.sir_convert_a_lot.devops import hemma_workload, hemma_workload_runtime


class QueueRunner:
    def __init__(self, results: list[hemma_workload.CommandResult]) -> None:
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
        self.commands.append(argv)
        if not self.results:
            raise AssertionError(f"unexpected command: {argv}")
        return self.results.pop(0)


class StatefulRunner:
    def __init__(self) -> None:
        self.running = {hemma_workload.STT_CONTAINER}
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
        self.commands.append(argv)
        if argv == (*hemma_workload.DOCKER_COMMAND, "ps", "--format", "{{.Names}}"):
            return hemma_workload.CommandResult(
                0, "".join(f"{name}\n" for name in sorted(self.running))
            )
        if argv == ("rocm-smi", "--showpids", "--json"):
            return hemma_workload.CommandResult(0, "")
        if argv[:4] == (*hemma_workload.DOCKER_COMMAND, "top"):
            return hemma_workload.CommandResult(0, "PID\n")
        if argv[:4] == (*hemma_workload.DOCKER_COMMAND, "stop"):
            self.running.remove(argv[4])
            return hemma_workload.CommandResult(0, "")
        if argv[:4] == (*hemma_workload.DOCKER_COMMAND, "start"):
            self.running.add(argv[4])
            return hemma_workload.CommandResult(0, "")
        if argv == ("pdm", "run", "prod-workload-start"):
            self.running.update(hemma_workload.PRODUCTION_CONTAINERS)
            return hemma_workload.CommandResult(0, "outcome=succeeded\n")
        if argv[:3] == ("pdm", "run", "prod-stop"):
            self.running.difference_update(hemma_workload.PRODUCTION_CONTAINERS)
            return hemma_workload.CommandResult(0, "")
        if argv[:6] == (
            *hemma_workload.DOCKER_COMMAND,
            "inspect",
            "--format",
            hemma_workload.CONTAINER_STATE_FORMAT,
        ):
            state = "running" if argv[6] in self.running else "exited"
            restart = (
                hemma_workload.PRODUCTION_RESTART_POLICY
                if argv[6] in hemma_workload.PRODUCTION_CONTAINERS
                else hemma_workload.SIDECAR_RESTART_POLICY
            )
            return hemma_workload.CommandResult(0, f"{state}\t{restart}\n")
        if argv[:6] == (
            *hemma_workload.DOCKER_COMMAND,
            "inspect",
            "--format",
            hemma_workload.CONTAINER_HEALTH_FORMAT,
        ):
            return hemma_workload.CommandResult(0, "healthy\n")
        if argv[:6] == (
            *hemma_workload.DOCKER_COMMAND,
            "inspect",
            "--format",
            "{{.Image}}",
        ):
            if argv[6] in (*hemma_workload.PRODUCTION_CONTAINERS, hemma_workload.STT_CONTAINER):
                return hemma_workload.CommandResult(0, "sha256:existing\n")
            return hemma_workload.CommandResult(1, "No such object")
        raise AssertionError(f"unexpected command: {argv}")


def _declaration_payload(
    identity: str,
    *,
    claims: list[str],
    kind: str | None,
    dependencies: list[str] | None = None,
    conflicts: list[str] | None = None,
) -> dict[str, object]:
    return {
        "identity": identity,
        "services": [identity],
        "dependencies": dependencies or [],
        "claims": claims,
        "conflicts": conflicts or [],
        "outcomes": ["succeeded"],
        "kind": kind,
    }


SIBLING_DECLARATIONS: dict[str, tuple[dict[str, object], ...]] = {
    "huleedu": (
        _declaration_payload("hule-prod-core", claims=["hule:prod-core"], kind=None),
        _declaration_payload(
            "hule-prod-rst-parser",
            claims=["gpu:amdgpu"],
            kind="service",
            dependencies=["hule-prod-core"],
        ),
        _declaration_payload("hule-offload", claims=["gpu:amdgpu"], kind="batch"),
        _declaration_payload("hule-transformer-train", claims=["gpu:amdgpu"], kind="batch"),
        _declaration_payload("hule-vision-crop", claims=["gpu:amdgpu"], kind="batch"),
    ),
    "skriptoteket": (
        _declaration_payload("skriptoteket-web", claims=["product:skriptoteket"], kind=None),
        _declaration_payload(
            "skriptoteket-worker",
            claims=["product:skriptoteket"],
            kind=None,
            dependencies=["skriptoteket-web"],
        ),
    ),
    "qwen": (
        _declaration_payload(
            "qwen3.8-27b-q8kl-mtp",
            claims=["gpu:amdgpu"],
            kind="interactive",
            conflicts=[
                "hule-prod-rst-parser",
                "hule-offload",
                "hule-transformer-train",
                "hule-vision-crop",
                "sir-production",
                "sir-stt-sidecar",
            ],
        ),
    ),
}


class CompositionRunner:
    """Fake sibling product-worker runner returning fixed published declarations."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        argv: tuple[str, ...],
        *,
        timeout: float,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> hemma_workload.CommandResult:
        self.calls.append(argv)
        assert argv[:5] == WORKER_COMMAND
        assert argv[6] == "declarations"
        owner = argv[5]
        payload = {"declarations": list(SIBLING_DECLARATIONS[owner])}
        return hemma_workload.CommandResult(0, json.dumps(payload))


def _composition_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = tmp_path / "hemma-workload.toml"
    settings.write_text(
        "declaration_timeout_seconds = 60.0\n"
        "[operation_timeout_seconds]\n"
        + "".join(
            f'"{identity}" = 60.0\n'
            for declarations in SIBLING_DECLARATIONS.values()
            for declaration in declarations
            for identity in [declaration["identity"]]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(products, "role_resource", lambda relative: settings)
    monkeypatch.setattr(
        products,
        "product_spec",
        lambda name: products.ProductSpec(name, tmp_path / name),
    )


def _composition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CompositionRunner:
    _composition_settings(tmp_path, monkeypatch)
    return CompositionRunner()


def test_sir_declarations_publish_service_kinds() -> None:
    declarations = hemma_workload.sir_workload_declarations(
        runner=QueueRunner([]), project_root=Path("/srv/sir")
    )

    assert [item.identity for item in declarations] == [
        hemma_workload.PRODUCTION_WORKLOAD_ID,
        hemma_workload.STT_WORKLOAD_ID,
    ]
    for declaration in declarations:
        assert declaration.kind is ClaimKind.SERVICE
        assert declaration.resource_claims == frozenset({"gpu:amdgpu"})


def test_registry_composes_host_declarations_with_sir_kinds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_runner = _composition(tmp_path, monkeypatch)
    registry = hemma_workload.sir_workload_registry(
        runner=QueueRunner([]),
        product_runner=product_runner,
        project_root=Path("/srv/sir"),
    )

    assert registry.host_identity == "hemma"
    expected_identities = {
        declaration["identity"]
        for declarations in SIBLING_DECLARATIONS.values()
        for declaration in declarations
    }
    assert registry.identities == frozenset(
        {
            hemma_workload.PRODUCTION_WORKLOAD_ID,
            hemma_workload.STT_WORKLOAD_ID,
            *expected_identities,
        }
    )
    assert {call[5] for call in product_runner.calls} == {"huleedu", "skriptoteket", "qwen"}

    production = registry.declaration(hemma_workload.PRODUCTION_WORKLOAD_ID)
    stt = registry.declaration(hemma_workload.STT_WORKLOAD_ID)
    assert production.service_identities == (
        hemma_workload.API_CONTAINER,
        hemma_workload.GPU_WORKER_CONTAINER,
    )
    assert stt.service_identities == (hemma_workload.STT_CONTAINER,)
    for declaration in (production, stt):
        assert declaration.kind is ClaimKind.SERVICE
        assert declaration.resource_claims == frozenset({"gpu:amdgpu"})
        assert declaration.dependencies == ()
        assert declaration.accepted_terminal_outcomes == frozenset({TerminalOutcome.SUCCEEDED})
    gpu_products = {
        "hule-offload",
        "hule-transformer-train",
        "hule-vision-crop",
        "qwen3.8-27b-q8kl-mtp",
    }
    assert production.conflicts == frozenset({hemma_workload.STT_WORKLOAD_ID, *gpu_products})
    assert stt.conflicts == frozenset({hemma_workload.PRODUCTION_WORKLOAD_ID, *gpu_products})
    assert isinstance(production.adapter, hemma_workload.ProductionWorkloadAdapter)
    assert isinstance(
        registry.declaration("hule-prod-rst-parser").adapter,
        products.ProductWorkloadAdapter,
    )


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [
        (0, "detail\noutcome=succeeded\n", TerminalOutcome.SUCCEEDED),
        (1, "outcome=timed_out\n", TerminalOutcome.TIMED_OUT),
        (1, "outcome=dependency_unhealthy\n", TerminalOutcome.DEPENDENCY_UNHEALTHY),
        (1, "outcome=refused\n", TerminalOutcome.REFUSED),
        (1, "outcome=failed\n", TerminalOutcome.FAILED),
    ],
)
def test_production_start_uses_bounded_command_and_maps_terminal_outcome(
    returncode: int, stdout: str, expected: TerminalOutcome
) -> None:
    runner = QueueRunner([hemma_workload.CommandResult(returncode, stdout)])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    result = adapter.start()

    assert result.outcome is expected
    assert runner.commands == [("pdm", "run", "prod-workload-start")]
    assert "--build" not in runner.commands[0]


def _operator_root_worker(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sudo_user: str | None = "operator",
    sudo_uid: str | None = None,
) -> None:
    monkeypatch.setattr(hemma_workload.os, "geteuid", lambda: 0)
    if sudo_user is None:
        monkeypatch.delenv("SUDO_USER", raising=False)
    else:
        monkeypatch.setenv("SUDO_USER", sudo_user)
    if sudo_uid is None:
        monkeypatch.delenv("SUDO_UID", raising=False)
    else:
        monkeypatch.setenv("SUDO_UID", sudo_uid)
    entry = pwd.struct_passwd(("operator", "x", 1000, 1000, "", "/home/operator", "/bin/bash"))
    monkeypatch.setattr(hemma_workload.pwd, "getpwnam", lambda name: entry)
    monkeypatch.setattr(hemma_workload.pwd, "getpwuid", lambda uid: entry)


def test_root_worker_runs_bounded_startup_as_operator_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    runner = QueueRunner([hemma_workload.CommandResult(0, "outcome=succeeded\n")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start().outcome is TerminalOutcome.SUCCEEDED
    command = runner.commands[0]
    assert command[:4] == ("sudo", "-n", "-u", "operator")
    assert command[4] == "env"
    assert command[5].startswith("PATH=/home/operator/.local/bin:")
    assert command[-3:] == ("pdm", "run", "prod-workload-start")


def test_root_worker_falls_back_to_sudo_uid_for_operator_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch, sudo_user=None, sudo_uid="1000")
    runner = QueueRunner([hemma_workload.CommandResult(0, "outcome=succeeded\n")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands[0][:4] == ("sudo", "-n", "-u", "operator")


def test_root_worker_runs_production_stop_as_operator_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch)
    runner = QueueRunner([hemma_workload.CommandResult(0, "")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.stop().outcome is TerminalOutcome.SUCCEEDED
    command = runner.commands[0]
    assert command[:3] == ("sudo", "-n", "-u")
    assert command[-5:-3] == ("pdm", "run")
    assert command[-3:] == (
        "prod-stop",
        hemma_workload.GPU_WORKER_CONTAINER,
        hemma_workload.API_CONTAINER,
    )


def test_root_worker_without_operator_identity_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch, sudo_user=None)
    monkeypatch.setattr(
        hemma_workload.pwd,
        "getpwnam",
        lambda name: pytest.fail("operator lookup without SUDO_USER"),
    )
    runner = QueueRunner([])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start().outcome is TerminalOutcome.FAILED
    assert adapter.stop().outcome is TerminalOutcome.FAILED
    assert runner.commands == []


@pytest.mark.parametrize(
    "stdout",
    ["", "outcome=succeeded\noutcome=succeeded\n", "outcome=succeeded\ntrailing\n", "noise\n"],
)
def test_production_start_refuses_nonterminal_or_ambiguous_outcome(stdout: str) -> None:
    adapter = hemma_workload.ProductionWorkloadAdapter(
        QueueRunner([hemma_workload.CommandResult(0, stdout)]), Path("/srv/sir")
    )

    assert adapter.start().outcome is TerminalOutcome.FAILED


def test_host_command_timeout_exceeds_task04_bounded_startup_timeout() -> None:
    assert (
        hemma_workload_runtime.HOST_COMMAND_TIMEOUT_SECONDS > hemma_workload.TOTAL_TIMEOUT_SECONDS
    )


def test_production_stop_uses_only_named_worker_and_api() -> None:
    runner = QueueRunner([hemma_workload.CommandResult(0, "")])
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.stop().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands == [
        (
            "pdm",
            "run",
            "prod-stop",
            hemma_workload.GPU_WORKER_CONTAINER,
            hemma_workload.API_CONTAINER,
        )
    ]
    assert "--build" not in runner.commands[0]


def test_production_status_requires_exact_group_and_restart_no() -> None:
    mixed = QueueRunner(
        [
            hemma_workload.CommandResult(0, "running\tno\n"),
            hemma_workload.CommandResult(0, "exited\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(mixed, Path("/srv/sir"))
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.REFUSED

    running = QueueRunner(
        [
            hemma_workload.CommandResult(0, "running\tno\n"),
            hemma_workload.CommandResult(0, "running\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(running, Path("/srv/sir"))
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.SUCCEEDED

    wrong_restart = QueueRunner(
        [
            hemma_workload.CommandResult(0, "running\tunless-stopped\n"),
            hemma_workload.CommandResult(0, "running\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(wrong_restart, Path("/srv/sir"))
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.FAILED

    stopped_wrong_restart = QueueRunner(
        [
            hemma_workload.CommandResult(0, "exited\tunless-stopped\n"),
            hemma_workload.CommandResult(0, "exited\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(stopped_wrong_restart, Path("/srv/sir"))
    assert adapter.status(ExpectedState.STOPPED).outcome is TerminalOutcome.FAILED


def test_production_status_refuses_unknown_container_state() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "unknown\tno\n"),
            hemma_workload.CommandResult(0, "running\tno\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.REFUSED


def test_production_readiness_reuses_task04_api_and_worker_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        hemma_workload,
        "_repository_head",
        lambda runner: "a" * 40,
    )
    monkeypatch.setattr(
        hemma_workload,
        "_poll_ready",
        lambda runner, *, head, docker_prefix: calls.append(
            ("api", f"{head}:{' '.join(docker_prefix)}")
        ),
    )
    monkeypatch.setattr(
        hemma_workload,
        "_prove_gpu_readiness",
        lambda runner, *, docker_prefix: calls.append(("worker", " ".join(docker_prefix))),
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(QueueRunner([]), Path("/srv/sir"))

    assert adapter.readiness().outcome is TerminalOutcome.SUCCEEDED
    privileged_docker = " ".join(hemma_workload.DOCKER_COMMAND)
    assert calls == [
        ("api", f"{'a' * 40}:{privileged_docker}"),
        ("worker", privileged_docker),
    ]


def test_production_operations_normalize_subprocess_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TimeoutRunner:
        def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
            raise subprocess.TimeoutExpired(argv, 1)

    adapter = hemma_workload.ProductionWorkloadAdapter(TimeoutRunner(), Path("/srv/sir"))
    assert adapter.start().outcome is TerminalOutcome.TIMED_OUT
    assert adapter.stop().outcome is TerminalOutcome.TIMED_OUT
    assert adapter.status(ExpectedState.RUNNING).outcome is TerminalOutcome.TIMED_OUT

    monkeypatch.setattr(
        hemma_workload,
        "_repository_head",
        lambda bounded: (_ for _ in ()).throw(subprocess.TimeoutExpired("git", 1)),
    )
    assert adapter.readiness().outcome is TerminalOutcome.TIMED_OUT


def test_controller_uses_public_provider_and_owner_state_constants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = hemma_workload.sir_workload_controller(
        runner=QueueRunner([]),
        product_runner=_composition(tmp_path, monkeypatch),
        project_root=Path("/srv/sir"),
        state_root=tmp_path,
    )

    assert isinstance(controller, WorkloadController)
    assert hemma_workload.HOST_STATE_ROOT == Path("/var/lib/hemma/workload-switch")
    assert hemma_workload.LOCK_PATH == Path("/var/lib/hemma/workload-switch/active.lock")
    assert not (tmp_path / "claim-ledger.json").exists()
    assert not (tmp_path / "active.lock").exists()


def test_controller_refuses_retired_edge_without_host_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = QueueRunner([])
    controller = hemma_workload.sir_workload_controller(
        runner=runner,
        product_runner=_composition(tmp_path, monkeypatch),
        project_root=Path("/srv/sir"),
        state_root=tmp_path,
    )

    with pytest.raises(ValueError, match="unknown workload identity 'sir-public-reserved-edge'"):
        controller.start("sir-public-reserved-edge", "tx-retired")

    assert runner.commands == []
    assert not (tmp_path / "claim-ledger.json").exists()


def test_provider_controller_refuses_unknown_consumer_before_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sir_convert_unknown_gpu\n"),
            hemma_workload.CommandResult(0, ""),
        ]
    )
    controller = hemma_workload.sir_workload_controller(
        runner=runner,
        product_runner=_composition(tmp_path, monkeypatch),
        project_root=Path("/srv/sir"),
        state_root=tmp_path,
    )

    with pytest.raises(WorkloadTransactionError, match="unknown consumers require declaration"):
        controller.start(hemma_workload.PRODUCTION_WORKLOAD_ID, "tx-unknown")
    assert not (tmp_path / "claim-ledger.json").exists()


def test_shared_controller_restores_only_receipted_conflict_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = StatefulRunner()
    monkeypatch.setattr(hemma_workload, "_repository_head", lambda bounded: "a" * 40)
    monkeypatch.setattr(
        hemma_workload,
        "_poll_ready",
        lambda bounded, *, head, docker_prefix: None,
    )
    monkeypatch.setattr(
        hemma_workload,
        "_prove_gpu_readiness",
        lambda bounded, *, docker_prefix: None,
    )
    controller = hemma_workload.sir_workload_controller(
        runner=runner,
        product_runner=_composition(tmp_path, monkeypatch),
        project_root=Path("/srv/sir"),
        state_root=tmp_path,
    )

    started = controller.start(hemma_workload.PRODUCTION_WORKLOAD_ID, "tx-restore")
    assert started.outcome is TerminalOutcome.SUCCEEDED
    assert runner.running == set(hemma_workload.PRODUCTION_CONTAINERS)

    stopped = controller.stop(hemma_workload.PRODUCTION_WORKLOAD_ID, "tx-restore")
    assert stopped.outcome is TerminalOutcome.SUCCEEDED
    assert runner.running == {hemma_workload.STT_CONTAINER}
    started_containers = {command[4] for command in runner.commands if command[3:4] == ("start",)}
    assert started_containers <= set(hemma_workload.PRODUCTION_CONTAINERS) | {
        hemma_workload.STT_CONTAINER
    }
    ledger = LedgerStore(tmp_path).read()
    assert ledger.holders == ()
    assert ledger.queue == ()


def test_production_start_existing_starts_matching_containers() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, ""),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start_existing().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands[-1] == (
        *hemma_workload.DOCKER_COMMAND,
        "start",
        *hemma_workload.PRODUCTION_CONTAINERS,
    )


def test_production_start_existing_refuses_absent_container() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(1, "No such object"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "absent" in result.reason
    assert all(command[3:4] != ("start",) for command in runner.commands)


def test_production_start_existing_refuses_stale_image() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:app\n"),
            hemma_workload.CommandResult(0, "sha256:old\n"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "stale application image" in result.reason
    assert all(command[3:4] != ("start",) for command in runner.commands)


def test_production_start_existing_refuses_missing_application_image() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "a" * 40 + "\n"),
            hemma_workload.CommandResult(1, "No such image"),
        ]
    )
    adapter = hemma_workload.ProductionWorkloadAdapter(runner, Path("/srv/sir"))

    assert adapter.start_existing().outcome is TerminalOutcome.FAILED


def test_container_start_existing_starts_existing_container() -> None:
    runner = QueueRunner(
        [
            hemma_workload.CommandResult(0, "sha256:stt\n"),
            hemma_workload.CommandResult(0, ""),
        ]
    )
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID, hemma_workload.STT_CONTAINER, runner
    )

    assert adapter.start_existing().outcome is TerminalOutcome.SUCCEEDED
    assert runner.commands[-1] == (
        *hemma_workload.DOCKER_COMMAND,
        "start",
        hemma_workload.STT_CONTAINER,
    )


def test_container_start_existing_refuses_absent_container() -> None:
    runner = QueueRunner([hemma_workload.CommandResult(1, "No such object")])
    adapter = hemma_workload.ContainerWorkloadAdapter(
        hemma_workload.STT_WORKLOAD_ID, hemma_workload.STT_CONTAINER, runner
    )

    result = adapter.start_existing()

    assert result.outcome is TerminalOutcome.FAILED
    assert "absent" in result.reason
