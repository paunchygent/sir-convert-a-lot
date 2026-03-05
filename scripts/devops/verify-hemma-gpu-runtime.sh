#!/usr/bin/env bash
#
# Purpose:
#   Verify Hemma GPU runtime compliance through a committed Python command
#   surface and deterministic remote execution context.
#
# Relationships:
#   - Local mode delegates to `run-hemma` wrapper in argv mode.
#   - Remote mode executes `scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime`.
#
# Usage:
#   pdm run run-local-pdm hemma-verify-gpu-runtime
#   bash scripts/devops/verify-hemma-gpu-runtime.sh --remote [args...]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

if [[ "${1:-}" == "--remote" ]]; then
  shift
  exec pdm run python -m scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime "$@"
fi

exec pdm run run-local-pdm run-hemma -- bash scripts/devops/verify-hemma-gpu-runtime.sh --remote "$@"
