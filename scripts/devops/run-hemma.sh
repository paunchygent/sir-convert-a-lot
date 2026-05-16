#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

HEMMA_HOST="${SIR_CONVERT_A_LOT_HEMMA_HOST:-hemma}"
HEMMA_ROOT="${SIR_CONVERT_A_LOT_HEMMA_ROOT:-/home/paunchygent/apps/sir-convert-a-lot}"
HEMMA_LOCAL_HOSTNAME="${SIR_CONVERT_A_LOT_HEMMA_LOCAL_HOSTNAME:-paunchygent-server}"
HEMMA_SKILL_REPOSITORY="${SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY:-/home/paunchygent/apps/skill-repository}"
REMOTE_BASH=(/bin/bash --noprofile --norc -s)

usage() {
  cat >&2 <<'EOF'
Usage:
  pdm run run-hemma -- <command> [args...]
  pdm run run-hemma --shell "<command with shell operators>"

Environment:
  SIR_CONVERT_A_LOT_HEMMA_HOST   SSH host alias (default: hemma)
  SIR_CONVERT_A_LOT_HEMMA_ROOT   Remote repo root (default: /home/paunchygent/apps/sir-convert-a-lot)
  SIR_CONVERT_A_LOT_FORCE_REMOTE_HEMMA
                                  Force SSH execution even when already on Hemma.
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

current_hostname() {
  if [[ -n "${SIR_CONVERT_A_LOT_CURRENT_HOSTNAME:-}" ]]; then
    printf '%s\n' "${SIR_CONVERT_A_LOT_CURRENT_HOSTNAME}"
    return 0
  fi
  hostname
}

current_skill_repository() {
  if [[ -n "${SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY:-}" ]]; then
    printf '%s\n' "${SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY}"
    return 0
  fi
  readlink -f "${HOME}/.codex/skill-repository" 2>/dev/null || true
}

is_hemma_local_session() {
  if [[ "${SIR_CONVERT_A_LOT_FORCE_REMOTE_HEMMA:-0}" == "1" ]]; then
    return 1
  fi

  local host
  local root
  local skill_repository
  host="$(current_hostname)"
  root="$(pwd -P)"
  skill_repository="$(current_skill_repository)"

  [[ "${host}" == "${HEMMA_LOCAL_HOSTNAME}" ]] \
    && [[ "${root}" == "${HEMMA_ROOT}" ]] \
    && [[ "${skill_repository}" == "${HEMMA_SKILL_REPOSITORY}" ]]
}

run_local_hemma() {
  local user_cmd="$1"
  local prelude
  prelude="$(remote_prelude)"
  /bin/bash --noprofile --norc -c "${prelude}; ${user_cmd}"
}

run_hemma() {
  local user_cmd="$1"
  if is_hemma_local_session; then
    run_local_hemma "${user_cmd}"
    return $?
  fi
  run_remote "${user_cmd}"
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
  run_hemma "${REMOTE_SHELL_CMD}"
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
run_hemma "${REMOTE_CMD}"
