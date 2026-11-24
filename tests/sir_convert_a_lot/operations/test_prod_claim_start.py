"""Wrapper tests for the claim-routed production start surfaces.

Purpose:
    Ensure `scripts/devops/prod-claim-start.sh` starts production through the
    owner's Hemma workload claim, and that the production `recreate` action
    creates the containers without starting them before the same claim start.

Relationships:
    - Exercises `scripts/devops/prod-claim-start.sh` and the `recreate` action
      of `scripts/devops/prod-compose.sh` and `scripts/devops/compose-actions.sh`.
    - Shares fakes with the local, production and remote-proof wrapper tests
      through `tests.sir_convert_a_lot.operations.compose_wrapper_fakes`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from tests.sir_convert_a_lot.operations.compose_wrapper_fakes import (
    DEV_COMPOSE_SCRIPT,
    PROD_COMPOSE_SCRIPT,
    REPO_ROOT,
    _run_wrapper,
    _with_fake_hemma_env,
    _with_fake_prod_compose_env,
    _write_fake_agent_secrets,
    _write_fake_docker,
    _write_fake_pdm,
    _write_fake_sudo,
)

PROD_CLAIM_START_SCRIPT = REPO_ROOT / "scripts" / "devops" / "prod-claim-start.sh"
CLAIM_START_RE = re.compile(
    r"^pdm run hemma-workload start sir-production "
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _prod_env_with_fakes(tmp_path: Path) -> tuple[dict[str, str], Path]:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    _write_fake_agent_secrets(fake_bin)
    _write_fake_pdm(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "prod_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "prod_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_prod_compose_env(env, tmp_path)
    return env, log_file


def test_prod_claim_start_runs_owner_claim_with_generated_transaction(tmp_path: Path) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_CLAIM_START_SCRIPT, [], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    claim_lines = [line for line in log_lines if CLAIM_START_RE.match(line)]
    assert len(claim_lines) == 1


@pytest.mark.parametrize("claim_exit_code", [0, 3, 1])
def test_prod_claim_start_passes_claim_exit_code_through(
    tmp_path: Path, claim_exit_code: int
) -> None:
    env, _log_file = _prod_env_with_fakes(tmp_path)
    env["FAKE_PDM_EXIT"] = str(claim_exit_code)

    result = _run_wrapper(PROD_CLAIM_START_SCRIPT, [], env)
    assert result.returncode == claim_exit_code


def test_prod_compose_recreate_creates_without_starting_then_runs_claim(tmp_path: Path) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate", "sir_convert_a_lot_prod"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    up_index = next(
        index
        for index, line in enumerate(log_lines)
        if "up -d --no-start --no-build --no-deps --force-recreate sir_convert_a_lot_prod" in line
    )
    assert "compose.secrets.yaml" in log_lines[up_index]
    claim_index = next(index for index, line in enumerate(log_lines) if CLAIM_START_RE.match(line))
    assert up_index < claim_index


@pytest.mark.parametrize("claim_exit_code", [3, 1])
def test_prod_compose_recreate_exits_with_claim_code(tmp_path: Path, claim_exit_code: int) -> None:
    env, _log_file = _prod_env_with_fakes(tmp_path)
    env["FAKE_PDM_EXIT"] = str(claim_exit_code)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate", "sir_convert_a_lot_prod"], env)
    assert result.returncode == claim_exit_code


def test_dev_compose_recreate_keeps_build_and_start_without_claim(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_pdm(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)

    result = _run_wrapper(DEV_COMPOSE_SCRIPT, ["recreate", "sir_convert_a_lot_dev"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("up -d --force-recreate --build sir_convert_a_lot_dev" in line for line in log_lines)
    assert not any(CLAIM_START_RE.match(line) for line in log_lines)
