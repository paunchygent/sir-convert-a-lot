"""Wrapper tests for the local deterministic compose execution surface.

Purpose:
    Ensure the local Docker Compose wrapper enforces deterministic command
    behavior, revision wiring, and canonical action mappings.

Relationships:
    - Exercises `scripts/devops/dev-compose.sh`.
    - Shares fakes with the production and remote-proof wrapper tests through
      `tests.sir_convert_a_lot.operations.compose_wrapper_fakes`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from tests.sir_convert_a_lot.operations.compose_wrapper_fakes import (
    DEV_COMPOSE_SCRIPT,
    REPO_ROOT,
    _run_wrapper,
    _write_fake_docker,
    _write_fake_docker_without_compose_plugin,
)


def test_dev_compose_requires_action_argument() -> None:
    result = subprocess.run(
        ["/bin/bash", str(DEV_COMPOSE_SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_dev_compose_fails_when_docker_is_unavailable(tmp_path: Path) -> None:
    # A PATH of system directories finds the host's real docker (Hemma has /usr/bin/docker),
    # so give the wrapper only the non-docker tools it runs before the docker check.
    bin_dir = tmp_path / "bin-without-docker"
    bin_dir.mkdir()
    for tool in ("bash", "dirname"):
        tool_path = shutil.which(tool)
        if tool_path is not None:
            (bin_dir / tool).symlink_to(tool_path)
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    result = _run_wrapper(DEV_COMPOSE_SCRIPT, ["ps"], env)
    assert result.returncode == 67
    assert "docker is not installed" in result.stderr


def test_dev_compose_fails_when_compose_plugin_is_unavailable(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker_without_compose_plugin(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = _run_wrapper(DEV_COMPOSE_SCRIPT, ["ps"], env)
    assert result.returncode == 68
    assert "docker compose v2 plugin is not available" in result.stderr


def test_dev_compose_start_maps_to_up_with_build_and_revision_defaults(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env.pop("SIR_CONVERT_A_LOT_SERVICE_REVISION", None)
    env.pop("SIR_CONVERT_A_LOT_EXPECTED_REVISION", None)

    result = _run_wrapper(DEV_COMPOSE_SCRIPT, ["start", "sir_convert_a_lot_dev"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert log_lines[0].startswith(
        f"-f {REPO_ROOT / 'compose.local.yaml'} up -d --build sir_convert_a_lot_dev"
    )
    expected_head = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    assert log_lines[1] == f"service_revision={expected_head} expected_revision={expected_head}"


def test_dev_compose_preserves_explicit_revision_environment(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "service_rev_override"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "expected_rev_override"

    result = _run_wrapper(DEV_COMPOSE_SCRIPT, ["ps"], env)
    assert result.returncode == 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert log_lines[1] == (
        "service_revision=service_rev_override expected_revision=expected_rev_override"
    )


def test_dev_compose_check_runs_config_then_ps(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "rev_x"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "rev_x"

    result = _run_wrapper(DEV_COMPOSE_SCRIPT, ["check"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    command_lines = [line for index, line in enumerate(log_lines) if index % 2 == 0]
    assert command_lines == [
        f"-f {REPO_ROOT / 'compose.local.yaml'} config",
        f"-f {REPO_ROOT / 'compose.local.yaml'} ps",
    ]
