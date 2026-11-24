#!/usr/bin/env bash
#
# Purpose:
#   Execute deterministic Docker Compose actions for a caller-selected Sir
#   Convert-a-Lot compose surface.
#
# Relationships:
#   - Shared by scripts/devops/dev-compose.sh and scripts/devops/prod-compose.sh.
#   - Preserves one action mapping for local and Hemma production wrappers while
#     keeping their compose files explicit.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

COMPOSE_LABEL="${SIR_CONVERT_A_LOT_COMPOSE_LABEL:-compose-actions}"
COMPOSE_FILE="${SIR_CONVERT_A_LOT_COMPOSE_FILE:-}"
COMPOSE_FILE_DESCRIPTION="${SIR_CONVERT_A_LOT_COMPOSE_FILE_DESCRIPTION:-compose file}"
COMPOSE_USAGE="${SIR_CONVERT_A_LOT_COMPOSE_USAGE:-Usage: compose wrapper <action> [service...]}"
COMPOSE_SECRETS_FILE="${SIR_CONVERT_A_LOT_COMPOSE_SECRETS_FILE:-}"
COMPOSE_SECRETS_SET="${SIR_CONVERT_A_LOT_AGENT_SECRETS_SET:-}"
COMPOSE_SECRET_ACTIONS="${SIR_CONVERT_A_LOT_COMPOSE_SECRET_ACTIONS:-start recreate build build-clean}"
COMPOSE_RECREATE_CLAIM_START="${SIR_CONVERT_A_LOT_COMPOSE_RECREATE_CLAIM_START:-}"

usage() {
  printf "%s\n" "${COMPOSE_USAGE}" >&2
}

if [[ "$#" -lt 1 ]]; then
  usage
  exit 2
fi

if [[ -z "${COMPOSE_FILE}" ]]; then
  echo "${COMPOSE_LABEL}: compose file not configured" >&2
  exit 65
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "${COMPOSE_LABEL}: ${COMPOSE_FILE_DESCRIPTION} not found: ${COMPOSE_FILE}" >&2
  exit 66
fi

if [[ -n "${COMPOSE_SECRETS_FILE}" && ! -f "${COMPOSE_SECRETS_FILE}" ]]; then
  echo "${COMPOSE_LABEL}: compose secrets file not found: ${COMPOSE_SECRETS_FILE}" >&2
  exit 66
fi

# shellcheck source=scripts/devops/docker-command.sh
source "${SCRIPT_DIR}/docker-command.sh"
sir_convert_require_docker_command "${COMPOSE_LABEL}"

if ! "${SIR_CONVERT_DOCKER_CMD[@]}" compose version >/dev/null 2>&1; then
  echo "${COMPOSE_LABEL}: docker compose v2 plugin is not available" >&2
  exit 68
fi

ACTION="$1"
shift

cd "${REPO_ROOT}"

resolve_repo_head_revision() {
  local head_revision
  head_revision="$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || echo unknown)"
  if [[ -z "${head_revision}" ]]; then
    echo "unknown"
    return 0
  fi
  echo "${head_revision}"
}

resolved_revision="${SIR_CONVERT_A_LOT_SERVICE_REVISION:-}"
if [[ -z "${resolved_revision}" ]]; then
  resolved_revision="$(resolve_repo_head_revision)"
fi
if [[ -z "${resolved_revision}" ]]; then
  resolved_revision="unknown"
fi

resolved_expected_revision="${SIR_CONVERT_A_LOT_EXPECTED_REVISION:-${resolved_revision}}"
if [[ -z "${resolved_expected_revision}" ]]; then
  resolved_expected_revision="unknown"
fi

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"
export COMPOSE_DOCKER_CLI_BUILD="${COMPOSE_DOCKER_CLI_BUILD:-1}"
export SIR_CONVERT_A_LOT_SERVICE_REVISION="${resolved_revision}"
export SIR_CONVERT_A_LOT_EXPECTED_REVISION="${resolved_expected_revision}"

COMPOSE_SOURCE_ENV_FILE=""
if [[ -n "${SIR_CONVERT_A_LOT_COMPOSE_ENV_FILE:-}" ]]; then
  if [[ ! -f "${SIR_CONVERT_A_LOT_COMPOSE_ENV_FILE}" ]]; then
    echo "${COMPOSE_LABEL}: compose env file not found: ${SIR_CONVERT_A_LOT_COMPOSE_ENV_FILE}" >&2
    exit 66
  fi
  COMPOSE_SOURCE_ENV_FILE="${SIR_CONVERT_A_LOT_COMPOSE_ENV_FILE}"
fi

COMPOSE_DYNAMIC_ENV_FILE=""
cleanup_compose_dynamic_env_file() {
  if [[ -n "${COMPOSE_DYNAMIC_ENV_FILE}" && -f "${COMPOSE_DYNAMIC_ENV_FILE}" ]]; then
    rm -f "${COMPOSE_DYNAMIC_ENV_FILE}"
  fi
}
trap cleanup_compose_dynamic_env_file EXIT

write_compose_env_line() {
  local key="$1"
  local value="${!key:-}"
  if [[ -z "${value}" ]]; then
    return 0
  fi
  if [[ "${value}" == *$'\n'* ]]; then
    echo "${COMPOSE_LABEL}: compose env value contains a newline: ${key}" >&2
    exit 70
  fi
  printf "%s=%s\n" "${key}" "${value}"
}

