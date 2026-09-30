"""GPU and product-claim inventory for Sir Hemma workloads.

Purpose:
    Inspect running Docker containers, ROCm KFD GPU processes, and declared
    container PIDs so the shared workload controller sees exact Sir workloads
    and fails closed on unknown GPU consumers.

Relationships:
    - Imported by `hemma_workload.py`, which wires `SirGpuInventory` into the
      Sir workload controller and re-exports it.
    - Uses `hemma_workload_constants.py` for claims, workload IDs, container
      names, and the privileged Docker prefix.
    - Runs host commands through `hemma_workload_runtime.CommandExecutor`.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from repository_governance.hemma_workload import (
    InventoryInspectionError,
    InventorySnapshot,
)
from repository_governance.retained_context.json_contract import JsonValue, strict_pairs

from scripts.sir_convert_a_lot.devops.hemma_workload_constants import (
    DECLARED_GPU_CONTAINERS,
    DOCKER_COMMAND,
    GPU_CLAIM,
    PRODUCT_RESOURCE_CLAIM,
    PRODUCTION_CONTAINERS,
    PRODUCTION_WORKLOAD_ID,
    RESERVED_EDGE_CONTAINER,
    RESERVED_EDGE_WORKLOAD_ID,
    STT_CONTAINER,
    STT_WORKLOAD_ID,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_runtime import CommandExecutor


@dataclass(frozen=True)
class GpuProcess:
    pid: int
    vram_bytes: int


class SirGpuInventory:
    """Inventory exact Sir workloads and fail closed on unknown GPU consumers."""

    def __init__(self, runner: CommandExecutor) -> None:
        self._runner = runner

    def inspect(self, resource_claims: frozenset[str]) -> InventorySnapshot:
        try:
            if resource_claims == frozenset({PRODUCT_RESOURCE_CLAIM}):
                running = _running_containers(self._runner)
                product_workloads = (
                    frozenset({RESERVED_EDGE_WORKLOAD_ID})
                    if RESERVED_EDGE_CONTAINER in running
                    else frozenset()
                )
                return InventorySnapshot(product_workloads, ())
            if resource_claims != frozenset({GPU_CLAIM}):
                raise ValueError(f"Sir inventory cannot inspect claims {sorted(resource_claims)}")
            running = _running_containers(self._runner)
            production_members = frozenset(PRODUCTION_CONTAINERS) & running
            if production_members and production_members != frozenset(PRODUCTION_CONTAINERS):
                raise ValueError("production API and GPU worker have a partial running state")
            workloads: set[str] = set()
            if production_members:
                workloads.add(PRODUCTION_WORKLOAD_ID)
            if STT_CONTAINER in running:
                workloads.add(STT_WORKLOAD_ID)
            declared_services = frozenset(
                (*PRODUCTION_CONTAINERS, STT_CONTAINER, RESERVED_EDGE_CONTAINER)
            )
            unknown = {
                f"container {name}"
                for name in running - declared_services
                if name.startswith(("sir_convert", "sir-convert"))
            }
            owned_pids = _declared_container_pids(self._runner, running)
            unknown.update(
                f"PID {process.pid}"
                for process in _rocm_processes(self._runner)
                if process.vram_bytes > 0 and process.pid not in owned_pids
            )
            return InventorySnapshot(frozenset(workloads), tuple(sorted(unknown)))
        except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
            raise InventoryInspectionError(str(error)) from error


def _running_containers(runner: CommandExecutor) -> frozenset[str]:
    result = runner.run((*DOCKER_COMMAND, "ps", "--format", "{{.Names}}"))
    if result.returncode != 0:
        raise ValueError("cannot inspect Docker running-container state")
    return frozenset(line for line in result.stdout.splitlines() if line)


def _rocm_processes(runner: CommandExecutor) -> tuple[GpuProcess, ...]:
    result = runner.run(("rocm-smi", "--showpids", "--json"))
    if result.returncode != 0:
        raise ValueError("cannot inspect current ROCm KFD process state")
    if not result.stdout.strip():
        return ()
    value: JsonValue = json.loads(result.stdout, object_pairs_hook=strict_pairs)
    if not isinstance(value, dict):
        raise ValueError("ROCm KFD process payload must be a mapping")
    system = value.get("system")
    if not isinstance(system, dict):
        raise ValueError("ROCm KFD process payload has no system map")
    processes: list[GpuProcess] = []
    for key, record in system.items():
        if not isinstance(key, str) or not key.startswith("PID") or not key[3:].isdigit():
            raise ValueError("ROCm KFD process payload has an invalid PID key")
        if not isinstance(record, str):
            raise ValueError("ROCm KFD process payload has an invalid process record")
        fields = tuple(field.strip() for field in record.split(","))
        if len(fields) < 3 or not fields[2].isdigit():
            raise ValueError("ROCm KFD process payload has an invalid VRAM field")
        processes.append(GpuProcess(int(key[3:]), int(fields[2])))
    return tuple(processes)


def _declared_container_pids(runner: CommandExecutor, running: frozenset[str]) -> frozenset[int]:
    pids: set[int] = set()
    for container in DECLARED_GPU_CONTAINERS:
        if container not in running:
            continue
        result = runner.run((*DOCKER_COMMAND, "top", container, "-eo", "pid"))
        if result.returncode != 0:
            raise ValueError(f"cannot inspect declared GPU container {container}")
        lines = result.stdout.splitlines()
        if not lines or lines[0].strip() != "PID":
            raise ValueError(f"declared GPU container {container} has malformed PID output")
        for value in lines[1:]:
            if not value.strip().isdigit():
                raise ValueError(f"declared GPU container {container} has malformed PID output")
            pids.add(int(value.strip()))
    return frozenset(pids)
