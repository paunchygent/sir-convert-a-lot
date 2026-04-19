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

cd "${REPO_ROOT}"

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

python -m scripts.sir_convert_a_lot.devops.export_service_requirements \
  --project-root "${REPO_ROOT}" \
  --output "${REQUIREMENTS_PATH}"

DEPENDENCY_HASH="$(python -m scripts.sir_convert_a_lot.devops.service_dependency_inputs \
  --project-root "${REPO_ROOT}" \
  --requirements "${REQUIREMENTS_PATH}" \
  --output-dir "${CONTRACT_DIR}" \
  --runtime "${RUNTIME_KIND}")"

HASH_IMAGE="${IMAGE_REPOSITORY}:${DEPENDENCY_HASH}"
LOCAL_IMAGE="${IMAGE_REPOSITORY}:local"

image_exists() {
  docker image inspect "${HASH_IMAGE}" >/dev/null 2>&1
}

build_args=(
  docker build
  --file Dockerfile.deps
  --target "${TARGET_STAGE}"
  --build-arg "SERVICE_DEPENDENCY_HASH=${DEPENDENCY_HASH}"
  --tag "${HASH_IMAGE}"
  --tag "${LOCAL_IMAGE}"
)

if [[ "${ACTION}" == "build-clean" ]]; then
  build_args+=(--no-cache)
fi

build_args+=(.)

if [[ "${ACTION}" == "ensure" ]] && image_exists; then
  docker tag "${HASH_IMAGE}" "${LOCAL_IMAGE}" >/dev/null
else
  "${build_args[@]}"
fi

printf "runtime_kind=%s\n" "${RUNTIME_KIND}"
printf "dependency_hash=%s\n" "${DEPENDENCY_HASH}"
printf "deps_image=%s\n" "${HASH_IMAGE}"
printf "deps_image_local=%s\n" "${LOCAL_IMAGE}"
