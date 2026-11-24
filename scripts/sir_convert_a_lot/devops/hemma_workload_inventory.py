"""GPU inventory for Sir Hemma workloads.

Purpose:
    Inspect running Docker containers, the declared Qwen systemd process, and
    ROCm KFD GPU processes so the shared workload controller sees every
    declared host GPU workload and fails closed on unknown GPU consumers.

Relationships:
    - Imported by `hemma_workload.py`, which wires `SirGpuInventory` into the
      Sir workload controller with the composed container map published by
      the HuleEdu product worker, and re-exports it.
    - Uses `hemma_workload_constants.py` for claims, the Qwen identity, and
      the privileged Docker prefix.
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
    DOCKER_COMMAND,
    GPU_CLAIM,
    PRODUCTION_WORKLOAD_ID,
    QWEN_SERVICE_NAME,
    QWEN_WORKLOAD_ID,
    STT_WORKLOAD_ID,
)
from scripts.sir_convert_a_lot.devops.hemma_workload_runtime import CommandExecutor

SIR_WORKLOAD_IDENTITIES = frozenset({PRODUCTION_WORKLOAD_ID, STT_WORKLOAD_ID})


@dataclass(frozen=True)
class GpuProcess:
    pid: int
    vram_bytes: int


class SirGpuInventory:
    """Inventory declared host GPU workloads and fail closed on unknown consumers."""

    def __init__(
        self,
        runner: CommandExecutor,
        containers: dict[str, tuple[str, ...]],
        gpu_identities: frozenset[str],
    ) -> None:
        self._runner = runner
        missing = SIR_WORKLOAD_IDENTITIES - containers.keys()
        if missing:
            raise ValueError(f"published containers lack Sir workloads {sorted(missing)}")
        self._containers = {
            identity: members
            for identity, members in containers.items()
            if identity in gpu_identities
        }

    def inspect(self, resource_claims: frozenset[str]) -> InventorySnapshot:
        try:
            if resource_claims != frozenset({GPU_CLAIM}):
                raise ValueError(f"Sir inventory cannot inspect claims {sorted(resource_claims)}")
            running = _running_containers(self._runner)
            declared_names = frozenset(
                name for members in self._containers.values() for name in members
            )
            workloads: set[str] = set()
            for identity, members in self._containers.items():
                present = frozenset(members) & running
                if present and present != frozenset(members):
                    raise ValueError(f"declared workload {identity} has a partial running state")
                if present:
                    workloads.add(identity)
            unknown = {
                f"container {name}"
                for name in running - declared_names
                if name.startswith(("sir_convert", "sir-convert"))
            }
            owned_pids = set(_declared_container_pids(self._runner, running & declared_names))
            qwen_pid = _qwen_main_pid(self._runner)
            if qwen_pid > 0:
                workloads.add(QWEN_WORKLOAD_ID)
                owned_pids.add(qwen_pid)
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


def _qwen_main_pid(runner: CommandExecutor) -> int:
    result = runner.run(("systemctl", "show", "-p", "MainPID", "--value", QWEN_SERVICE_NAME))
    if result.returncode != 0 or not result.stdout.strip().isdigit():
        raise ValueError("cannot inspect declared Qwen systemd PID")
    return int(result.stdout.strip())


def _declared_container_pids(runner: CommandExecutor, running: frozenset[str]) -> frozenset[int]:
    pids: set[int] = set()
    for container in sorted(running):
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