prepare_compose_dynamic_env_file() {
  if [[ -z "${COMPOSE_SOURCE_ENV_FILE}" || -n "${COMPOSE_DYNAMIC_ENV_FILE}" ]]; then
    return 0
  fi

  local dynamic_keys=(
    SIR_CONVERT_A_LOT_DEPS_IMAGE
    SIR_CONVERT_A_LOT_SERVICE_REVISION
    SIR_CONVERT_A_LOT_EXPECTED_REVISION
    HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH
  )
  local has_dynamic_values=0
  local key
  for key in "${dynamic_keys[@]}"; do
    if [[ -n "${!key:-}" ]]; then
      has_dynamic_values=1
      break
    fi
  done
  if [[ "${has_dynamic_values}" == "0" ]]; then
    return 0
  fi
  local compose_env_snapshot_dir="${SIR_CONVERT_A_LOT_COMPOSE_ENV_SNAPSHOT_DIR:-${REPO_ROOT}/build/compose-env}"
  mkdir -p "${compose_env_snapshot_dir}"
  chmod 700 "${compose_env_snapshot_dir}"
  COMPOSE_DYNAMIC_ENV_FILE="$(mktemp "${compose_env_snapshot_dir}/sir-convert-compose-env.XXXXXX")"
  chmod 600 "${COMPOSE_DYNAMIC_ENV_FILE}"
  for key in "${dynamic_keys[@]}"; do
    write_compose_env_line "${key}" >>"${COMPOSE_DYNAMIC_ENV_FILE}"
  done
}

refresh_compose_command() {
  prepare_compose_dynamic_env_file
  local compose_env_args=()
  if [[ -n "${COMPOSE_SOURCE_ENV_FILE}" ]]; then
    compose_env_args+=(--env-file "${COMPOSE_SOURCE_ENV_FILE}")
  fi
  if [[ -n "${COMPOSE_DYNAMIC_ENV_FILE}" ]]; then
    compose_env_args+=(--env-file "${COMPOSE_DYNAMIC_ENV_FILE}")
  fi
  COMPOSE_CMD=("${SIR_CONVERT_DOCKER_CMD[@]}" compose "${compose_env_args[@]}" -f "${COMPOSE_FILE}")
}

run_compose() {
  refresh_compose_command
  "${COMPOSE_CMD[@]}" "$@"
}

action_needs_secrets() {
  [[ " ${COMPOSE_SECRET_ACTIONS} " == *" $1 "* ]]
}

run_compose_wrapped() {
  refresh_compose_command
  local wrapped_cmd=("${COMPOSE_CMD[@]}")
  if [[ -n "${COMPOSE_SECRETS_FILE}" ]]; then
    wrapped_cmd+=(-f "${COMPOSE_SECRETS_FILE}")
  fi
  wrapped_cmd+=("$@")
  if ! command -v agent-secrets >/dev/null 2>&1; then
    echo "${COMPOSE_LABEL}: agent-secrets is required to inject set ${COMPOSE_SECRETS_SET}" >&2
    exit 67
  fi
  if [[ "${SIR_CONVERT_DOCKER_CMD[0]:-}" == "sudo" ]]; then
    # COMPOSE_CMD starts with `sudo -n`; re-wrap it so the variables agent-secrets
    # injected survive sudo env_reset inside the agent-secrets child process.
    agent-secrets run --set "${COMPOSE_SECRETS_SET}" -- \
      bash -c "exec sudo -n --preserve-env=\"\$AGENT_SECRETS_VARIABLES\" \"\$@\"" \
      bash "${wrapped_cmd[@]:2}"
  else
    agent-secrets run --set "${COMPOSE_SECRETS_SET}" -- "${wrapped_cmd[@]}"
  fi
}

run_compose_for_action() {
  local action="$1"
  shift
  if [[ -n "${COMPOSE_SECRETS_SET}" ]] && action_needs_secrets "${action}"; then
    run_compose_wrapped "$@"
  else
    run_compose "$@"
  fi
}

ensure_dependency_image() {
  local deps_runtime="${SIR_CONVERT_A_LOT_DEPS_RUNTIME:-}"
  if [[ -z "${deps_runtime}" ]]; then
    return 0
  fi

  local deps_output
  deps_output="$(bash "${SCRIPT_DIR}/service-deps-image.sh" "${deps_runtime}" ensure)"
  while IFS='=' read -r key value; do
    if [[ "${key}" == "deps_image" ]]; then
      export SIR_CONVERT_A_LOT_DEPS_IMAGE="${value}"
      return 0
    fi
  done <<<"${deps_output}"

  echo "${COMPOSE_LABEL}: dependency image helper did not emit deps_image" >&2
  echo "${deps_output}" >&2
  exit 69
}

case "${ACTION}" in
  start)
    ensure_dependency_image
    run_compose_for_action start up -d --build "$@"
    ;;
  stop)
    if [[ "$#" -eq 0 ]]; then
      run_compose_for_action stop down
    else
      run_compose_for_action stop stop "$@"
    fi
    ;;
  build)
    ensure_dependency_image
    run_compose_for_action build build "$@"
    ;;
  build-clean)
    ensure_dependency_image
    run_compose_for_action build-clean build --no-cache "$@"
    ;;
  recreate)
    ensure_dependency_image
    if [[ -n "${COMPOSE_RECREATE_CLAIM_START}" ]]; then
      run_compose_for_action recreate up -d --no-start --no-build --no-deps --force-recreate "$@"
      bash "${COMPOSE_RECREATE_CLAIM_START}"
    else
      run_compose_for_action recreate up -d --force-recreate --build "$@"
    fi
    ;;
  logs)
    run_compose_for_action logs logs --tail=200 "$@"
    ;;
  ps)
    run_compose_for_action ps ps "$@"
    ;;
  config)
    run_compose_for_action config config "$@"
    ;;
  check)
    run_compose_for_action config config >/dev/null
    run_compose_for_action ps ps
    ;;
  *)
    usage
    exit 2
    ;;
esac
