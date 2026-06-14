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

DOCKER_CMD=(docker)
if [[ "${SIR_CONVERT_A_LOT_COMPOSE_USE_SUDO:-0}" == "1" ]]; then
  DOCKER_CMD=(sudo -n docker)
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "${COMPOSE_LABEL}: docker is not installed or not on PATH" >&2
  exit 67
fi

if ! "${DOCKER_CMD[@]}" compose version >/dev/null 2>&1; then
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

COMPOSE_CMD=("${DOCKER_CMD[@]}" compose -f "${COMPOSE_FILE}")

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
    "${COMPOSE_CMD[@]}" up -d --build "$@"
    ;;
  stop)
    if [[ "$#" -eq 0 ]]; then
      "${COMPOSE_CMD[@]}" down
    else
      "${COMPOSE_CMD[@]}" stop "$@"
    fi
    ;;
  build)
    ensure_dependency_image
    "${COMPOSE_CMD[@]}" build "$@"
    ;;
  build-clean)
    ensure_dependency_image
    "${COMPOSE_CMD[@]}" build --no-cache "$@"
    ;;
  recreate)
    ensure_dependency_image
    "${COMPOSE_CMD[@]}" up -d --force-recreate --build "$@"
    ;;
  logs)
    "${COMPOSE_CMD[@]}" logs --tail=200 "$@"
    ;;
  ps)
    "${COMPOSE_CMD[@]}" ps "$@"
    ;;
  config)
    "${COMPOSE_CMD[@]}" config "$@"
    ;;
  check)
    "${COMPOSE_CMD[@]}" config >/dev/null
    "${COMPOSE_CMD[@]}" ps
    ;;
  *)
    usage
    exit 2
    ;;
esac
