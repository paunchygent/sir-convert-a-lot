#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

HEMMA_HOST="${SIR_CONVERT_A_LOT_HEMMA_HOST:-hemma}"
HEMMA_ROOT="${SIR_CONVERT_A_LOT_HEMMA_ROOT:-/home/paunchygent/apps/sir-convert-a-lot}"
REMOTE_BASH=(/bin/bash --noprofile --norc -s)

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

remote_prelude() {
  local root_q
  root_q="$(printf '%q' "${HEMMA_ROOT}")"
  printf '%s' \
    "set -euo pipefail; " \
    "SIR_HEMMA_ROOT=${root_q}; " \
    "if [[ ! -d \"\${SIR_HEMMA_ROOT}\" ]]; then " \
    "echo \"run-hemma: remote root not found: \${SIR_HEMMA_ROOT}\" >&2; " \
    "exit 66; " \
    "fi; " \
    "if [[ ! -d \"\${SIR_HEMMA_ROOT}/.git\" && ! -f \"\${SIR_HEMMA_ROOT}/.git\" ]]; then " \
    "echo \"run-hemma: remote root is not a git repository: \${SIR_HEMMA_ROOT}\" >&2; " \
    "exit 67; " \
    "fi; " \
    "cd \"\${SIR_HEMMA_ROOT}\"; " \
    "SIR_HEMMA_EXPECTED_ROOT=\"\$(cd \"\${SIR_HEMMA_ROOT}\" && pwd -P)\"; " \
    "SIR_HEMMA_ACTUAL_ROOT=\"\$(pwd -P)\"; " \
    "if [[ \"\${SIR_HEMMA_ACTUAL_ROOT}\" != \"\${SIR_HEMMA_EXPECTED_ROOT}\" ]]; then " \
    "echo \"run-hemma: remote cwd mismatch: expected \${SIR_HEMMA_EXPECTED_ROOT}, got \${SIR_HEMMA_ACTUAL_ROOT}\" >&2; " \
    "exit 68; " \
    "fi; " \
    "export PATH=\"\${HOME}/.local/bin:\${PATH}\""
}

run_remote() {
  local user_cmd="$1"
  local prelude
  prelude="$(remote_prelude)"
  local remote_script
  remote_script="${prelude}; ${user_cmd}"
  ssh "${HEMMA_HOST}" "${REMOTE_BASH[@]}" <<<"${remote_script}"
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
  run_remote "${REMOTE_SHELL_CMD}"
  exit $?
fi

if [[ "$1" == "--" ]]; then
  shift
fi

if [[ "$#" -eq 0 ]]; then
  usage
  exit 2
fi

REMOTE_CMD="$(quote_args "$@")"
run_remote "${REMOTE_CMD}"
