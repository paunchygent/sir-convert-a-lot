"""Tests for host-local Hemma command guards.

Purpose:
    Ensure Hemma Server-only command surfaces fail before touching Docker or
    shared production env paths when executed from a client-like environment.

Relationships:
    - Protects environment-aware PDM script behavior around production compose
      and ROCm dependency image helpers.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROD_COMPOSE = REPO_ROOT / "scripts" / "devops" / "prod-compose.sh"
SERVICE_DEPS_IMAGE = REPO_ROOT / "scripts" / "devops" / "service-deps-image.sh"
SYNC_PROD_ENV_MIRROR = REPO_ROOT / "scripts" / "devops" / "sync-prod-env-mirror.sh"


def _client_like_env() -> dict[str, str]:
    env = os.environ.copy()
    env["SIR_CONVERT_A_LOT_CURRENT_HOSTNAME"] = "not-hemma"
    env["SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY"] = "/tmp/not-skill-repository"
    return env


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        env=_client_like_env(),
        text=True,
        capture_output=True,
    )


def test_prod_compose_refuses_client_like_environment_before_docker() -> None:
    result = _run_script(["bash", str(PROD_COMPOSE), "ps"])

    assert result.returncode == 70
    assert "prod-compose: this command is Hemma Server-only" in result.stderr
    assert "Use: pdm run run-hemma -- <command> [args...]" in result.stderr


def test_rocm_dependency_image_refuses_client_like_environment_before_build() -> None:
    result = _run_script(["bash", str(SERVICE_DEPS_IMAGE), "rocm", "ensure"])

    assert result.returncode == 70
    assert "service-deps-image rocm: this command is Hemma Server-only" in result.stderr
    assert "docker build" not in result.stderr


def test_prod_env_mirror_refuses_client_like_environment_before_host_paths() -> None:
    result = _run_script(["bash", str(SYNC_PROD_ENV_MIRROR)])

    assert result.returncode == 70
    assert "sync-prod-env-mirror: this command is Hemma Server-only" in result.stderr
    assert "[sync-prod-env]" not in result.stderr
