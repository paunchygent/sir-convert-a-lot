"""Start only the exact production API and GPU worker on Hemma."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    CommandRunner,
    RuntimeSnapshot,
    StartupFailure,
    assert_preserved,
    compose_command,
    compose_volume_names,
    docker_command,
    inspect_container,
    inspect_image,
    take_runtime_snapshot,
)
from scripts.sir_convert_a_lot.devops.service_dependency_inputs import (
    build_project_dependency_image_identity_payload,
)
from scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime import (
    _read_pinned_torch_version,
)

TOTAL_TIMEOUT_SECONDS = 120.0
API_SERVICE = "sir_convert_a_lot_prod"
WORKER_SERVICE = "sir_convert_a_lot_gpu_worker"
SELECTED_NAMES = frozenset((API_SERVICE, WORKER_SERVICE))
EXPLICIT_EXCLUDED_NAMES = frozenset(
    (
        "sir_convert_a_lot_stt_sidecar",
        "sir_convert_qwen_answer_key",
        "sir_convert_a_lot_public_reserved",
    )
)
DEPENDENCY_LABELS = (
    "sir-convert-a-lot.dependency-hash",
    "sir-convert-a-lot.recipe-hash",
    "sir-convert-a-lot.dependency-image-hash",
)


def _repository_head(runner: CommandRunner) -> str:
    head = runner.run(["git", "rev-parse", "HEAD"]).stdout.strip()
    if len(head) != 40:
        raise StartupFailure(f"repository HEAD is malformed: {head!r}")
    return head


def _require_clean_repository(runner: CommandRunner) -> None:
    status = runner.run(["git", "status", "--porcelain", "--untracked-files=normal"]).stdout
    if status != "":
        raise StartupFailure(
            "repository checkout is dirty; commit or remove tracked and untracked source changes"
        )


def _dependency_identity(project_root: Path) -> dict[str, str]:
    requirements = project_root.joinpath("docker/service-deps/service-requirements.txt").read_text(
        encoding="utf-8"
    )
    payload = build_project_dependency_image_identity_payload(
        project_root=project_root,
        requirements_text=requirements,
        runtime_kind="rocm",
    )
    return {
        "dependency_hash": str(payload["dependency_hash"]),
        "recipe_hash": str(payload["recipe_hash"]),
        "dependency_image_hash": str(payload["dependency_image_hash"]),
    }


def _require_dependency_image(runner: CommandRunner, identity: dict[str, str]) -> str:
    image = f"sir-convert-a-lot-deps-rocm:{identity['dependency_image_hash']}"
    _, labels = inspect_image(runner, image, dependency_boundary=True)
    expected = {
        DEPENDENCY_LABELS[0]: identity["dependency_hash"],
        DEPENDENCY_LABELS[1]: identity["recipe_hash"],
        DEPENDENCY_LABELS[2]: identity["dependency_image_hash"],
    }
    for key, value in expected.items():
        if labels.get(key) != value:
            raise StartupFailure(
                "dependency image label mismatch: "
                f"{key} expected={value!r} actual={labels.get(key)!r}",
                outcome="dependency_unhealthy",
            )
    return image


def _compose_environment(*, head: str, dependency_image: str) -> dict[str, str]:
    return {
        "COMPOSE_DOCKER_CLI_BUILD": "1",
        "DOCKER_BUILDKIT": "1",
        "SIR_CONVERT_A_LOT_DEPS_IMAGE": dependency_image,
        "SIR_CONVERT_A_LOT_DEPS_RUNTIME": "rocm",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION": head,
        "SIR_CONVERT_A_LOT_IMAGE_TAG": head,
        "SIR_CONVERT_A_LOT_SERVICE_REVISION": head,
    }


def _admit_application_image(
    runner: CommandRunner,
    *,
    head: str,
    dependency_hash: str,
    dependency_image: str,
    environment: dict[str, str],
) -> tuple[str, str]:
    image = f"sir-convert-a-lot-runtime:{head}"
    needs_build = False
    try:
        _, labels = inspect_image(runner, image)
        needs_build = (
            labels.get("org.opencontainers.image.revision") != head
            or labels.get("sir-convert-a-lot.dependency-image-hash") != dependency_hash
        )
    except StartupFailure:
        needs_build = True
    if needs_build:
        runner.run(
            [
                *compose_command(environment),
                "-f",
                "compose.yaml",
                "build",
                "--build-arg",
                f"DEPS_IMAGE={dependency_image}",
                "--build-arg",
                f"SERVICE_REVISION={head}",
                "--build-arg",
                f"SIR_CONVERT_A_LOT_DEPENDENCY_IMAGE_HASH={dependency_hash}",
                API_SERVICE,
            ],
            environment=environment,
        )
    image_id, labels = inspect_image(runner, image)
    if labels.get("org.opencontainers.image.revision") != head:
        raise StartupFailure("application image OCI revision label mismatch")
    if labels.get("sir-convert-a-lot.dependency-image-hash") != dependency_hash:
        raise StartupFailure("application image dependency label mismatch")
    return image, image_id


def _start_selected(
    runner: CommandRunner,
    *,
    before: RuntimeSnapshot,
    application_image_id: str,
    environment: dict[str, str],
) -> None:
    worker = before.containers[WORKER_SERVICE]
    if worker.status == "running":
        if worker.image_id != application_image_id:
            raise StartupFailure("running GPU worker has stale application provenance")
        start_worker = False
    elif worker.status in (None, "created", "exited"):
        start_worker = True
    else:
        raise StartupFailure(
            f"GPU worker state is not admissible for bounded startup: {worker.status!r}"
        )

    api = before.containers[API_SERVICE]
    api_command = [
        *compose_command(environment),
        "-f",
        "compose.yaml",
        "up",
        "-d",
        "--no-deps",
        "--no-build",
    ]
    if api.image_id != application_image_id:
        api_command.append("--force-recreate")
    runner.run([*api_command, API_SERVICE], environment=environment)
    if not start_worker:
        return
    runner.run(
        [
            *compose_command(environment),
            "-f",
            "compose.yaml",
            "up",
            "-d",
            "--no-deps",
            "--no-build",
            WORKER_SERVICE,
        ],
        environment=environment,
    )


def _assert_running_worker_identity_preserved(
    runner: CommandRunner,
    *,
    before: RuntimeSnapshot,
    application_image_id: str,
) -> None:
    worker_before = before.containers[WORKER_SERVICE]
    if worker_before.status != "running" or worker_before.image_id != application_image_id:
        return
    worker_after = inspect_container(runner, WORKER_SERVICE)
    if worker_after.identity != worker_before.identity:
        raise StartupFailure("running GPU worker container identity changed")
    if worker_after.status != "running":
        raise StartupFailure("preserved GPU worker is no longer running")
    if worker_after.image_id != application_image_id:
        raise StartupFailure("preserved GPU worker application provenance changed")


def _resolve_api_ready_url(
    runner: CommandRunner, *, docker_prefix: Sequence[str] | None = None
) -> str:
    command = docker_command() if docker_prefix is None else list(docker_prefix)
    output = runner.run([*command, "port", API_SERVICE, "8085/tcp"]).stdout
    bindings = [line.strip() for line in output.splitlines() if line.strip()]
    if not bindings:
        raise StartupFailure("production API has no published 8085/tcp binding")
    ports: set[int] = set()
    for binding in bindings:
        match = re.fullmatch(
            r"(?:127\.0\.0\.1|0\.0\.0\.0|\[::\]|\[::1\]):([0-9]{1,5})",
            binding,
        )
        if match is None:
            raise StartupFailure(f"production API binding is not loopback-safe: {binding!r}")
        port = int(match.group(1))
        if port < 1 or port > 65535:
            raise StartupFailure(f"production API binding port is invalid: {binding!r}")
        ports.add(port)
    if len(ports) != 1:
        raise StartupFailure(f"production API has ambiguous published bindings: {bindings!r}")
    return f"http://127.0.0.1:{ports.pop()}/readyz"


def _poll_ready(
    runner: CommandRunner, *, head: str, docker_prefix: Sequence[str] | None = None
) -> None:
    url = _resolve_api_ready_url(runner, docker_prefix=docker_prefix)
    last_diagnostic = "no response"
    while True:
        remaining = runner.deadline - time.monotonic()
        if remaining <= 0:
            raise StartupFailure(
                f"API readiness timed out; last diagnostic: {last_diagnostic}",
                outcome="timed_out",
            )
        try:
            with urllib.request.urlopen(url, timeout=min(5.0, remaining)) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")
            decoded = json.loads(body)
            if not isinstance(decoded, dict):
                raise ValueError("payload is not a JSON mapping")
            last_diagnostic = body
            if (
                status == 200
                and decoded.get("ready") is True
                and decoded.get("service_revision") == head
                and decoded.get("expected_revision") == head
                and decoded.get("service_profile") == "prod"
                and decoded.get("expected_service_profile") == "prod"
                and decoded.get("data_root") == "/var/lib/sir-convert-a-lot/prod"
            ):
                return
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_diagnostic = f"HTTP {exc.code}: {body}"
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            last_diagnostic = f"{type(exc).__name__}: {exc}"
        if runner.deadline - time.monotonic() <= 0:
            raise StartupFailure(
                f"API readiness timed out; last diagnostic: {last_diagnostic}",
                outcome="timed_out",
            )
        time.sleep(min(1.0, max(0.0, runner.deadline - time.monotonic())))


def _prove_gpu_readiness(
    runner: CommandRunner, *, docker_prefix: Sequence[str] | None = None
) -> None:
    command = docker_command() if docker_prefix is None else list(docker_prefix)
    expected_torch = _read_pinned_torch_version()
    runner.run(
        [
            *command,
            "exec",
            WORKER_SERVICE,
            "test",
            "-e",
            "/dev/kfd",
        ]
    )
    runner.run(
        [
            *command,
            "exec",
            WORKER_SERVICE,
            "test",
            "-d",
            "/dev/dri",
        ]
    )
    probe = runner.run(
        [
            *command,
            "exec",
            WORKER_SERVICE,
            "/app/.venv/bin/python",
            "-c",
            (
                "import json, torch; "
                "print(json.dumps({'available': torch.cuda.is_available(), "
                "'count': torch.cuda.device_count(), "
                "'rocm': torch.version.hip, 'torch': torch.__version__}, sort_keys=True))"
            ),
        ]
    ).stdout.strip()
    probe_lines = probe.splitlines()
    if not probe_lines:
        raise StartupFailure("GPU worker torch probe returned no payload")
    try:
        decoded = json.loads(probe_lines[-1])
    except json.JSONDecodeError as exc:
        raise StartupFailure("GPU worker torch probe payload is malformed") from exc
    if not isinstance(decoded, dict):
        raise StartupFailure("GPU worker torch probe payload is malformed")
    device_count = decoded.get("count")
    if (
        decoded.get("available") is not True
        or not isinstance(device_count, int)
        or device_count < 1
        or not isinstance(decoded.get("rocm"), str)
        or decoded.get("torch") != expected_torch
        or "+rocm" not in expected_torch
    ):
        raise StartupFailure(f"GPU worker ROCm torch probe failed: {probe}")
    runner.run(["rocm-smi", "--showuse"])


def _apply_restart_truth(runner: CommandRunner) -> None:
    runner.run([*docker_command(), "update", "--restart=no", API_SERVICE, WORKER_SERVICE])
    for name in (API_SERVICE, WORKER_SERVICE):
        snapshot = inspect_container(runner, name)
        if snapshot.status != "running":
            raise StartupFailure(f"selected service is not running: {name}")
        if snapshot.restart_policy != "no":
            raise StartupFailure(f"selected service restart policy is not no: {name}")


def execute(project_root: Path) -> None:
    runner = CommandRunner(
        project_root=project_root,
        deadline=time.monotonic() + TOTAL_TIMEOUT_SECONDS,
    )
    _require_clean_repository(runner)
    runner.run([*docker_command(), "compose", "version"])
    head = _repository_head(runner)
    identity = _dependency_identity(project_root)
    dependency_image = _require_dependency_image(runner, identity)
    environment = _compose_environment(head=head, dependency_image=dependency_image)
    volume_names = compose_volume_names(runner, environment)
    before = take_runtime_snapshot(
        runner,
        selected_names=SELECTED_NAMES,
        explicit_excluded_names=EXPLICIT_EXCLUDED_NAMES,
        volume_names=volume_names,
    )
    primary_failure: StartupFailure | None = None
    try:
        _, application_image_id = _admit_application_image(
            runner,
            head=head,
            dependency_hash=identity["dependency_image_hash"],
            dependency_image=dependency_image,
            environment=environment,
        )
        _start_selected(
            runner,
            before=before,
            application_image_id=application_image_id,
            environment=environment,
        )
        _assert_running_worker_identity_preserved(
            runner,
            before=before,
            application_image_id=application_image_id,
        )
        _poll_ready(runner, head=head)
        _prove_gpu_readiness(runner)
        _apply_restart_truth(runner)
    except StartupFailure as exc:
        primary_failure = exc
    except SystemExit as exc:
        primary_failure = StartupFailure(f"GPU readiness failed: {exc}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        primary_failure = StartupFailure(f"runtime verification failed: {exc}")
    try:
        assert_preserved(runner, before=before, selected_names=SELECTED_NAMES)
    except StartupFailure as preservation_failure:
        if primary_failure is None:
            raise
        raise StartupFailure(
            f"{primary_failure}; preservation check also failed: {preservation_failure}",
            outcome=primary_failure.outcome,
        ) from preservation_failure
    if primary_failure is not None:
        raise primary_failure


def main() -> int:
    outcome = "succeeded"
    try:
        execute(Path.cwd())
    except StartupFailure as exc:
        outcome = exc.outcome
        print(f"prod-start-bounded: {exc}", file=sys.stderr)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        outcome = "failed"
        print(f"prod-start-bounded: {exc}", file=sys.stderr)
    print(f"outcome={outcome}")
    return 0 if outcome == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
