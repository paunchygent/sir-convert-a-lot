#!/usr/bin/env bash
#
# Purpose:
#   Set v2 async push feature flags in Hemma's canonical prod env for Sir Convert-a-Lot.
#
# Relationships:
#   - Reads/writes the canonical env file under ~/infrastructure/env/prod.
#   - Intended to be invoked via the canonical wrapper:
# pdm run run-local-pdm run-hemma -- bash scripts/devops/set-prod-push-flags.sh --sse 1 --onboarding
# 1 --delivery 0
#   - After updating flags, the service container must be recreated to pick up env changes.
#

set -euo pipefail

ENV_PATH="/home/paunchygent/infrastructure/env/prod/sir-convert-a-lot.env"

usage() {
  cat >&2 <<'EOF'
Usage:
  bash scripts/devops/set-prod-push-flags.sh --sse 0|1 --onboarding 0|1 --delivery 0|1

Notes:
  - This updates only feature flags; it does not restart docker compose.
  - Secrets are never printed.
EOF
}

require_bit() {
  local name="$1"
  local value="$2"
  if [[ "${value}" != "0" && "${value}" != "1" ]]; then
    echo "set-prod-push-flags: ${name} must be 0 or 1 (got: ${value})" >&2
    exit 2
  fi
}

ensure_key() {
  local file_path="$1"
  local key_name="$2"
  local key_value="$3"
  local tmp_file
  tmp_file="$(mktemp)"

  if [[ -f "${file_path}" ]]; then
    awk -v key="${key_name}" -v value="${key_value}" '
      BEGIN { updated = 0 }
      $0 ~ ("^" key "=") {
        if (!updated) {
          print key "=" value
          updated = 1
        }
        next
      }
      { print }
      END {
        if (!updated) {
          print key "=" value
        }
      }
    ' "${file_path}" >"${tmp_file}"
  else
    printf '%s=%s\n' "${key_name}" "${key_value}" >"${tmp_file}"
  fi

  mv "${tmp_file}" "${file_path}"
}

if [[ "$#" -eq 0 ]]; then
  usage
  exit 2
fi

sse=""
onboarding=""
delivery=""

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --sse)
      sse="${2:-}"
      shift 2
      ;;
    --onboarding)
      onboarding="${2:-}"
      shift 2
      ;;
    --delivery)
      delivery="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "set-prod-push-flags: unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${sse}" || -z "${onboarding}" || -z "${delivery}" ]]; then
  echo "set-prod-push-flags: missing required flags" >&2
  usage
  exit 2
fi

require_bit "sse" "${sse}"
require_bit "onboarding" "${onboarding}"
require_bit "delivery" "${delivery}"

mkdir -p "$(dirname "${ENV_PATH}")"

ensure_key "${ENV_PATH}" "SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM" "${sse}"
ensure_key "${ENV_PATH}" "SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_ONBOARDING" "${onboarding}"
ensure_key "${ENV_PATH}" "SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY" "${delivery}"

chmod 600 "${ENV_PATH}"

echo "[set-prod-push-flags] updated push flags at ${ENV_PATH}"

