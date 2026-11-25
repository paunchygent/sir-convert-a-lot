#!/usr/bin/env bash
#
# Purpose:
#   Redeploy Sir Convert-a-Lot production through the shared `hemma-services`
#   claim so a recreated deployment honors the shared GPU claim queue.
#
# Relationships:
#   - Referenced by scripts/devops/prod-compose.sh as the claim step of the
#     production `recreate` action.
#   - Ends with `hemma-services redeploy sir-production`, which prints one JSON
#     line with `outcome`, `reason`, `target_identity` and `transaction_id`
#     (null when the refusal precedes a transaction); the command's exit code
#     is the result (0 succeeded, 3 queued, 1 otherwise). Redeploy starts the
#     claim when unheld, replaces a held claim, and is refused when the claim
#     is suspended.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

if [[ "$#" -gt 0 ]]; then
  printf '%s\n' "Usage: pdm run prod-recreate" >&2
  exit 2
fi

exec hemma-services redeploy sir-production
