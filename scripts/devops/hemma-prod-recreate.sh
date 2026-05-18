#!/usr/bin/env bash
#
# Purpose:
#   Recreate Sir Convert-a-Lot Hemma production services through one stable
#   local operator command that preserves PDM, Docker, and BuildKit paths across
#   the remote sudo boundary.
#
# Relationships:
#   - Exposed by the PDM `hemma-prod-recreate` script.
#   - Delegates to the canonical remote `prod-recreate` compose wrapper.
#   - Provides the same sudo/PATH behavior used by deploy-and-verify fallback.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

REMOTE_PDM="${SIR_CONVERT_A_LOT_HEMMA_PDM:-/home/paunchygent/.local/bin/pdm}"
REMOTE_DEPLOY_PATH="${SIR_CONVERT_A_LOT_HEMMA_DEPLOY_PATH:-/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"

usage() {
  cat >&2 <<'EOF'
Usage:
  pdm run hemma-prod-recreate [service...]

Default services:
  sir_convert_a_lot_gpu_worker sir_convert_a_lot_prod sir_convert_a_lot_public_reserved

Environment:
  SIR_CONVERT_A_LOT_HEMMA_PDM          Remote pdm executable path.
  SIR_CONVERT_A_LOT_HEMMA_DEPLOY_PATH  Remote sudo PATH containing pdm and docker.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

services=("$@")
if [[ "${#services[@]}" -eq 0 ]]; then
  services=(
    sir_convert_a_lot_gpu_worker
    sir_convert_a_lot_prod
    sir_convert_a_lot_public_reserved
  )
fi

cd "${REPO_ROOT}"

exec pdm run run-local-pdm run-hemma -- \
  sudo -n env \
  "PATH=${REMOTE_DEPLOY_PATH}" \
  "${REMOTE_PDM}" run prod-recreate "${services[@]}"
