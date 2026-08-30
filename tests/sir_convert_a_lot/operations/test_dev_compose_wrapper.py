"""Wrapper tests for deterministic compose execution surfaces.

Purpose:
    Ensure the local and production Docker Compose wrappers enforce
    deterministic command behavior, revision wiring, and canonical action
    mappings without sharing compose files accidentally.

Relationships:
    - Exercises `scripts/devops/dev-compose.sh`.
    - Exercises `scripts/devops/prod-compose.sh`.
    - Protects compose command-surface compose command-surface contracts.
    - Protects public-edge verification local/prod compose surface separation.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

from scripts.sir_convert_a_lot.devops.service_dependency_inputs import (
    build_project_dependency_image_identity_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "dev-compose.sh"
PROD_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "prod-compose.sh"
REMOTE_PROOF_COMPOSE_SCRIPT = REPO_ROOT / "scripts" / "devops" / "remote-proof-compose.sh"
SERVICE_REQUIREMENTS = REPO_ROOT / "docker" / "service-deps" / "service-requirements.txt"


def _write_fake_docker(script_dir: Path) -> None:
    fake_docker = script_dir / "docker"
    fake_docker.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  compose)
    shift
    ;;
  image)
    case "${2:-}" in
      inspect)
        if [[ "${FAKE_DOCKER_IMAGE_EXISTS:-0}" != "1" ]]; then
          exit 1
        fi
        if [[ "${3:-}" == "--format" ]]; then
          case "${4:-}" in
            *sir-convert-a-lot.dependency-hash*)
              echo "${FAKE_DOCKER_LABEL_DEPENDENCY_HASH:-}"
              ;;
            *sir-convert-a-lot.recipe-hash*)
              echo "${FAKE_DOCKER_LABEL_RECIPE_HASH:-}"
              ;;
            *sir-convert-a-lot.dependency-image-hash*)
              echo "${FAKE_DOCKER_LABEL_DEPENDENCY_IMAGE_HASH:-}"
              ;;
            *)
              echo ""
              ;;
          esac
        fi
        exit 0
        ;;
      ls)
        if [[ -n "${FAKE_DOCKER_LOG:-}" && "${FAKE_DOCKER_LOG_BUILDS:-0}" == "1" ]]; then
          printf "image ls %s\\n" "${*:3}" >>"${FAKE_DOCKER_LOG}"
        fi
        exit 0
        ;;
      rm)
        if [[ -n "${FAKE_DOCKER_LOG:-}" && "${FAKE_DOCKER_LOG_BUILDS:-0}" == "1" ]]; then
          printf "image rm %s\\n" "${*:3}" >>"${FAKE_DOCKER_LOG}"
        fi
        exit 0
        ;;
    esac
    echo "fake-docker: unsupported image command: $*" >&2
    exit 90
    ;;
  ps)
    if [[ -n "${FAKE_DOCKER_LOG:-}" && "${FAKE_DOCKER_LOG_BUILDS:-0}" == "1" ]]; then
      printf "ps %s\\n" "${*:2}" >>"${FAKE_DOCKER_LOG}"
    fi
    exit 0
    ;;
  build)
    shift
    if [[ -n "${FAKE_DOCKER_LOG:-}" && "${FAKE_DOCKER_LOG_BUILDS:-0}" == "1" ]]; then
      printf "build %s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
    fi
    exit 0
    ;;
  buildx)
    if [[ "${2:-}" != "build" ]]; then
      echo "fake-docker: unsupported buildx command: $*" >&2
      exit 90
    fi
    shift 2
    if [[ -n "${FAKE_DOCKER_LOG:-}" && "${FAKE_DOCKER_LOG_BUILDS:-0}" == "1" ]]; then
      printf "buildx build %s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
    fi
    exit 0
    ;;
  tag)
    shift
    if [[ -n "${FAKE_DOCKER_LOG:-}" && "${FAKE_DOCKER_LOG_BUILDS:-0}" == "1" ]]; then
      printf "tag %s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
    fi
    exit 0
    ;;
  *)
    echo "fake-docker: expected compose/buildx/build/image/tag command, got: $*" >&2
    exit 90
    ;;
esac

if [[ "${1:-}" == "version" ]]; then
  echo "Docker Compose version v2.fake"
  exit 0
fi

if [[ -n "${FAKE_DOCKER_LOG:-}" ]]; then
  compose_env_file=""
  compose_args=("$@")
  for index in "${!compose_args[@]}"; do
    if [[ "${compose_args[index]}" == "--env-file" ]]; then
      compose_env_file="${compose_args[index + 1]}"
      break
    fi
  done

  service_revision="${SIR_CONVERT_A_LOT_SERVICE_REVISION:-}"
  expected_revision="${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-}"
  if [[ -n "${compose_env_file}" ]]; then
    while IFS= read -r env_line || [[ -n "${env_line}" ]]; do
      case "${env_line}" in
        SIR_CONVERT_A_LOT_SERVICE_REVISION=*)
          service_revision="${env_line#*=}"
          ;;
        SIR_CONVERT_A_LOT_EXPECTED_REVISION=*)
          expected_revision="${env_line#*=}"
          ;;
      esac
    done <"${compose_env_file}"
  fi

  printf "%s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
  printf "service_revision=%s expected_revision=%s\\n" \
    "${service_revision}" \
    "${expected_revision}" >>"${FAKE_DOCKER_LOG}"
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


def _write_fake_sudo(script_dir: Path) -> None:
    fake_sudo = script_dir / "sudo"
    fake_sudo.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${FAKE_DOCKER_LOG:-}" ]]; then
  printf "sudo %s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
fi
if [[ "${1:-}" == "-n" ]]; then
  shift
fi
unset SIR_CONVERT_A_LOT_SERVICE_REVISION
unset SIR_CONVERT_A_LOT_EXPECTED_REVISION
exec "$@"
""",
        encoding="utf-8",
    )
    fake_sudo.chmod(fake_sudo.stat().st_mode | stat.S_IXUSR)


