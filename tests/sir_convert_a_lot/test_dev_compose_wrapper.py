"""Wrapper tests for deterministic local compose execution.

Purpose:
    Ensure the local Docker Compose wrapper enforces deterministic command
    behavior, revision wiring, and canonical action mappings.

Relationships:
    - Exercises `scripts/devops/dev-compose.sh`.
    - Protects Task 22 compose command-surface contracts.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "dev-compose.sh"


def _write_fake_docker(script_dir: Path) -> None:
    fake_docker = script_dir / "docker"
    fake_docker.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "compose" ]]; then
  echo "fake-docker: expected compose subcommand, got: $*" >&2
  exit 90
fi
shift

if [[ "${1:-}" == "version" ]]; then
  echo "Docker Compose version v2.fake"
  exit 0
fi

if [[ -n "${FAKE_DOCKER_LOG:-}" ]]; then
  printf "%s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
  printf "service_revision=%s expected_revision=%s\\n" \
    "${SIR_CONVERT_A_LOT_SERVICE_REVISION:-}" \
    "${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-}" >>"${FAKE_DOCKER_LOG}"
fi

exit 0
""",
        encoding="utf-8",
    )
    fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)


def _write_fake_docker_without_compose_plugin(script_dir: Path) -> None:
    fake_docker = script_dir / "docker"
    fake_docker.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "compose" && "${2:-}" == "version" ]]; then
  echo "fake-docker: compose plugin missing" >&2
  exit 1
fi
exit 0
""",
        encoding="utf-8",
    )
    fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)


def _run_wrapper(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(DEV_COMPOSE_SCRIPT), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
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
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"
    result = _run_wrapper(["ps"], env)
    assert result.returncode == 67
    assert "docker is not installed" in result.stderr


def test_dev_compose_fails_when_compose_plugin_is_unavailable(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker_without_compose_plugin(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = _run_wrapper(["ps"], env)
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

    result = _run_wrapper(["start", "sir_convert_a_lot_prod"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert log_lines[0].startswith(
        f"-f {REPO_ROOT / 'compose.yaml'} up -d --build sir_convert_a_lot_prod"
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

    result = _run_wrapper(["ps"], env)
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

    result = _run_wrapper(["check"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    command_lines = [line for index, line in enumerate(log_lines) if index % 2 == 0]
    assert command_lines == [
        f"-f {REPO_ROOT / 'compose.yaml'} config",
        f"-f {REPO_ROOT / 'compose.yaml'} ps",
    ]
