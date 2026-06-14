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

REMOTE_PROOF_TRUST_DIR="${SIR_CONVERT_A_LOT_REMOTE_PROOF_TRUST_DIR:-/home/paunchygent/.data/sir-convert-a-lot/remote-proof/local-auth-integration}"
REMOTE_PROOF_PUBLIC_KEY_HOST_PATH="${HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH:-${REMOTE_PROOF_TRUST_DIR}/gateway-internal-identity-public-key.pem}"

if [[ -z "${HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_TRUST_PROFILE_JSON:-}" ]]; then
  echo "remote-proof-compose: HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_TRUST_PROFILE_JSON is required" >&2
  exit 70
fi
if [[ ! -f "${REMOTE_PROOF_PUBLIC_KEY_HOST_PATH}" ]]; then
  echo "remote-proof-compose: HuleEdu local-auth-integration public key PEM not found: ${REMOTE_PROOF_PUBLIC_KEY_HOST_PATH}" >&2
  exit 70
fi

export SIR_CONVERT_A_LOT_COMPOSE_LABEL="remote-proof-compose"
export SIR_CONVERT_A_LOT_COMPOSE_FILE="${REPO_ROOT}/compose.remote-proof.yaml"
export SIR_CONVERT_A_LOT_COMPOSE_FILE_DESCRIPTION="remote-proof compose file"
export SIR_CONVERT_A_LOT_DEPS_RUNTIME="rocm"
export SIR_CONVERT_A_LOT_DOCKER_USE_SUDO="1"
export HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH="${REMOTE_PROOF_PUBLIC_KEY_HOST_PATH}"
export SIR_CONVERT_A_LOT_COMPOSE_USAGE=$'Usage:\n  pdm run remote-proof-start [service...]\n  pdm run remote-proof-stop [service...]\n  pdm run remote-proof-build [service...]\n  pdm run remote-proof-build-clean [service...]\n  pdm run remote-proof-recreate [service...]\n  pdm run remote-proof-logs [service...]\n  pdm run remote-proof-ps [service...]\n  pdm run remote-proof-config\n  pdm run remote-proof-check'

exec bash "${SCRIPT_DIR}/compose-actions.sh" "$@"
