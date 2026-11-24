"""Shared fakes and fixtures for the compose wrapper test modules.

Purpose:
    Provide the fake docker/sudo/agent-secrets binaries, wrapper runners and
    lane environment fixtures shared by the local, production and remote-proof
    compose wrapper tests.

Relationships:
    - Imported by test_dev_compose_wrapper.py, test_prod_compose_wrapper.py and
      test_remote_proof_compose_wrapper.py.
"""

from __future__ import annotations

import shutil
import stat
import subprocess
import sys
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
  compose_env_files=()
  compose_args=("$@")
  for index in "${!compose_args[@]}"; do
    if [[ "${compose_args[index]}" == "--env-file" ]]; then
      compose_env_files+=("${compose_args[index + 1]}")
    fi
  done

  service_revision="${SIR_CONVERT_A_LOT_SERVICE_REVISION:-}"
  expected_revision="${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-}"
  # Compose semantics: a process-environment variable wins over every env file;
  # among env files a later file overrides an earlier one.
  for compose_env_file in "${compose_env_files[@]}"; do
    while IFS= read -r env_line || [[ -n "${env_line}" ]]; do
      case "${env_line}" in
        SIR_CONVERT_A_LOT_SERVICE_REVISION=*)
          if [[ -z "${SIR_CONVERT_A_LOT_SERVICE_REVISION:-}" ]]; then
            service_revision="${env_line#*=}"
          fi
          ;;
        SIR_CONVERT_A_LOT_EXPECTED_REVISION=*)
          if [[ -z "${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-}" ]]; then
            expected_revision="${env_line#*=}"
          fi
          ;;
      esac
    done <"${compose_env_file}"
  done

  printf "%s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
  printf "service_revision=%s expected_revision=%s\\n" \
    "${service_revision}" \
    "${expected_revision}" >>"${FAKE_DOCKER_LOG}"
  if [[ "${FAKE_DOCKER_LOG_SECRETS:-0}" == "1" ]]; then
    secret_probe_names=(
      SIR_CONVERT_A_LOT_V2_API_KEY
      HF_TOKEN
    )
    for secret_name in "${secret_probe_names[@]}"; do
      if [[ -n "${!secret_name:-}" ]]; then
        printf "secret_env %s=present\\n" "${secret_name}" >>"${FAKE_DOCKER_LOG}"
      else
        printf "secret_env %s=absent\\n" "${secret_name}" >>"${FAKE_DOCKER_LOG}"
      fi
    done
    env_secret_regex='^(SIR_CONVERT_A_LOT_V2_API_KEY|HF_TOKEN)='
    for compose_env_file in "${compose_env_files[@]}"; do
      printf "env_file_secret_lines %s=%s\\n" \
        "${compose_env_file}" \
        "$(grep -cE "${env_secret_regex}" "${compose_env_file}" || true)" \
        >>"${FAKE_DOCKER_LOG}"
      env_file_key_names="$(
        sed -n 's/^\\([A-Za-z_][A-Za-z0-9_]*\\)=.*/\\1/p' "${compose_env_file}" | paste -sd, -
      )"
      printf "env_file_keys %s=%s\\n" \
        "${compose_env_file}" \
        "${env_file_key_names}" \
        >>"${FAKE_DOCKER_LOG}"
    done
  fi
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
preserve_env_list=""
sudo_args=("$@")
while [[ "${#sudo_args[@]}" -gt 0 ]]; do
  case "${sudo_args[0]}" in
    -n)
      sudo_args=("${sudo_args[@]:1}")
      ;;
    --preserve-env=*)
      preserve_env_list="${sudo_args[0]#--preserve-env=}"
      sudo_args=("${sudo_args[@]:1}")
      ;;
    *)
      break
      ;;
  esac
