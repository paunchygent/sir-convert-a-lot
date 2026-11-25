from pathlib import Path

from repository_governance.hemma_workload import ClaimKind, TerminalOutcome

from scripts.sir_convert_a_lot.devops import hemma_workload


class NoCommandRunner:
    def run(self, argv: tuple[str, ...]) -> hemma_workload.CommandResult:
        raise AssertionError(f"publication must not run commands: {argv}")


def test_sir_declarations_publish_service_kinds() -> None:
    declarations = hemma_workload.sir_workload_declarations(
        runner=NoCommandRunner(), project_root=Path("/srv/sir")
    )

    assert [item.identity for item in declarations] == [
        hemma_workload.PRODUCTION_WORKLOAD_ID,
        hemma_workload.STT_WORKLOAD_ID,
    ]
    production, stt = declarations
    assert production.service_identities == (
        hemma_workload.API_CONTAINER,
        hemma_workload.GPU_WORKER_CONTAINER,
    )
    assert stt.service_identities == (hemma_workload.STT_CONTAINER,)
    assert production.conflicts == frozenset({hemma_workload.STT_WORKLOAD_ID})
    assert stt.conflicts == frozenset({hemma_workload.PRODUCTION_WORKLOAD_ID})
    for declaration in declarations:
        assert declaration.kind is ClaimKind.SERVICE
        assert declaration.resource_claims == frozenset({"gpu:amdgpu"})
        assert declaration.dependencies == ()
        assert declaration.accepted_terminal_outcomes == frozenset({TerminalOutcome.SUCCEEDED})
    assert isinstance(production.adapter, hemma_workload.ProductionWorkloadAdapter)
    assert isinstance(stt.adapter, hemma_workload.ContainerWorkloadAdapter)
