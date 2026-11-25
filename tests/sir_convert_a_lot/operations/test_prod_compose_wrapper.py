"""Wrapper tests for the production deterministic compose execution surface.

Purpose:
    Ensure the production Docker Compose wrapper enforces deterministic command
    behavior, revision wiring, secrets-overlay routing and canonical action
    mappings without sharing compose files accidentally.

Relationships:
    - Exercises `scripts/devops/prod-compose.sh`.
    - Shares fakes with the local and remote-proof wrapper tests through
      `tests.sir_convert_a_lot.operations.compose_wrapper_fakes`.
"""

from __future__ import annotations

import os
from pathlib import Path

from tests.sir_convert_a_lot.operations.compose_wrapper_fakes import (
    PROD_COMPOSE_SCRIPT,
    REPO_ROOT,
    _current_rocm_identity,
    _run_wrapper,
    _with_fake_hemma_env,
    _with_fake_prod_compose_env,
    _write_fake_agent_secrets,
    _write_fake_docker,
    _write_fake_hemma_services,
    _write_fake_python,
    _write_fake_sudo,
)


def test_prod_compose_recreate_maps_to_production_compose_surface(tmp_path: Path) -> None:
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
    env["FAKE_DOCKER_LOG_SECRETS"] = "1"
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "prod_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "prod_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_prod_compose_env(env, tmp_path)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate", "sir_convert_a_lot_prod"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    agent_secrets_line = next(
        line for line in log_lines if line.startswith("agent-secrets run --set ")
    )
    assert agent_secrets_line.startswith(
        "agent-secrets run --set sir-convert-a-lot-prod -- bash -c "
    )
    sudo_compose_line = next(
        line
        for line in log_lines
        if line.startswith("sudo -n --preserve-env=") and " docker compose --env-file " in line
    )
    source_env_path = tmp_path / "prod-compose.env"
    assert f"--env-file {source_env_path} --env-file " in sudo_compose_line
    snapshot_path = Path(
        sudo_compose_line.split(f"--env-file {source_env_path} --env-file ", maxsplit=1)[1].split(
            " -f ", maxsplit=1
        )[0]
    )
    assert snapshot_path.parent == tmp_path / "compose-env-snapshots"
    assert snapshot_path.name.startswith("sir-convert-compose-env.")
    assert (
        f"--env-file {source_env_path} --env-file {snapshot_path} "
        f"-f {REPO_ROOT / 'compose.yaml'} "
        f"-f {REPO_ROOT / 'compose.secrets.yaml'} "
        "up -d --no-start --no-build --no-deps --force-recreate "
        "sir_convert_a_lot_prod sir_convert_a_lot_gpu_worker"
    ) in log_lines
    assert "service_revision=prod_rev expected_revision=prod_rev" in log_lines
    assert "secret_env SIR_CONVERT_A_LOT_V2_API_KEY=present" in log_lines
    assert "secret_env HF_TOKEN=present" in log_lines
    assert f"env_file_secret_lines {source_env_path}=2" in log_lines
    assert f"env_file_secret_lines {snapshot_path}=0" in log_lines
    keys_prefix = f"env_file_keys {snapshot_path}="
    keys_line = next(line for line in log_lines if line.startswith(keys_prefix))
    generated_keys = set(keys_line[len(keys_prefix) :].split(","))
    assert generated_keys <= {
        "SIR_CONVERT_A_LOT_DEPS_IMAGE",
        "SIR_CONVERT_A_LOT_IMAGE_TAG",
        "SIR_CONVERT_A_LOT_SERVICE_REVISION",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION",
        "HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH",
    }
    assert "SIR_CONVERT_A_LOT_SERVICE_REVISION" in generated_keys
    assert "SIR_CONVERT_A_LOT_IMAGE_TAG" in generated_keys
    assert "UNRELATED_SOURCE_VALUE" not in generated_keys
    assert not snapshot_path.exists()


def test_prod_compose_refuses_raw_start_without_a_claim(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    _write_fake_agent_secrets(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["FAKE_DOCKER_LOG_SECRETS"] = "1"
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "prod_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "prod_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_prod_compose_env(env, tmp_path)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["start", "sir_convert_a_lot_prod"], env)
    assert result.returncode == 2
    assert "Usage:" in result.stderr

    log_text = log_file.read_text(encoding="utf-8") if log_file.exists() else ""
    assert "up -d --build" not in log_text
    assert "agent-secrets run" not in log_text
    assert "hemma-services" not in log_text


def test_prod_compose_ps_uses_base_file_without_agent_secrets(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "prod_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "prod_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_prod_compose_env(env, tmp_path)

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["ps"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert not any(line.startswith("agent-secrets") for line in log_lines)
    compose_line = next(line for line in log_lines if line.endswith(" ps"))
    assert f"-f {REPO_ROOT / 'compose.yaml'}" in compose_line
    assert "compose.secrets.yaml" not in compose_line


def test_prod_compose_reuses_dependency_image_only_when_labels_match(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    log_file = tmp_path / "docker.log"
    identity = _current_rocm_identity()

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["FAKE_DOCKER_LOG_BUILDS"] = "1"
    env["FAKE_DOCKER_IMAGE_EXISTS"] = "1"
    env["FAKE_DOCKER_LABEL_DEPENDENCY_HASH"] = identity["dependency_hash"]
    env["FAKE_DOCKER_LABEL_RECIPE_HASH"] = identity["recipe_hash"]
    env["FAKE_DOCKER_LABEL_DEPENDENCY_IMAGE_HASH"] = identity["dependency_image_hash"]
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "prod_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "prod_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_prod_compose_env(env, tmp_path)

    _write_fake_agent_secrets(fake_bin)
    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["build"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    dependency_image = f"sir-convert-a-lot-deps-rocm:{identity['dependency_image_hash']}"
    assert f"tag {dependency_image} sir-convert-a-lot-deps-rocm:local" in log_lines
    assert not any(
        line.startswith("buildx build --load --file Dockerfile.deps") for line in log_lines
    )


def test_prod_compose_rebuilds_dependency_image_when_recipe_label_is_stale(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    log_file = tmp_path / "docker.log"
    identity = _current_rocm_identity()

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["FAKE_DOCKER_LOG_BUILDS"] = "1"
    env["FAKE_DOCKER_IMAGE_EXISTS"] = "1"
    env["FAKE_DOCKER_LABEL_DEPENDENCY_HASH"] = identity["dependency_hash"]
    env["FAKE_DOCKER_LABEL_RECIPE_HASH"] = "stale-recipe"
    env["FAKE_DOCKER_LABEL_DEPENDENCY_IMAGE_HASH"] = identity["dependency_image_hash"]
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "prod_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "prod_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_prod_compose_env(env, tmp_path)

    _write_fake_agent_secrets(fake_bin)
    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["build"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(line.startswith("buildx build --load --file Dockerfile.deps") for line in log_lines)
    assert any(
        f"--build-arg SERVICE_RECIPE_HASH={identity['recipe_hash']}" in line for line in log_lines
    )
