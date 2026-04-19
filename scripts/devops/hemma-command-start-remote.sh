#!/usr/bin/env bash
#
# Purpose:
#   Start one validated Sir Convert-a-Lot Hemma command in the background.
#
# Relationships:
#   - Invoked through scripts/devops/hemma-command-start.sh.
#   - Writes durable logs and PID breadcrumbs under .artifacts/.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

usage() {
  cat >&2 <<'EOF'
Usage: bash scripts/devops/hemma-command-start-remote.sh <label> -- <remote-command> [args...]
EOF
}

if [[ "$#" -lt 3 ]]; then
  usage
  exit 2
fi

label="$1"
shift

case "${label}" in
  *[!a-zA-Z0-9_.-]*|"")
    echo "Unsupported detached command label: ${label}" >&2
    exit 2
    ;;
esac

if [[ "${1:-}" != "--" ]]; then
  usage
  exit 2
fi
shift

if [[ "$#" -lt 1 ]]; then
  usage
  exit 2
fi

mkdir -p .artifacts
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_path="${REPO_ROOT}/.artifacts/hemma-command-${label}-${run_stamp}.log"
pid_path="${REPO_ROOT}/.artifacts/hemma-command-${label}-${run_stamp}.pid"

nohup "$@" >"${log_path}" 2>&1 </dev/null &
pid="$!"
printf '%s\n' "${pid}" >"${pid_path}"

sleep 1

if ! kill -0 "${pid}" 2>/dev/null; then
  echo "Detached Hemma command failed to stay alive after launch." >&2
  echo "Remote log: ${log_path}" >&2
  if [[ -f "${log_path}" ]]; then
    tail -n 40 "${log_path}" >&2 || true
  fi
  exit 1
fi

echo "Detached Hemma command handoff succeeded."
echo "Command label: ${label}"
echo "Remote PID: ${pid}"
echo "Remote log: ${log_path}"
echo "Remote PID file: ${pid_path}"
echo "Monitor command: pdm run run-local-pdm hemma-command-monitor -- ${log_path}"
echo "Command completion status: follow the remote log or monitor command above."
