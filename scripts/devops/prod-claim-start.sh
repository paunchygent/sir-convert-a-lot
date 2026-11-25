#!/usr/bin/env bash
#
# Purpose:
#   Start Sir Convert-a-Lot production through the shared `hemma-services`
#   claim so every operator start honors the shared GPU claim queue.
#
# Relationships:
#   - Referenced by the PDM `prod-start` and `prod-start-bounded` scripts in
#     pyproject.toml.
#   - Ends with `hemma-services claim sir-production`, which prints one JSON
#     line with `outcome`, `reason`, `target_identity` and `transaction_id`
#     (null when the refusal precedes a transaction); the command's exit code
#     is the result (0 succeeded, 3 queued, 1 otherwise).
#   - The claim adapter's internal start is the PDM `prod-workload-start`
#     script, which keeps this command from recursing.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

if [[ "$#" -gt 0 ]]; then
  printf '%s\n' "Usage: pdm run prod-start" "       pdm run prod-start-bounded" >&2
  exit 2
fi

exec hemma-services claim sir-production