done
unset SIR_CONVERT_A_LOT_SERVICE_REVISION
unset SIR_CONVERT_A_LOT_EXPECTED_REVISION
secret_probe_names=(
  SIR_CONVERT_A_LOT_V2_API_KEY
  HF_TOKEN
)
for secret_name in "${secret_probe_names[@]}"; do
  if [[ ",${preserve_env_list}," != *",${secret_name},"* ]]; then
    unset "${secret_name}"
  fi
done
exec "${sudo_args[@]}"
""",
        encoding="utf-8",
    )
    fake_sudo.chmod(fake_sudo.stat().st_mode | stat.S_IXUSR)


def _write_fake_agent_secrets(script_dir: Path) -> None:
    fake_agent_secrets = script_dir / "agent-secrets"
    fake_agent_secrets.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${FAKE_DOCKER_LOG:-}" ]]; then
  printf "agent-secrets %s\\n" "$*" >>"${FAKE_DOCKER_LOG}"
fi
set_name=""
args=("$@")
while [[ "${#args[@]}" -gt 0 ]]; do
  case "${args[0]}" in
    --set)
      set_name="${args[1]}"
      args=("${args[@]:2}")
      ;;
    --)
      args=("${args[@]:1}")
      break
      ;;
    *)
      args=("${args[@]:1}")
      ;;
  esac
done
case "${set_name}" in
  sir-convert-a-lot-prod)
    export SIR_CONVERT_A_LOT_V2_API_KEY="test-store-prod-key"
    export HF_TOKEN="test-store-hf-token"
    export AGENT_SECRETS_VARIABLES="HF_TOKEN,SIR_CONVERT_A_LOT_V2_API_KEY"
    ;;
  sir-convert-a-lot-remote-proof)
    export SIR_CONVERT_A_LOT_V2_API_KEY="test-store-remote-proof-key"
    export AGENT_SECRETS_VARIABLES="SIR_CONVERT_A_LOT_V2_API_KEY"
    ;;
  *)
    echo "fake-agent-secrets: unknown set: ${set_name}" >&2
    exit 3
    ;;
esac
exec "${args[@]}"
""",
        encoding="utf-8",
    )
    fake_agent_secrets.chmod(fake_agent_secrets.stat().st_mode | stat.S_IXUSR)


def _write_fake_python(script_dir: Path) -> None:
    real_python = sys.executable
    fake_python = script_dir / "python"
    fake_python.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail

if [[ "${{1:-}}" == "-m" \\
  && "${{2:-}}" == "scripts.sir_convert_a_lot.devops.bounded_production_startup" \\
  && "${{3:-}}" == "prepare-image" ]]; then
  if [[ "${{FAKE_PREPARE_IMAGE_EXIT:-0}}" == "0" ]]; then
    printf "image_tag=%s\\n" "${{FAKE_PREPARE_IMAGE_TAG:-fake_prepared_head}}"
    printf "outcome=succeeded\\n"
  else
    printf "outcome=failed\\n"
    exit "${{FAKE_PREPARE_IMAGE_EXIT:-0}}"
  fi
  exit 0
fi
exec "{real_python}" "$@"
""",
        encoding="utf-8",
    )
    fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)


def _write_fake_pdm(script_dir: Path) -> None:
    real_pdm = shutil.which("pdm") or "pdm"
    fake_pdm = script_dir / "pdm"
    fake_pdm.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail

if [[ "${{1:-}}" == "run" && "${{2:-}}" == "hemma-workload" ]]; then
  if [[ -n "${{FAKE_DOCKER_LOG:-}}" ]]; then
    printf "pdm %s\\n" "$*" >>"${{FAKE_DOCKER_LOG}}"
  fi
  exit "${{FAKE_PDM_EXIT:-0}}"
fi
exec "{real_pdm}" "$@"
""",
        encoding="utf-8",
    )
    fake_pdm.chmod(fake_pdm.stat().st_mode | stat.S_IXUSR)


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
                "SIR_CONVERT_A_LOT_V2_API_KEY=source-env-api-key",
                "HF_TOKEN=source-env-hf-token",
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
