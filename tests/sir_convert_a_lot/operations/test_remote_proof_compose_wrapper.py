"""Wrapper tests for the remote-proof deterministic compose execution surface.

Purpose:
    Ensure the Hemma remote-proof Docker Compose wrapper routes mutating
    actions through the remote-proof secrets overlay and agent-secrets set
    while diagnostic actions stay on the base files without the store.

Relationships:
    - Exercises `scripts/devops/remote-proof-compose.sh`.
    - Shares fakes with the local and production wrapper tests through
      `tests.sir_convert_a_lot.operations.compose_wrapper_fakes`.
"""

from __future__ import annotations

import os
from pathlib import Path

from tests.sir_convert_a_lot.operations.compose_wrapper_fakes import (
    REMOTE_PROOF_COMPOSE_SCRIPT,
    REPO_ROOT,
    _run_wrapper,
    _with_fake_hemma_env,
    _with_fake_remote_proof_trust_env,
    _write_fake_agent_secrets,
    _write_fake_docker,
    _write_fake_sudo,
)


def test_remote_proof_wrapper_routes_compose_and_deps_through_shared_sudo_docker(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    _write_fake_agent_secrets(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["FAKE_DOCKER_LOG_BUILDS"] = "1"
    env["FAKE_DOCKER_LOG_SECRETS"] = "1"
    env["SIR_CONVERT_A_LOT_COMPOSE_ENV_SNAPSHOT_DIR"] = str(tmp_path)
    env["SIR_CONVERT_A_LOT_PRUNE_SUPERSEDED_DEPS_IMAGES"] = "1"
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "remote_proof_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "remote_proof_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_remote_proof_trust_env(env, tmp_path)

    result = _run_wrapper(REMOTE_PROOF_COMPOSE_SCRIPT, ["start"], env)
    assert result.returncode == 0

    log_text = log_file.read_text(encoding="utf-8")
    log_lines = log_text.splitlines()
    assert "sudo -n docker compose version" in log_text
    assert "sudo -n docker image inspect" in log_text
    assert "sudo -n docker buildx build" in log_text
    assert "sudo -n docker image ls" in log_text
    assert "sudo -n docker ps --format" in log_text
    assert "agent-secrets run --set sir-convert-a-lot-remote-proof -- bash -c" in log_text
    assert (
        "sudo -n --preserve-env=SIR_CONVERT_A_LOT_V2_API_KEY docker compose --env-file" in log_text
    )
    assert (
        f"--env-file {tmp_path / 'remote-proof.env'} "
        f"--env-file {tmp_path}/sir-convert-compose-env." in log_text
    )
    assert f"-f {REPO_ROOT / 'compose.remote-proof.yaml'}" in log_text
    assert f"-f {REPO_ROOT / 'compose.remote-proof.secrets.yaml'}" in log_text
    assert "compose.secrets.yaml" not in log_text
    assert "secret_env SIR_CONVERT_A_LOT_V2_API_KEY=present" in log_text
    assert f"env_file_secret_lines {tmp_path / 'remote-proof.env'}=0" in log_lines
    keys_prefix = f"env_file_keys {tmp_path}/sir-convert-compose-env."
    keys_line = next(line for line in log_lines if line.startswith(keys_prefix))
    generated_keys = set(keys_line.split("=", maxsplit=1)[1].split(","))
    assert generated_keys == {
        "SIR_CONVERT_A_LOT_DEPS_IMAGE",
        "SIR_CONVERT_A_LOT_SERVICE_REVISION",
        "SIR_CONVERT_A_LOT_EXPECTED_REVISION",
        "HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH",
    }
    env_secret_line = next(
        line
        for line in log_lines
        if line.startswith(f"env_file_secret_lines {tmp_path}/sir-convert-compose-env.")
    )
    assert env_secret_line.endswith("=0")
    assert "superseded dependency image cleanup failed" not in result.stderr
    assert not list(tmp_path.glob("sir-convert-compose-env.*"))


def test_remote_proof_compose_ps_uses_base_files_without_agent_secrets(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    _write_fake_agent_secrets(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "remote_proof_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "remote_proof_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_remote_proof_trust_env(env, tmp_path)

    result = _run_wrapper(REMOTE_PROOF_COMPOSE_SCRIPT, ["ps"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert not any(line.startswith("agent-secrets") for line in log_lines)
    compose_line = next(line for line in log_lines if line.endswith(" ps"))
    assert f"-f {REPO_ROOT / 'compose.remote-proof.yaml'}" in compose_line
    assert "secrets.yaml" not in compose_line


def test_remote_proof_wrapper_fails_before_docker_when_trust_key_is_missing(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_docker(fake_bin)
    _write_fake_sudo(fake_bin)
    log_file = tmp_path / "docker.log"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log_file)
    env["SIR_CONVERT_A_LOT_REMOTE_PROOF_TRUST_DIR"] = str(tmp_path / "missing-trust")
    env["SIR_CONVERT_A_LOT_REMOTE_PROOF_ENV_FILE"] = str(tmp_path / "remote-proof.env")
    Path(env["SIR_CONVERT_A_LOT_REMOTE_PROOF_ENV_FILE"]).write_text(
        "HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_TRUST_PROFILE_JSON='{}'\n",
        encoding="utf-8",
    )
    env["HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_TRUST_PROFILE_JSON"] = (
        '{"key_id":"gateway-identity-rs256-v1"}'
    )
    env.pop("HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH", None)
    env = _with_fake_hemma_env(env)

    result = _run_wrapper(REMOTE_PROOF_COMPOSE_SCRIPT, ["start"], env)

    assert result.returncode == 70
    assert "public key PEM not found" in result.stderr
    assert not log_file.exists()
