#!/usr/bin/env bash
#
# Purpose:
#   Start Sir Convert-a-Lot production through the owner's Hemma workload
#   claim so every operator start honors the shared GPU claim queue.
#
# Relationships:
#   - Referenced by the PDM `prod-start` and `prod-start-bounded` scripts in
#     pyproject.toml.
#   - Ends with `pdm run hemma-workload start sir-production <transaction-id>`;
#     the claim's exit code is the result (0 succeeded, 3 queued, 1 otherwise).
#   - The claim adapter's internal start is the PDM `prod-workload-start`
#     script, which keeps this command from recursing.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

transaction_id="$(python3 -c 'import uuid; print(uuid.uuid4())')"
exec pdm run hemma-workload start sir-production "${transaction_id}"
