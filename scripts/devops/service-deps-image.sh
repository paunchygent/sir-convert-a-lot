#!/usr/bin/env bash
#
# Purpose:
#   Build or ensure hash-addressed Sir Convert-a-Lot service dependency images
#   from narrow generated dependency input artifacts.
#
# Relationships:
#   - Referenced by PDM `prod-deps-rocm-build` and `dev-deps-cpu-build`.
#   - Called by compose-actions.sh before app/runtime image builds.
#   - Builds Dockerfile.deps with BuildKit cache mounts for pip downloads.
#

set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  service-deps-image.sh rocm ensure
  service-deps-image.sh rocm build
  service-deps-image.sh rocm build-clean
  service-deps-image.sh cpu ensure
  service-deps-image.sh cpu build
  service-deps-image.sh cpu build-clean
EOF
}

if [[ "$#" -ne 2 ]]; then
  usage
  exit 2
fi

RUNTIME_KIND="$1"
ACTION="$2"

case "${RUNTIME_KIND}" in
  rocm)
    TARGET_STAGE="rocm-deps"
    IMAGE_REPOSITORY="${SIR_CONVERT_A_LOT_DEPS_ROCM_IMAGE_REPOSITORY:-sir-convert-a-lot-deps-rocm}"
    ;;
  cpu)
    TARGET_STAGE="cpu-deps"
    IMAGE_REPOSITORY="${SIR_CONVERT_A_LOT_DEPS_CPU_IMAGE_REPOSITORY:-sir-convert-a-lot-deps-cpu}"
    ;;
  *)
    usage
    exit 2
    ;;
esac

case "${ACTION}" in
  ensure | build | build-clean)
    ;;
  *)
    usage
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONTRACT_DIR="${REPO_ROOT}/docker/service-deps"
REQUIREMENTS_PATH="${CONTRACT_DIR}/service-requirements.txt"
PYTHON_IMAGE="${SIR_CONVERT_A_LOT_DEPS_PYTHON_IMAGE:-python:3.11-slim}"

cd "${REPO_ROOT}"

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

python -m scripts.sir_convert_a_lot.devops.export_service_requirements \
  --project-root "${REPO_ROOT}" \
  --output "${REQUIREMENTS_PATH}"

IDENTITY_OUTPUT="$(python -m scripts.sir_convert_a_lot.devops.service_dependency_inputs \
  --project-root "${REPO_ROOT}" \
  --requirements "${REQUIREMENTS_PATH}" \
  --output-dir "${CONTRACT_DIR}" \
  --runtime "${RUNTIME_KIND}" \
  --python-image "${PYTHON_IMAGE}" \
  --format shell)"

DEPENDENCY_HASH=""
RECIPE_HASH=""
DEPENDENCY_IMAGE_HASH=""
while IFS='=' read -r key value; do
  case "${key}" in
    dependency_hash)
      DEPENDENCY_HASH="${value}"
      ;;
    recipe_hash)
      RECIPE_HASH="${value}"
      ;;
    dependency_image_hash)
      DEPENDENCY_IMAGE_HASH="${value}"
      ;;
  esac
done <<<"${IDENTITY_OUTPUT}"

if [[ -z "${DEPENDENCY_HASH}" || -z "${RECIPE_HASH}" || -z "${DEPENDENCY_IMAGE_HASH}" ]]; then
  echo "service-deps-image: dependency identity helper did not emit required hashes" >&2
  echo "${IDENTITY_OUTPUT}" >&2
  exit 69
fi

HASH_IMAGE="${IMAGE_REPOSITORY}:${DEPENDENCY_IMAGE_HASH}"
LOCAL_IMAGE="${IMAGE_REPOSITORY}:local"

image_exists() {
  docker image inspect "${HASH_IMAGE}" >/dev/null 2>&1
}

image_label() {
  local label_key="$1"
  docker image inspect --format "{{ index .Config.Labels \"${label_key}\" }}" "${HASH_IMAGE}" 2>/dev/null || true
}

image_label_matches() {
  local label_key="$1"
  local expected_value="$2"
  local actual_value
  actual_value="$(image_label "${label_key}")"
  [[ "${actual_value}" == "${expected_value}" ]]
}

image_is_current() {
  image_exists \
    && image_label_matches "sir-convert-a-lot.dependency-hash" "${DEPENDENCY_HASH}" \
    && image_label_matches "sir-convert-a-lot.recipe-hash" "${RECIPE_HASH}" \
    && image_label_matches "sir-convert-a-lot.dependency-image-hash" "${DEPENDENCY_IMAGE_HASH}"
}

build_args=(
  docker build
  --file Dockerfile.deps
  --target "${TARGET_STAGE}"
  --build-arg "PYTHON_IMAGE=${PYTHON_IMAGE}"
  --build-arg "SERVICE_DEPENDENCY_HASH=${DEPENDENCY_HASH}"
  --build-arg "SERVICE_RECIPE_HASH=${RECIPE_HASH}"
  --build-arg "SERVICE_DEPENDENCY_IMAGE_HASH=${DEPENDENCY_IMAGE_HASH}"
  --tag "${HASH_IMAGE}"
  --tag "${LOCAL_IMAGE}"
)

if [[ "${ACTION}" == "build-clean" ]]; then
  build_args+=(--no-cache)
fi

build_args+=(.)

if [[ "${ACTION}" == "ensure" ]] && image_is_current; then
  docker tag "${HASH_IMAGE}" "${LOCAL_IMAGE}" >/dev/null
else
  "${build_args[@]}"
fi

printf "runtime_kind=%s\n" "${RUNTIME_KIND}"
printf "dependency_hash=%s\n" "${DEPENDENCY_HASH}"
printf "recipe_hash=%s\n" "${RECIPE_HASH}"
printf "dependency_image_hash=%s\n" "${DEPENDENCY_IMAGE_HASH}"
printf "deps_image=%s\n" "${HASH_IMAGE}"
printf "deps_image_local=%s\n" "${LOCAL_IMAGE}"
