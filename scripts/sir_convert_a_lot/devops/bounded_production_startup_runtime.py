"""Docker and host-runtime primitives for bounded production startup."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ContainerSnapshot:
    name: str
    identity: str | None
    status: str | None
    state_record: str | None
    image_id: str | None
    configured_image: str | None
    restart_policy: str | None

    def exact_record(self) -> tuple[str | None, ...]:
        return (
            self.identity,
            self.state_record,
            self.image_id,
            self.configured_image,
            self.restart_policy,
        )


@dataclass(frozen=True)
class RuntimeSnapshot:
    containers: dict[str, ContainerSnapshot]
    excluded_names: frozenset[str]
    volumes: dict[str, str]


class StartupFailure(RuntimeError):
    def __init__(self, message: str, *, outcome: str = "failed") -> None:
        super().__init__(message)
        self.outcome = outcome


class CommandRunner:
    def __init__(self, *, project_root: Path, deadline: float) -> None:
        self.project_root = project_root
        self.deadline = deadline

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise StartupFailure("bounded startup deadline expired", outcome="timed_out")
        return remaining

    def run(
        self,
        command: Sequence[str],
        *,
        environment: Mapping[str, str] | None = None,
        dependency_boundary: bool = False,
    ) -> CommandResult:
        merged_environment = os.environ.copy()
        if environment is not None:
            merged_environment.update(environment)
        try:
            completed = subprocess.run(
                list(command),
                cwd=self.project_root,
                env=merged_environment,
                capture_output=True,
                check=False,
                text=True,
                timeout=self.remaining(),
            )
        except subprocess.TimeoutExpired as exc:
            raise StartupFailure(
                f"command timed out: {' '.join(command)}", outcome="timed_out"
            ) from exc
        if completed.returncode != 0:
            diagnostic = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic"
            outcome = "dependency_unhealthy" if dependency_boundary else "failed"
            raise StartupFailure(
                f"command failed ({completed.returncode}): {' '.join(command)}: {diagnostic}",
                outcome=outcome,
            )
        return CommandResult(stdout=completed.stdout, stderr=completed.stderr)


def docker_command() -> list[str]:
    if os.environ.get("SIR_CONVERT_A_LOT_DOCKER_USE_SUDO", "0") == "1":
        return ["sudo", "-n", "docker"]
    return ["docker"]


def inspect_image(
    runner: CommandRunner, image: str, *, dependency_boundary: bool = False
) -> tuple[str, dict[str, str]]:
    result = runner.run(
        [
            *docker_command(),
            "image",
            "inspect",
            "--format",
            "{{.Id}}\t{{json .Config.Labels}}",
            image,
        ],
        dependency_boundary=dependency_boundary,
    )
    fields = result.stdout.strip().split("\t", maxsplit=1)
    if len(fields) != 2 or not fields[0].startswith("sha256:"):
        raise StartupFailure(f"malformed image inspection for {image!r}")
    decoded = json.loads(fields[1])
    if not isinstance(decoded, dict):
        raise StartupFailure(f"image labels are malformed for {image!r}")
    labels: dict[str, str] = {}
    for key, value in decoded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise StartupFailure(f"image labels are malformed for {image!r}")
        labels[key] = value
    return fields[0], labels


def inspect_container(runner: CommandRunner, name: str) -> ContainerSnapshot:
    result = runner.run(
        [
            *docker_command(),
            "container",
            "inspect",
            "--format",
            (
                "{{.Id}}\t{{.State.Status}}\t{{.State.Running}}\t"
                "{{.State.Paused}}\t{{.State.Restarting}}\t"
                "{{.State.OOMKilled}}\t{{.State.Dead}}\t"
                "{{.State.ExitCode}}\t{{json .State.Error}}\t"
                "{{.State.StartedAt}}\t{{.State.FinishedAt}}\t{{.Image}}\t"
                "{{.Config.Image}}\t{{.HostConfig.RestartPolicy.Name}}"
            ),
            name,
        ]
    )
    fields = result.stdout.strip().split("\t")
    if len(fields) != 14:
        raise StartupFailure(f"malformed container inspection for {name!r}")
    return ContainerSnapshot(
        name=name,
        identity=fields[0],
        status=fields[1],
        state_record="\t".join(fields[1:11]),
        image_id=fields[11],
        configured_image=fields[12],
        restart_policy=fields[13],
    )


def container_names(runner: CommandRunner) -> set[str]:
    result = runner.run([*docker_command(), "ps", "-a", "--format", "{{.Names}}"])
    return {
        line
        for line in result.stdout.splitlines()
        if line.startswith(("sir_convert", "sir-convert"))
    }


def compose_volume_names(runner: CommandRunner, environment: Mapping[str, str]) -> tuple[str, str]:
    result = runner.run(
        [*docker_command(), "compose", "-f", "compose.yaml", "config", "--format", "json"],
        environment=environment,
    )
    decoded = json.loads(result.stdout)
    if not isinstance(decoded, dict):
        raise StartupFailure("Compose config payload is malformed")
    volumes = decoded.get("volumes")
    if not isinstance(volumes, dict):
        raise StartupFailure("Compose config does not declare production volumes")
    resolved: list[str] = []
    for key in ("sir-convert-a-lot-prod-data", "sir-convert-a-lot-stt-sidecar-inputs"):
        value = volumes.get(key)
        if not isinstance(value, dict) or not isinstance(value.get("name"), str):
            raise StartupFailure(f"Compose volume {key!r} has no resolved name")
        resolved.append(value["name"])
    return resolved[0], resolved[1]


def inspect_volume(runner: CommandRunner, name: str) -> str:
    return runner.run(
        [*docker_command(), "volume", "inspect", "--format", "{{json .}}", name]
    ).stdout.strip()


def take_runtime_snapshot(
    runner: CommandRunner,
    *,
    selected_names: frozenset[str],
    explicit_excluded_names: frozenset[str],
    volume_names: tuple[str, str],
) -> RuntimeSnapshot:
    present = container_names(runner)
    names = present | selected_names | explicit_excluded_names
    containers: dict[str, ContainerSnapshot] = {}
    for name in sorted(names):
        if name in present:
            containers[name] = inspect_container(runner, name)
        else:
            containers[name] = ContainerSnapshot(name, None, None, None, None, None, None)
    excluded = frozenset(names - selected_names)
    volumes = {name: inspect_volume(runner, name) for name in volume_names}
    return RuntimeSnapshot(containers=containers, excluded_names=excluded, volumes=volumes)


def assert_preserved(
    runner: CommandRunner,
    *,
    before: RuntimeSnapshot,
    selected_names: frozenset[str],
) -> None:
    after_names = container_names(runner)
    newly_appeared = after_names - set(before.containers) - set(selected_names)
    if newly_appeared:
        raise StartupFailure(f"excluded containers appeared: {sorted(newly_appeared)!r}")
    for name in sorted(before.excluded_names):
        current = (
            inspect_container(runner, name)
            if name in after_names
            else ContainerSnapshot(name, None, None, None, None, None, None)
        )
        if current.exact_record() != before.containers[name].exact_record():
            raise StartupFailure(f"excluded container identity changed: {name}")
    for name, exact_record in before.volumes.items():
        if inspect_volume(runner, name) != exact_record:
            raise StartupFailure(f"persistent volume identity changed: {name}")
