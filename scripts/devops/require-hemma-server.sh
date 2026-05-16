#!/usr/bin/env bash
#
# Purpose:
#   Guard command surfaces that are valid only inside the canonical Hemma
#   Server checkout.
#
# Relationships:
#   - Sourced by production and ROCm Docker helpers before host-local mutation.
#   - Mirrors the direct-Hemma detection used by scripts/devops/run-hemma.sh.
#

set -euo pipefail

SIR_CONVERT_A_LOT_REQUIRED_HEMMA_HOSTNAME="${SIR_CONVERT_A_LOT_HEMMA_LOCAL_HOSTNAME:-paunchygent-server}"
SIR_CONVERT_A_LOT_REQUIRED_HEMMA_ROOT="${SIR_CONVERT_A_LOT_HEMMA_ROOT:-/home/paunchygent/apps/sir-convert-a-lot}"
SIR_CONVERT_A_LOT_REQUIRED_SKILL_REPOSITORY="${SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY:-/home/paunchygent/apps/skill-repository}"

sir_convert_current_hostname() {
  if [[ -n "${SIR_CONVERT_A_LOT_CURRENT_HOSTNAME:-}" ]]; then
    printf '%s\n' "${SIR_CONVERT_A_LOT_CURRENT_HOSTNAME}"
    return 0
  fi
  hostname
}

sir_convert_current_skill_repository() {
  if [[ -n "${SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY:-}" ]]; then
    printf '%s\n' "${SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY}"
    return 0
  fi
  readlink -f "${HOME}/.codex/skill-repository" 2>/dev/null || true
}

sir_convert_require_hemma_server() {
  local label="$1"
  local current_hostname
  local current_root
  local current_skill_repository

  current_hostname="$(sir_convert_current_hostname)"
  current_root="$(pwd -P)"
  current_skill_repository="$(sir_convert_current_skill_repository)"

  if [[ "${current_hostname}" == "${SIR_CONVERT_A_LOT_REQUIRED_HEMMA_HOSTNAME}" ]] \
    && [[ "${current_root}" == "${SIR_CONVERT_A_LOT_REQUIRED_HEMMA_ROOT}" ]] \
    && [[ "${current_skill_repository}" == "${SIR_CONVERT_A_LOT_REQUIRED_SKILL_REPOSITORY}" ]]; then
    return 0
  fi

  cat >&2 <<EOF
${label}: this command is Hemma Server-only.
  hostname: ${current_hostname}
  repo root: ${current_root}
  skill repository: ${current_skill_repository:-<missing>}

Use: pdm run run-hemma -- <command> [args...]
EOF
  return 70
}
