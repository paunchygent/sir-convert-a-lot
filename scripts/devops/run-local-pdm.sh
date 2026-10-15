#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "$#" -lt 1 ]]; then
  echo "Usage: pdm run run-local-pdm <pdm-script> [args...]" >&2
  exit 2
fi

cd "${REPO_ROOT}"

exec pdm run "$@"
