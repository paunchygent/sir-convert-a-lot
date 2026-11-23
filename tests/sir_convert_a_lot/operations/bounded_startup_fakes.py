"""Shared fakes for the bounded production startup test modules.

Purpose:
    Provide the recording command runner, HTTP response fake and container
    snapshot builders shared by the provenance and readiness test modules.

Relationships:
    - Imported by `test_bounded_production_startup.py` and
      `test_bounded_production_startup_readiness.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from types import TracebackType

from scripts.sir_convert_a_lot.devops import bounded_production_startup as startup
from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    CommandResult,
    CommandRunner,
    ContainerSnapshot,
    RuntimeSnapshot,
)

HEAD = "a" * 40
DEPENDENCY_IMAGE_HASH = "dependency-image-hash"
DEPENDENCY_IMAGE = f"sir-convert-a-lot-deps-rocm:{DEPENDENCY_IMAGE_HASH}"
APPLICATION_IMAGE_ID = "sha256:application"


class FakeRunner(CommandRunner):
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
        if command_vector[-3:] == ["port", startup.API_SERVICE, "8085/tcp"]:
            return CommandResult(stdout=self.api_port, stderr="")
        if "/app/.venv/bin/python" in command_vector:
            return CommandResult(stdout=self.gpu_probe, stderr="")
        return CommandResult(stdout="", stderr="")


class FakeResponse:
    def __init__(self, *, status: int, body: str) -> None:
        self.status = status
        self.body = body

    def __enter__(self) -> FakeResponse:
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


def container(
    name: str,
    *,
    identity: str = "container-id",
    status: str | None = "running",
    image_id: str | None = APPLICATION_IMAGE_ID,
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


def before_snapshot(
    *,
    api_image_id: str = APPLICATION_IMAGE_ID,
    worker_image_id: str = APPLICATION_IMAGE_ID,
    worker_status: str | None = "running",
) -> RuntimeSnapshot:
    return RuntimeSnapshot(
        containers={
            startup.API_SERVICE: container(startup.API_SERVICE, image_id=api_image_id),
            startup.WORKER_SERVICE: container(
                startup.WORKER_SERVICE,
                identity="current-worker-id",
                image_id=worker_image_id,
                status=worker_status,
            ),
        },
        excluded_names=frozenset(),
        volumes={},
    )
