#!/usr/bin/env bash
#
# Purpose:
#   Provide a canonical local Docker Compose command surface for Sir Convert-a-Lot.
#
# Relationships:
#   - Referenced by PDM scripts in pyproject.toml (dev-start/dev-stop/etc).
#   - Operates on compose.yaml at repository root.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose.yaml"

usage() {
  cat >&2 <<'EOF'
Usage:
  pdm run dev-start [service...]
  pdm run dev-stop [service...]
  pdm run dev-build [service...]
  pdm run dev-build-clean [service...]
  pdm run dev-recreate [service...]
  pdm run dev-logs [service...]
  pdm run dev-ps [service...]
  pdm run dev-config
  pdm run dev-check
EOF
}

if [[ "$#" -lt 1 ]]; then
  usage
  exit 2
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "dev-compose: compose file not found: ${COMPOSE_FILE}" >&2
  exit 66
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "dev-compose: docker is not installed or not on PATH" >&2
  exit 67
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "dev-compose: docker compose v2 plugin is not available" >&2
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

export SIR_CONVERT_A_LOT_SERVICE_REVISION="${resolved_revision}"
export SIR_CONVERT_A_LOT_EXPECTED_REVISION="${resolved_expected_revision}"

COMPOSE_CMD=(docker compose -f "${COMPOSE_FILE}")

case "${ACTION}" in
  start)
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
    "${COMPOSE_CMD[@]}" build "$@"
    ;;
  build-clean)
    "${COMPOSE_CMD[@]}" build --no-cache "$@"
    ;;
  recreate)
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
