#!/usr/bin/env bash
#
# Purpose:
#   Provide the canonical Hemma remote-proof Docker Compose command surface for
#   Sir Convert-a-Lot local-auth STT proof.
#
# Relationships:
#   - Referenced by PDM `remote-proof-*` scripts in pyproject.toml.
#   - Operates on compose.remote-proof.yaml and stays separate from production
#     compose and local CPU-only dev-compose lanes.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"
# shellcheck source=scripts/devops/require-hemma-server.sh
source "${SCRIPT_DIR}/require-hemma-server.sh"
sir_convert_require_hemma_server "remote-proof-compose"

REMOTE_PROOF_ENV_FILE="${SIR_CONVERT_A_LOT_REMOTE_PROOF_ENV_FILE:-/home/paunchygent/.data/sir-convert-a-lot/remote-proof/remote-proof.env}"
if [[ -f "${REMOTE_PROOF_ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${REMOTE_PROOF_ENV_FILE}"
  set +a
fi

export SIR_CONVERT_A_LOT_COMPOSE_LABEL="remote-proof-compose"
export SIR_CONVERT_A_LOT_COMPOSE_FILE="${REPO_ROOT}/compose.remote-proof.yaml"
export SIR_CONVERT_A_LOT_COMPOSE_FILE_DESCRIPTION="remote-proof compose file"
export SIR_CONVERT_A_LOT_DEPS_RUNTIME="rocm"
export SIR_CONVERT_A_LOT_COMPOSE_USAGE=$'Usage:\n  pdm run remote-proof-start [service...]\n  pdm run remote-proof-stop [service...]\n  pdm run remote-proof-build [service...]\n  pdm run remote-proof-build-clean [service...]\n  pdm run remote-proof-recreate [service...]\n  pdm run remote-proof-logs [service...]\n  pdm run remote-proof-ps [service...]\n  pdm run remote-proof-config\n  pdm run remote-proof-check'

exec bash "${SCRIPT_DIR}/compose-actions.sh" "$@"
