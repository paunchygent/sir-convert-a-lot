#!/usr/bin/env bash
#
# Purpose:
#   Provide the Hemma-only command surface for bounded production startup.
#
# Relationships:
#   - Referenced by the PDM `prod-start-bounded` script in pyproject.toml.
#   - Delegates bounded startup orchestration to its typed Python coordinator.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"
# shellcheck source=scripts/devops/require-hemma-server.sh
source "${SCRIPT_DIR}/require-hemma-server.sh"
guard_status=0
sir_convert_require_hemma_server "prod-start-bounded" || guard_status="$?"
if [[ "${guard_status}" -ne 0 ]]; then
  printf '%s\n' 'outcome=failed'
  exit "${guard_status}"
fi

export SIR_CONVERT_A_LOT_DOCKER_USE_SUDO="1"
exec python -m scripts.sir_convert_a_lot.devops.bounded_production_startup
