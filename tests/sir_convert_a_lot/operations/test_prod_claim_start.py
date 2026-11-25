"""Wrapper tests for the claim-routed production start and recreate surfaces.

Purpose:
    Ensure `scripts/devops/prod-claim-start.sh` starts production through
    `hemma-services claim sir-production`, and that the production `recreate` action
    prepares the HEAD application image, creates the two production containers
    without starting them, and ends with `hemma-services redeploy sir-production`.

Relationships:
    - Exercises `scripts/devops/prod-claim-start.sh`,
      `scripts/devops/prod-claim-redeploy.sh`, and the `recreate` action
      of `scripts/devops/prod-compose.sh` and `scripts/devops/compose-actions.sh`.
    - Shares fakes with the local, production and remote-proof wrapper tests
      through `tests.sir_convert_a_lot.operations.compose_wrapper_fakes`.
"""

from __future__ import annotations

import json
import os
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
    _write_fake_hemma_services,
    _write_fake_python,
    _write_fake_sudo,
)

PROD_CLAIM_START_SCRIPT = REPO_ROOT / "scripts" / "devops" / "prod-claim-start.sh"
PROD_CLAIM_REDEPLOY_SCRIPT = REPO_ROOT / "scripts" / "devops" / "prod-claim-redeploy.sh"
CLAIM_START_LINE = "hemma-services claim sir-production"
CLAIM_REDEPLOY_LINE = "hemma-services redeploy sir-production"


def _prod_env_with_fakes(tmp_path: Path) -> tuple[dict[str, str], Path]:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    _write_fake_agent_secrets(fake_bin)
    _write_fake_hemma_services(fake_bin)
    _write_fake_python(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "prod_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "prod_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_prod_compose_env(env, tmp_path)
    return env, log_file


def test_prod_claim_start_runs_hemma_services_claim(tmp_path: Path) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_CLAIM_START_SCRIPT, [], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert log_lines.count(CLAIM_START_LINE) == 1
    claim = json.loads(result.stdout.strip().splitlines()[-1])
    assert claim["outcome"] == "succeeded"
    assert claim["target_identity"] == "sir-production"
    assert claim["transaction_id"] is None


def test_prod_claim_redeploy_runs_hemma_services_redeploy(tmp_path: Path) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_CLAIM_REDEPLOY_SCRIPT, [], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert log_lines.count(CLAIM_REDEPLOY_LINE) == 1


@pytest.mark.parametrize("claim_exit_code", [0, 3, 1])
def test_prod_claim_start_passes_claim_exit_code_through(
    tmp_path: Path, claim_exit_code: int
) -> None:
    env, _log_file = _prod_env_with_fakes(tmp_path)
    env["FAKE_HEMMA_SERVICES_EXIT"] = str(claim_exit_code)

    result = _run_wrapper(PROD_CLAIM_START_SCRIPT, [], env)
    assert result.returncode == claim_exit_code


@pytest.mark.parametrize("extra_args", [["--help"], ["sir_convert_a_lot_prod"]])
def test_prod_claim_start_refuses_extra_arguments_without_a_claim(
    tmp_path: Path, extra_args: list[str]
) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_CLAIM_START_SCRIPT, extra_args, env)
    assert result.returncode == 2
    assert "Usage:" in result.stderr

    log_text = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    assert "hemma-services" not in log_text


@pytest.mark.parametrize("extra_args", [["--help"], ["sir_convert_a_lot_prod"]])
def test_prod_claim_redeploy_refuses_extra_arguments_without_a_claim(
    tmp_path: Path, extra_args: list[str]
) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_CLAIM_REDEPLOY_SCRIPT, extra_args, env)
    assert result.returncode == 2
    assert "Usage:" in result.stderr

    log_text = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    assert "hemma-services" not in log_text


def test_prod_compose_recreate_creates_without_starting_then_runs_claim_redeploy(
    tmp_path: Path,
) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    up_index = next(
        index
        for index, line in enumerate(log_lines)
        if "up -d --no-start --no-build --no-deps --force-recreate" in line
    )
    assert "compose.secrets.yaml" in log_lines[up_index]
    assert "sir_convert_a_lot_prod" in log_lines[up_index]
    assert "sir_convert_a_lot_gpu_worker" in log_lines[up_index]
    assert "sir_convert_a_lot_stt_sidecar" not in log_lines[up_index]
    claim_index = next(index for index, line in enumerate(log_lines) if line == CLAIM_REDEPLOY_LINE)
    assert up_index < claim_index


@pytest.mark.parametrize("claim_exit_code", [3, 1])
def test_prod_compose_recreate_exits_with_claim_code(tmp_path: Path, claim_exit_code: int) -> None:
    env, _log_file = _prod_env_with_fakes(tmp_path)
    env["FAKE_HEMMA_SERVICES_EXIT"] = str(claim_exit_code)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate"], env)
    assert result.returncode == claim_exit_code


def test_prod_compose_recreate_refuses_non_production_services(tmp_path: Path) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate", "sir_convert_a_lot_stt_sidecar"], env)
    assert result.returncode == 2
    assert "Usage:" in result.stderr

    log_text = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    assert "--force-recreate" not in log_text
    assert "hemma-services" not in log_text


def test_prod_compose_recreate_fails_when_image_admission_fails(tmp_path: Path) -> None:
    env, log_file = _prod_env_with_fakes(tmp_path)
    env["FAKE_PREPARE_IMAGE_EXIT"] = "1"

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate"], env)
    assert result.returncode == 1

    log_text = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    assert "--force-recreate" not in log_text
    assert "hemma-services" not in log_text


def test_dev_compose_recreate_keeps_build_and_start_without_claim(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_hemma_services(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)

    result = _run_wrapper(DEV_COMPOSE_SCRIPT, ["recreate", "sir_convert_a_lot_dev"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("up -d --force-recreate --build sir_convert_a_lot_dev" in line for line in log_lines)
    assert not any(line.startswith("hemma-services") for line in log_lines)
