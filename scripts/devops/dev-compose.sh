#!/usr/bin/env bash
#
# Purpose:
#   Provide the canonical local Docker Compose command surface for Sir
#   Convert-a-Lot's CPU-only laptop debug lane.
#
# Relationships:
#   - Referenced by PDM `dev-*` scripts in pyproject.toml.
#   - Operates on compose.local.yaml and delegates action mapping to
#     scripts/devops/compose-actions.sh.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export SIR_CONVERT_A_LOT_COMPOSE_LABEL="dev-compose"
export SIR_CONVERT_A_LOT_COMPOSE_FILE="${REPO_ROOT}/compose.local.yaml"
export SIR_CONVERT_A_LOT_COMPOSE_FILE_DESCRIPTION="local compose file"
export SIR_CONVERT_A_LOT_DEPS_RUNTIME="cpu"
export SIR_CONVERT_A_LOT_COMPOSE_USAGE=$'Usage:\n  pdm run dev-deps-cpu-build\n  pdm run dev-start [service...]\n  pdm run dev-stop [service...]\n  pdm run dev-build [service...]\n  pdm run dev-build-clean [service...]\n  pdm run dev-recreate [service...]\n  pdm run dev-logs [service...]\n  pdm run dev-ps [service...]\n  pdm run dev-config\n  pdm run dev-check'

exec bash "${SCRIPT_DIR}/compose-actions.sh" "$@"
