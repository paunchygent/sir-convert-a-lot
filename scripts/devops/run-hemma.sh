#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

HEMMA_HOST="${SIR_CONVERT_A_LOT_HEMMA_HOST:-hemma}"
HEMMA_ROOT="${SIR_CONVERT_A_LOT_HEMMA_ROOT:-/home/paunchygent/apps/sir-convert-a-lot}"

usage() {
  cat >&2 <<'EOF'
Usage:
  pdm run run-hemma -- <command> [args...]
  pdm run run-hemma --shell "<command with shell operators>"

Environment:
  SIR_CONVERT_A_LOT_HEMMA_HOST   SSH host alias (default: hemma)
  SIR_CONVERT_A_LOT_HEMMA_ROOT   Remote repo root (default: /home/paunchygent/apps/sir-convert-a-lot)
EOF
}

quote_args() {
  local out=""
  local arg
  for arg in "$@"; do
    out+="$(printf '%q' "${arg}") "
  done
  printf '%s' "${out% }"
}

cd "${REPO_ROOT}"

if [[ "$#" -eq 0 ]]; then
  usage
  exit 2
fi

if [[ "$1" == "--shell" ]]; then
  if [[ "$#" -ne 2 ]]; then
    usage
    exit 2
  fi
  REMOTE_SHELL_CMD="$2"
  exec ssh "${HEMMA_HOST}" /bin/bash -lc "cd $(printf '%q' "${HEMMA_ROOT}") && ${REMOTE_SHELL_CMD}"
fi

if [[ "$1" == "--" ]]; then
  shift
fi

if [[ "$#" -eq 0 ]]; then
  usage
  exit 2
fi

REMOTE_CMD="$(quote_args "$@")"
exec ssh "${HEMMA_HOST}" /bin/bash -lc "cd $(printf '%q' "${HEMMA_ROOT}") && ${REMOTE_CMD}"
