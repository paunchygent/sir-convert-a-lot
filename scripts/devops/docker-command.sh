#!/usr/bin/env bash
#
# Purpose:
#   Resolve the Docker CLI invocation for Sir Convert-a-Lot devops wrappers.
#
# Relationships:
#   - Sourced by compose and dependency-image helpers that need the same host
#     Docker access policy.
#   - Keeps Hemma sudo Docker access explicit without coupling helpers to a
#     specific compose or build workflow.
#

sir_convert_resolve_docker_command() {
  if [[ "${SIR_CONVERT_A_LOT_DOCKER_USE_SUDO:-0}" == "1" ]]; then
    SIR_CONVERT_DOCKER_CMD=(sudo -n docker)
  else
    SIR_CONVERT_DOCKER_CMD=(docker)
  fi
}

sir_convert_require_docker_command() {
  local label="$1"
  if ! command -v docker >/dev/null 2>&1; then
    echo "${label}: docker is not installed or not on PATH" >&2
    exit 67
  fi
  if [[ "${SIR_CONVERT_A_LOT_DOCKER_USE_SUDO:-0}" == "1" ]] && ! command -v sudo >/dev/null 2>&1; then
    echo "${label}: sudo is required for SIR_CONVERT_A_LOT_DOCKER_USE_SUDO=1" >&2
    exit 67
  fi
  sir_convert_resolve_docker_command
}
