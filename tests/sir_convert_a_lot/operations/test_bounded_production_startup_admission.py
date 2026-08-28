"""Admission and guard boundaries for bounded Hemma production startup."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import bounded_production_startup as startup
from scripts.sir_convert_a_lot.devops import bounded_production_startup_runtime as runtime
from scripts.sir_convert_a_lot.devops.bounded_production_startup_runtime import (
    CommandResult,
    CommandRunner,
    StartupFailure,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROD_START_BOUNDED = REPO_ROOT / "scripts" / "devops" / "prod-start-bounded.sh"
HEAD = "a" * 40
DEPENDENCY_HASH = "dependency-hash"
RECIPE_HASH = "recipe-hash"
DEPENDENCY_IMAGE_HASH = "dependency-image-hash"
DEPENDENCY_IMAGE = f"sir-convert-a-lot-deps-rocm:{DEPENDENCY_IMAGE_HASH}"
APPLICATION_IMAGE_ID = "sha256:application"
IDENTITY = {
    "dependency_hash": DEPENDENCY_HASH,
    "recipe_hash": RECIPE_HASH,
    "dependency_image_hash": DEPENDENCY_IMAGE_HASH,
}
EXPECTED_DEPENDENCY_LABELS = {
    startup.DEPENDENCY_LABELS[0]: DEPENDENCY_HASH,
    startup.DEPENDENCY_LABELS[1]: RECIPE_HASH,
    startup.DEPENDENCY_LABELS[2]: DEPENDENCY_IMAGE_HASH,
}


class _Runner(CommandRunner):
    def __init__(
        self,
        *,
        dependency_labels: dict[str, str] | None = None,
        git_status: str = "",
        port_output: str = "",
        inventory_output: str = "",
    ) -> None:
        super().__init__(project_root=REPO_ROOT, deadline=10.0)
        self.calls: list[tuple[list[str], dict[str, str] | None, bool]] = []
        self.dependency_labels = dependency_labels
        self.git_status = git_status
        self.port_output = port_output
        self.inventory_output = inventory_output

    def run(
        self,
        command: Sequence[str],
        *,
        environment: Mapping[str, str] | None = None,
        dependency_boundary: bool = False,
    ) -> CommandResult:
        command_vector = list(command)
        copied_environment = None if environment is None else dict(environment)
        self.calls.append((command_vector, copied_environment, dependency_boundary))
        if command_vector == ["git", "status", "--porcelain", "--untracked-files=normal"]:
            return CommandResult(stdout=self.git_status, stderr="")
        if command_vector == ["docker", "port", startup.API_SERVICE, "8085/tcp"]:
            return CommandResult(stdout=self.port_output, stderr="")
        if command_vector == ["docker", "ps", "-a", "--format", "{{.Names}}"]:
            return CommandResult(stdout=self.inventory_output, stderr="")
        if dependency_boundary:
            if self.dependency_labels is None:
                raise StartupFailure("dependency image is absent", outcome="dependency_unhealthy")
            return CommandResult(
                stdout=f"sha256:dependency\t{json.dumps(self.dependency_labels)}\n",
                stderr="",
            )
        return CommandResult(stdout="", stderr="")


def test_dependency_image_requires_exact_tag_and_every_identity_label() -> None:
    for label in startup.DEPENDENCY_LABELS:
        labels = dict(EXPECTED_DEPENDENCY_LABELS)
        labels[label] = "mismatched"
        runner = _Runner(dependency_labels=labels)

        with pytest.raises(StartupFailure, match="dependency image label mismatch") as captured:
            startup._require_dependency_image(runner, IDENTITY)

        assert captured.value.outcome == "dependency_unhealthy"
        assert runner.calls[0][0][-1] == DEPENDENCY_IMAGE
        assert runner.calls[0][2] is True

    missing = _Runner()
    with pytest.raises(StartupFailure) as captured:
        startup._require_dependency_image(missing, IDENTITY)
    assert captured.value.outcome == "dependency_unhealthy"
    assert all("service-deps-image.sh" not in " ".join(call[0]) for call in missing.calls)


def test_exact_application_image_is_admitted_without_a_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels = {
        "org.opencontainers.image.revision": HEAD,
        "sir-convert-a-lot.dependency-image-hash": DEPENDENCY_IMAGE_HASH,
    }
    inspections = [(APPLICATION_IMAGE_ID, labels), (APPLICATION_IMAGE_ID, labels)]

    def inspect_image(
        runner: CommandRunner,
        image: str,
        *,
        dependency_boundary: bool = False,
    ) -> tuple[str, dict[str, str]]:
        del runner, image, dependency_boundary
        return inspections.pop(0)

    runner = _Runner()
    monkeypatch.setattr(startup, "inspect_image", inspect_image)

    image, image_id = startup._admit_application_image(
        runner,
        head=HEAD,
        dependency_hash=DEPENDENCY_IMAGE_HASH,
        dependency_image=DEPENDENCY_IMAGE,
        environment=startup._compose_environment(head=HEAD, dependency_image=DEPENDENCY_IMAGE),
    )

    assert image == f"sir-convert-a-lot-runtime:{HEAD}"
    assert image_id == APPLICATION_IMAGE_ID
    assert runner.calls == []


@pytest.mark.parametrize("first_inspection_missing", [True, False])
def test_missing_or_mislabeled_application_image_builds_then_reinspects(
    monkeypatch: pytest.MonkeyPatch,
    first_inspection_missing: bool,
) -> None:
    expected_labels = {
        "org.opencontainers.image.revision": HEAD,
        "sir-convert-a-lot.dependency-image-hash": DEPENDENCY_IMAGE_HASH,
    }
    inspections = [(APPLICATION_IMAGE_ID, expected_labels)]
    initial_inspection = True

    def inspect_image(
        runner: CommandRunner,
        image: str,
        *,
        dependency_boundary: bool = False,
    ) -> tuple[str, dict[str, str]]:
        nonlocal initial_inspection
        del runner, image, dependency_boundary
        if initial_inspection:
            initial_inspection = False
            if first_inspection_missing:
                raise StartupFailure("application image is absent")
            return "sha256:old", {"org.opencontainers.image.revision": "old"}
        return inspections.pop(0)

    runner = _Runner()
    environment = startup._compose_environment(head=HEAD, dependency_image=DEPENDENCY_IMAGE)
    monkeypatch.setattr(startup, "inspect_image", inspect_image)

    startup._admit_application_image(
        runner,
        head=HEAD,
        dependency_hash=DEPENDENCY_IMAGE_HASH,
        dependency_image=DEPENDENCY_IMAGE,
        environment=environment,
    )

    assert runner.calls == [
        (
            [
                "docker",
                "compose",
                "-f",
                "compose.yaml",
                "build",
                "--build-arg",
                f"DEPS_IMAGE={DEPENDENCY_IMAGE}",
                "--build-arg",
                f"SERVICE_REVISION={HEAD}",
                "--build-arg",
                f"SIR_CONVERT_A_LOT_DEPENDENCY_IMAGE_HASH={DEPENDENCY_IMAGE_HASH}",
                startup.API_SERVICE,
            ],
            environment,
            False,
        )
    ]


def test_clean_repository_is_accepted() -> None:
    runner = _Runner()

    startup._require_clean_repository(runner)

    assert runner.calls == [
        (["git", "status", "--porcelain", "--untracked-files=normal"], None, False)
    ]


def test_dirty_repository_refuses_before_docker_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _Runner(git_status=" M scripts/service.py\n")

    def command_runner(*, project_root: Path, deadline: float) -> _Runner:
        del project_root, deadline
        return runner

    monkeypatch.setattr(startup, "CommandRunner", command_runner)

    with pytest.raises(StartupFailure, match="checkout is dirty"):
        startup.execute(REPO_ROOT)

    assert [call[0] for call in runner.calls] == [
        ["git", "status", "--porcelain", "--untracked-files=normal"]
    ]


def test_exact_single_api_binding_resolves_to_loopback() -> None:
    runner = _Runner(port_output="0.0.0.0:28085\n")

    url = startup._resolve_api_ready_url(runner)

    assert url == "http://127.0.0.1:28085/readyz"
    assert runner.calls[0][0] == ["docker", "port", startup.API_SERVICE, "8085/tcp"]


@pytest.mark.parametrize(
    "port_output",
    [
        "",
        "10.0.0.7:28085\n",
        "127.0.0.1:28085\n127.0.0.1:28086\n",
    ],
)
def test_missing_unsafe_or_ambiguous_api_bindings_fail_without_fallback(port_output: str) -> None:
    runner = _Runner(port_output=port_output)

    with pytest.raises(StartupFailure):
        startup._resolve_api_ready_url(runner)

    assert [call[0] for call in runner.calls] == [
        ["docker", "port", startup.API_SERVICE, "8085/tcp"]
    ]


def test_runtime_inventory_keeps_both_sir_prefixes_and_ignores_unrelated() -> None:
    runner = _Runner(
        inventory_output=("sir_convert_a_lot_prod\nsir-convert-a-lot-legacy-edge\npostgres\n")
    )

    names = runtime.container_names(runner)

    assert names == {"sir_convert_a_lot_prod", "sir-convert-a-lot-legacy-edge"}


def test_hemma_guard_refusal_emits_failed_outcome_without_starting_coordinator(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    coordinator_probe = tmp_path / "python-invoked"
    fake_python = fake_bin / "python"
    fake_python.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' invoked > {coordinator_probe}\n",
        encoding="utf-8",
    )
    fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fake_bin}:{environment['PATH']}",
            "SIR_CONVERT_A_LOT_CURRENT_HOSTNAME": "not-hemma",
            "SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY": "/tmp/not-skill-repository",
        }
    )

    result = subprocess.run(
        ["/bin/bash", str(PROD_START_BOUNDED)],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 70
    assert "prod-start-bounded: this command is Hemma Server-only" in result.stderr
    assert "Use: pdm run run-hemma -- <command> [args...]" in result.stderr
    assert result.stdout.splitlines() == ["outcome=failed"]
    assert not coordinator_probe.exists()
