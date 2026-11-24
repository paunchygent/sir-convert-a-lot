import json
import pwd
import subprocess
from pathlib import Path

import pytest
from repository_governance.hemma_workload import (
    ClaimKind,
    LedgerStore,
    TerminalOutcome,
    WorkloadController,
    WorkloadTransactionError,
    products,
)
from repository_governance.hemma_workload.products import WORKER_COMMAND

from scripts.sir_convert_a_lot.devops import hemma_workload


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
        if argv == ("systemctl", "show", "-p", "MainPID", "--value", "hemma-qwen.service"):
            return hemma_workload.CommandResult(0, "0\n")
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
                "no"
                if argv[6] in (*hemma_workload.PRODUCTION_CONTAINERS, hemma_workload.STT_CONTAINER)
                else "unless-stopped"
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


PUBLISHED_CONTAINERS: dict[str, tuple[str, ...]] = {
    "hule-prod-core": ("huleedu_api", "huleedu_file_worker"),
    "hule-prod-rst-parser": ("huleedu_rst_parser_service_gumrrg",),
    "hule-offload": ("huleedu_essay_embed_offload",),
    "hule-transformer-train": ("huleedu_essay_transformer_train",),
    "hule-vision-crop": (
        "huleedu_vision_crop_offload",
        "huleedu_vision_crop_validator_phi",
    ),
    hemma_workload.PRODUCTION_WORKLOAD_ID: hemma_workload.PRODUCTION_CONTAINERS,
    hemma_workload.STT_WORKLOAD_ID: (hemma_workload.STT_CONTAINER,),
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
        owner = argv[5]
        if argv[6] == "containers":
            assert owner == "huleedu"
            containers = {"containers": PUBLISHED_CONTAINERS}
            return hemma_workload.CommandResult(0, json.dumps(containers))
        assert argv[6] == "declarations"
        declarations = {"declarations": list(SIBLING_DECLARATIONS[owner])}
        return hemma_workload.CommandResult(0, json.dumps(declarations))


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
            hemma_workload.CommandResult(0, "0\n"),
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


def test_service_start_queues_behind_adopted_conflicting_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = StatefulRunner()
    product_runner = _composition(tmp_path, monkeypatch)
    registry = hemma_workload.sir_workload_registry(
        runner=QueueRunner([]),
        product_runner=product_runner,
        project_root=Path("/srv/sir"),
    )
    production = registry.declaration(hemma_workload.PRODUCTION_WORKLOAD_ID)
    sidecar = registry.declaration(hemma_workload.STT_WORKLOAD_ID)
    assert hemma_workload.STT_WORKLOAD_ID in production.conflicts
    assert hemma_workload.PRODUCTION_WORKLOAD_ID in sidecar.conflicts
    controller = hemma_workload.sir_workload_controller(
        runner=runner,
        product_runner=product_runner,
        project_root=Path("/srv/sir"),
        state_root=tmp_path,
    )

    started = controller.start(hemma_workload.PRODUCTION_WORKLOAD_ID, "tx-service")

    assert started.outcome is TerminalOutcome.QUEUED
    assert hemma_workload.STT_WORKLOAD_ID in started.reason
    assert runner.running == {hemma_workload.STT_CONTAINER}
    stopped_containers = {command[4] for command in runner.commands if command[3:4] == ("stop",)}
    assert hemma_workload.STT_CONTAINER not in stopped_containers
    ledger = LedgerStore(tmp_path).read()
    assert {holder.identity for holder in ledger.holders} == {hemma_workload.STT_WORKLOAD_ID}
    assert [waiter.identity for waiter in ledger.queue] == [hemma_workload.PRODUCTION_WORKLOAD_ID]


def _operator_root_worker(monkeypatch: pytest.MonkeyPatch, *, operator: bool = True) -> None:
    monkeypatch.setattr(hemma_workload.os, "geteuid", lambda: 0)
    if operator:
        monkeypatch.setenv("SUDO_USER", "operator")
        entry = pwd.struct_passwd(("operator", "x", 1000, 1000, "", "/home/operator", "/bin/bash"))
        monkeypatch.setattr(hemma_workload.pwd, "getpwnam", lambda name: entry)
        monkeypatch.setattr(hemma_workload.pwd, "getpwuid", lambda uid: entry)
    else:
        monkeypatch.delenv("SUDO_USER", raising=False)
        monkeypatch.delenv("SUDO_UID", raising=False)


def test_sibling_runner_root_launches_as_operator_with_worker_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _operator_root_worker(monkeypatch)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def fake_run(argv: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "ok", "")

    monkeypatch.setattr(hemma_workload.subprocess, "run", fake_run)
    worker_cwd = tmp_path / "huleedu"
    worker_argv = (*WORKER_COMMAND, "huleedu", "declarations")

    result = hemma_workload._SiblingCommandRunner().run(
        worker_argv, timeout=30.0, cwd=worker_cwd, env={"PYTHONPATH": "/srv/huleedu"}
    )

    assert result.returncode == 0
    command, kwargs = calls[0]
    assert command[:6] == (
        "sudo",
        "-n",
        "-u",
        "operator",
        "env",
        "PATH=/home/operator/.local/bin:/usr/bin:/bin",
    )
    assert command[6] == "PYTHONPATH=/srv/huleedu"
    assert command[7:] == worker_argv
    assert kwargs["cwd"] == worker_cwd
    assert kwargs["timeout"] == 30.0


def test_sibling_runner_non_root_merges_worker_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hemma_workload.os, "geteuid", lambda: 1000)
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def fake_run(argv: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "ok", "")

    monkeypatch.setattr(hemma_workload.subprocess, "run", fake_run)
    worker_argv = (*WORKER_COMMAND, "huleedu", "declarations")

    result = hemma_workload._SiblingCommandRunner().run(
        worker_argv, timeout=5.0, cwd=tmp_path, env={"PYTHONPATH": "/srv/huleedu"}
    )

    assert result.returncode == 0
    command, kwargs = calls[0]
    assert command == worker_argv
    assert kwargs["cwd"] == tmp_path
    environment = kwargs["env"]
    assert isinstance(environment, dict)
    assert environment["PYTHONPATH"] == "/srv/huleedu"
    assert "PATH" in environment


def test_sibling_runner_root_without_operator_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _operator_root_worker(monkeypatch, operator=False)
    monkeypatch.setattr(
        hemma_workload.pwd,
        "getpwnam",
        lambda name: pytest.fail("operator lookup without SUDO_USER"),
    )
    monkeypatch.setattr(
        hemma_workload.subprocess,
        "run",
        lambda argv, **kwargs: pytest.fail("no subprocess without an operator account"),
    )

    result = hemma_workload._SiblingCommandRunner().run(
        (*WORKER_COMMAND, "huleedu", "declarations"), timeout=5.0
    )

    assert result.returncode != 0
    assert "operator" in result.stderr
