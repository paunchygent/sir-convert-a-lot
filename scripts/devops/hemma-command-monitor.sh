#!/usr/bin/env bash
#
# Purpose:
#   Monitor a detached Sir Convert-a-Lot Hemma command log.
#
# Relationships:
#   - Delegates to scripts/devops/hemma-command-monitor-remote.sh on Hemma.
#   - Complements scripts/devops/hemma-command-start.sh.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

remote_log_path=""
raw_mode=0

usage() {
  cat >&2 <<'EOF'
Usage: pdm run run-local-pdm hemma-command-monitor [--raw] [remote-log-path]

Without an explicit remote log path, the latest remote
.artifacts/hemma-command-*.log is selected.

Options:
  --raw    Stream the selected log without milestone/failure filtering.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --raw)
      raw_mode=1
      shift
      ;;
    --)
      shift
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      if [[ -n "${remote_log_path}" ]]; then
        echo "Only one remote log path may be provided." >&2
        usage
        exit 2
      fi
      remote_log_path="$1"
      shift
      ;;
  esac
done

remote_args=()
if [[ "${raw_mode}" -eq 1 ]]; then
  remote_args+=(--raw)
fi
remote_args+=("${remote_log_path}")

exec pdm run run-local-pdm run-hemma -- bash scripts/devops/hemma-command-monitor-remote.sh "${remote_args[@]}"
