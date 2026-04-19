#!/usr/bin/env bash
#
# Purpose:
#   Follow or replay detached Sir Convert-a-Lot Hemma command logs.
#
# Relationships:
#   - Invoked through scripts/devops/hemma-command-monitor.sh.
#   - Selects logs produced by scripts/devops/hemma-command-start-remote.sh.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

requested_log_path=""
raw_mode=0

usage() {
  cat >&2 <<'EOF'
Usage: bash scripts/devops/hemma-command-monitor-remote.sh [--raw] [remote-log-path]
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --raw)
      raw_mode=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
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
      if [[ -n "${requested_log_path}" ]]; then
        echo "Only one remote log path may be provided." >&2
        usage
        exit 2
      fi
      requested_log_path="$1"
      shift
      ;;
  esac
done

select_latest_command_log() {
  local candidate base stamp latest_log latest_stamp
  latest_log=""
  latest_stamp=""

  shopt -s nullglob
  for candidate in "${REPO_ROOT}"/.artifacts/hemma-command-*.log; do
    base="$(basename "${candidate}")"
    if [[ "${base}" =~ ^hemma-command-.+-([0-9]{8}T[0-9]{6}Z)\.log$ ]]; then
      stamp="${BASH_REMATCH[1]}"
      if [[ -z "${latest_stamp}" || "${stamp}" > "${latest_stamp}" ]]; then
        latest_stamp="${stamp}"
        latest_log="${candidate}"
      fi
    fi
  done
  shopt -u nullglob

  printf '%s\n' "${latest_log}"
}

if [[ -n "${requested_log_path}" ]]; then
  log_path="${requested_log_path}"
else
  if [[ ! -d "${REPO_ROOT}/.artifacts" ]]; then
    echo "No Hemma command logs found under ${REPO_ROOT}/.artifacts." >&2
    exit 1
  fi
  log_path="$(select_latest_command_log)"
  if [[ -z "${log_path}" ]]; then
    echo "No Hemma command logs found under ${REPO_ROOT}/.artifacts." >&2
    exit 1
  fi
fi

if [[ ! -f "${log_path}" ]]; then
  echo "Remote command log not found: ${log_path}" >&2
  exit 1
fi

pattern='(^== )|(^==>)|(passed\.)|(warn(ing)?)|(error)|(failed)|(fatal)|(exception)|(traceback)|(refus(ed|ing)?)|(blocked)|(missing)|(complete)|(healthy)|(created)|(started)'

echo "Monitoring remote log: ${log_path}" >&2
if [[ "${raw_mode}" -eq 1 ]]; then
  echo "Replaying existing log, then following raw output..." >&2
  cat "${log_path}"
else
  echo "Replaying existing milestone/failure lines, then following filtered updates..." >&2
  grep -Ei "${pattern}" "${log_path}" || true
fi

tail_args=(-n 0 -F "${log_path}")
session_parent_pid="$(ps -o ppid= -p "$$" | tr -d '[:space:]' || true)"
if [[ -n "${session_parent_pid}" && "${session_parent_pid}" != "1" ]]; then
  if tail --help 2>/dev/null | grep -q -- '--pid'; then
    tail_args=(--pid="${session_parent_pid}" "${tail_args[@]}")
  fi
fi

if [[ "${raw_mode}" -eq 1 ]]; then
  exec tail "${tail_args[@]}"
fi

tail "${tail_args[@]}" 2>&1 | grep --line-buffered -Ei "${pattern}" || true
