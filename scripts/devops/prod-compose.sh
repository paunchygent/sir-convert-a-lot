#!/usr/bin/env bash
#
# Purpose:
#   Provide the canonical production Docker Compose command surface for Sir
#   Convert-a-Lot on Hemma.
#
# Relationships:
#   - Referenced by PDM `prod-*` scripts in pyproject.toml.
#   - Operates on compose.yaml and stays separate from the local CPU-only
#     dev-compose lane.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"
# shellcheck source=scripts/devops/require-hemma-server.sh
source "${SCRIPT_DIR}/require-hemma-server.sh"
sir_convert_require_hemma_server "prod-compose"

export SIR_CONVERT_A_LOT_COMPOSE_LABEL="prod-compose"
export SIR_CONVERT_A_LOT_COMPOSE_FILE="${REPO_ROOT}/compose.yaml"
export SIR_CONVERT_A_LOT_COMPOSE_FILE_DESCRIPTION="production compose file"
export SIR_CONVERT_A_LOT_DEPS_RUNTIME="rocm"
export SIR_CONVERT_A_LOT_COMPOSE_USAGE=$'Usage:\n  pdm run prod-deps-rocm-build\n  pdm run prod-deps-rocm-build-clean\n  pdm run prod-start [service...]\n  pdm run prod-stop [service...]\n  pdm run prod-build [service...]\n  pdm run prod-build-clean [service...]\n  pdm run prod-recreate [service...]\n  pdm run prod-logs [service...]\n  pdm run prod-ps [service...]\n  pdm run prod-config\n  pdm run prod-check'

exec bash "${SCRIPT_DIR}/compose-actions.sh" "$@"
