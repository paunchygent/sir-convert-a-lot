"""Shared command-runner fake for the Sir Hemma workload adapter tests.

Purpose:
    Provide `QueueRunner`, which returns queued `CommandResult` values in order
    and records each argv.

Relationships:
    - Imported by the production and sidecar adapter test modules.
"""

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
