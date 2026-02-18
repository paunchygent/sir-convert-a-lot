#!/usr/bin/env bash
#
# Purpose:
#   Verify Hemma docker-lane multi-format conversions (service API v2) and
#   emit deterministic evidence under `build/verification/task-39-v2-smoke/`.
#
# Relationships:
#   - Local wrapper: uses `pdm run run-local-pdm run-hemma` to execute this script
#     remotely in the canonical Hemma repo root.
#   - Remote mode: runs `python -m scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions`
#     which performs the HTTP submissions and downloads artifacts.
#
# Usage:
#   pdm run run-local-pdm hemma-verify-v2-conversions
#   bash scripts/devops/verify-hemma-v2-conversions.sh --remote [args...]
#
# Notes:
#   - Defaults to verifying the Hemma docker lane (`127.0.0.1:8085`).
#   - Pass `--help` after `--remote` for python-level flags.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

if [[ "${1:-}" == "--remote" ]]; then
  shift
  exec pdm run python -m scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions "$@"
fi

exec pdm run run-local-pdm run-hemma -- bash scripts/devops/verify-hemma-v2-conversions.sh --remote "$@"

