#!/usr/bin/env bash
#
# Purpose:
#   Launch one Sir Convert-a-Lot Hemma command as a detached remote process.
#
# Relationships:
#   - Delegates to scripts/devops/hemma-command-start-remote.sh on Hemma.
#   - Provides the local operator entrypoint for long-running deploy commands.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

usage() {
  cat >&2 <<'EOF'
Usage: pdm run run-local-pdm hemma-command-start <label> -- <remote-command> [args...]

Examples:
  pdm run run-local-pdm hemma-command-start sir-prod-recreate -- sudo -n /home/paunchygent/.local/bin/pdm run prod-recreate sir_convert_a_lot_prod
  pdm run run-local-pdm hemma-command-monitor
EOF
}

if [[ "$#" -lt 3 ]]; then
  usage
  exit 2
fi

label="$1"
shift

if [[ "${1:-}" != "--" ]]; then
  usage
  exit 2
fi
shift

case "${label}" in
  *[!a-zA-Z0-9_.-]*|"")
    echo "Unsupported detached command label: ${label}" >&2
    exit 2
    ;;
esac

if [[ "$#" -lt 1 ]]; then
  usage
  exit 2
fi

remote_command=(bash scripts/devops/hemma-command-start-remote.sh "${label}" -- "$@")
exec pdm run run-local-pdm run-hemma -- "${remote_command[@]}"
