#!/usr/bin/env bash
set -euo pipefail

APPS_ROOT="/home/paunchygent/apps"
ENV_ROOT="/home/paunchygent/infrastructure/env/prod"

repos=(
  "sir-convert-a-lot"
  "huleedu"
  "skriptoteket"
  "projektveckor-portal"
)

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

if [[ ! -d "${APPS_ROOT}" ]]; then
  echo "[sync-prod-env] apps root not found: ${APPS_ROOT}" >&2
  exit 1
fi

mkdir -p "${ENV_ROOT}"
chmod 700 "/home/paunchygent/infrastructure/env" "${ENV_ROOT}"

sir_source_env="${APPS_ROOT}/sir-convert-a-lot/.env"
if [[ ! -f "${sir_source_env}" ]]; then
  echo "[sync-prod-env] missing source env: ${sir_source_env}" >&2
  exit 1
fi

sir_key_line="$(grep -m1 '^SIR_CONVERT_A_LOT_API_KEY=' "${sir_source_env}" || true)"
if [[ -z "${sir_key_line}" ]]; then
  echo "[sync-prod-env] missing SIR_CONVERT_A_LOT_API_KEY in ${sir_source_env}" >&2
  exit 1
fi
sir_key_value="${sir_key_line#SIR_CONVERT_A_LOT_API_KEY=}"

for repo in "${repos[@]}"; do
  repo_env="${APPS_ROOT}/${repo}/.env"
  canonical_env="${ENV_ROOT}/${repo}.env"

  if [[ ! -e "${repo_env}" && ! -L "${repo_env}" ]]; then
    echo "[sync-prod-env] missing repo env for ${repo}: ${repo_env}" >&2
    exit 1
  fi

  if [[ -f "${repo_env}" && ! -L "${repo_env}" ]]; then
    cp "${repo_env}" "${canonical_env}"
  elif [[ ! -f "${canonical_env}" ]]; then
    cp "${repo_env}" "${canonical_env}"
  fi

  ensure_key "${canonical_env}" "SIR_CONVERT_A_LOT_API_KEY" "${sir_key_value}"
  if [[ "${repo}" == "sir-convert-a-lot" ]]; then
    ensure_key "${canonical_env}" "SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE" "easyocr"
    ensure_key "${canonical_env}" "SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES" "sv,en"
    ensure_key "${canonical_env}" "SIR_CONVERT_A_LOT_EASYOCR_MODEL_STORAGE_DIR" "/opt/easyocr-models"
  fi
  if [[ "${repo}" == "projektveckor-portal" ]]; then
    ensure_key "${canonical_env}" "PVP_SIR_CONVERT_A_LOT_API_KEY" "${sir_key_value}"
  fi

  chmod 600 "${canonical_env}"
  ln -sfn "${canonical_env}" "${repo_env}"
done

echo "[sync-prod-env] mirrored canonical envs under ${ENV_ROOT} and refreshed symlinks."