def _run_wrapper(
    script_path: Path, args: list[str], env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(script_path), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def _with_fake_hemma_env(env: dict[str, str]) -> dict[str, str]:
    """Return env values that satisfy the production-wrapper Hemma guard."""
    updated = dict(env)
    updated["SIR_CONVERT_A_LOT_CURRENT_HOSTNAME"] = "test-hemma"
    updated["SIR_CONVERT_A_LOT_HEMMA_LOCAL_HOSTNAME"] = "test-hemma"
    updated["SIR_CONVERT_A_LOT_HEMMA_ROOT"] = str(REPO_ROOT)
    updated["SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY"] = str(REPO_ROOT / ".test-skills")
    updated["SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY"] = str(REPO_ROOT / ".test-skills")
    return updated


def _with_fake_prod_compose_env(env: dict[str, str], tmp_path: Path) -> dict[str, str]:
    """Provide isolated source and snapshot directories for production Compose tests."""
    updated = dict(env)
    source_env = tmp_path / "prod-compose.env"
    source_env.write_text(
        "\n".join(
            (
                "SIR_CONVERT_A_LOT_SERVICE_REVISION=source_service_revision",
                "SIR_CONVERT_A_LOT_EXPECTED_REVISION=source_expected_revision",
                "UNRELATED_SOURCE_VALUE=not-observed",
                "",
            )
        ),
        encoding="utf-8",
    )
    snapshot_dir = tmp_path / "compose-env-snapshots"
    updated["SIR_CONVERT_A_LOT_COMPOSE_ENV_FILE"] = str(source_env)
    updated["SIR_CONVERT_A_LOT_COMPOSE_ENV_SNAPSHOT_DIR"] = str(snapshot_dir)
    return updated


def _with_fake_remote_proof_trust_env(env: dict[str, str], tmp_path: Path) -> dict[str, str]:
    updated = dict(env)
    trust_dir = tmp_path / "remote-proof-trust"
    trust_dir.mkdir(parents=True)
    (trust_dir / "gateway-internal-identity-public-key.pem").write_text(
        "-----BEGIN PUBLIC KEY-----\nfake-test-key\n-----END PUBLIC KEY-----\n",
        encoding="utf-8",
    )
    remote_proof_env = tmp_path / "remote-proof.env"
    remote_proof_env.write_text(
        "\n".join(
            (
                "SIR_CONVERT_A_LOT_REMOTE_PROOF_V2_API_KEY=test-api-key",
                (
                    "HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_TRUST_PROFILE_JSON="
                    '\'{"key_id":"gateway-identity-rs256-v1"}\''
                ),
                "",
            )
        ),
        encoding="utf-8",
    )
    updated["SIR_CONVERT_A_LOT_REMOTE_PROOF_ENV_FILE"] = str(remote_proof_env)
    updated["SIR_CONVERT_A_LOT_REMOTE_PROOF_TRUST_DIR"] = str(trust_dir)
    updated.pop("HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_TRUST_PROFILE_JSON", None)
    updated.pop("HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH", None)
    return updated


def _current_rocm_identity() -> dict[str, str]:
    payload = build_project_dependency_image_identity_payload(
        project_root=REPO_ROOT,
        requirements_text=SERVICE_REQUIREMENTS.read_text(encoding="utf-8"),
        runtime_kind="rocm",
    )
    return {
        "dependency_hash": str(payload["dependency_hash"]),
        "dependency_image_hash": str(payload["dependency_image_hash"]),
        "recipe_hash": str(payload["recipe_hash"]),
    }


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


def test_prod_compose_recreate_maps_to_production_compose_surface(tmp_path: Path) -> None:
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

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["recreate", "sir_convert_a_lot_prod"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    sudo_compose_line = next(
        line for line in log_lines if line.startswith("sudo -n docker compose --env-file ")
    )
    snapshot_path = Path(sudo_compose_line.split(" --env-file ", maxsplit=1)[1].split(" -f ")[0])
    assert snapshot_path.parent == tmp_path / "compose-env-snapshots"
    assert snapshot_path.name.startswith("sir-convert-compose-env.")
    assert str(tmp_path / "prod-compose.env") not in sudo_compose_line
    assert (
        f"--env-file {snapshot_path} -f {REPO_ROOT / 'compose.yaml'} "
        "up -d --force-recreate --build sir_convert_a_lot_prod"
    ) in log_lines
    assert "service_revision=prod_rev expected_revision=prod_rev" in log_lines
    assert not snapshot_path.exists()


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

    result = _run_wrapper(PROD_COMPOSE_SCRIPT, ["build"], env)
    assert result.returncode == 0

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(line.startswith("buildx build --load --file Dockerfile.deps") for line in log_lines)
    assert any(
        f"--build-arg SERVICE_RECIPE_HASH={identity['recipe_hash']}" in line for line in log_lines
    )


def test_remote_proof_wrapper_routes_compose_and_deps_through_shared_sudo_docker(
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
    env["FAKE_DOCKER_LOG_BUILDS"] = "1"
    env["SIR_CONVERT_A_LOT_COMPOSE_ENV_SNAPSHOT_DIR"] = str(tmp_path)
    env["SIR_CONVERT_A_LOT_PRUNE_SUPERSEDED_DEPS_IMAGES"] = "1"
    env["SIR_CONVERT_A_LOT_SERVICE_REVISION"] = "remote_proof_rev"
    env["SIR_CONVERT_A_LOT_EXPECTED_REVISION"] = "remote_proof_rev"
    env = _with_fake_hemma_env(env)
    env = _with_fake_remote_proof_trust_env(env, tmp_path)

    result = _run_wrapper(REMOTE_PROOF_COMPOSE_SCRIPT, ["start"], env)
    assert result.returncode == 0

    log_text = log_file.read_text(encoding="utf-8")
    assert "sudo -n docker compose version" in log_text
    assert "sudo -n docker image inspect" in log_text
    assert "sudo -n docker buildx build" in log_text
    assert "sudo -n docker image ls" in log_text
    assert "sudo -n docker ps --format" in log_text
    assert "sudo -n docker compose --env-file" in log_text
    assert f"--env-file {tmp_path}/sir-convert-compose-env." in log_text
    assert f"--env-file {tmp_path / 'remote-proof.env'}" not in log_text
    assert f"-f {REPO_ROOT / 'compose.remote-proof.yaml'}" in log_text
    assert "superseded dependency image cleanup failed" not in result.stderr
    assert not list(tmp_path.glob("sir-convert-compose-env.*"))


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
