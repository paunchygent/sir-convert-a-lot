#!/usr/bin/env bash
#
# Purpose:
#   Build the Hemma Qwen3.6 llama.cpp provider binary with the bounded
#   concurrency and niceness required by the GPU runbook.
#
# Relationships:
#   - Exposed by PDM as `qwen-llama-provider-build`.
#   - Produces the canonical `/srv/scratch/sir-convert-a-lot/bin/llama-server`
#     symlink consumed by the production Qwen provider container.
#   - Keeps the heavyweight HIP build outside Docker Compose service startup.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"
# shellcheck source=scripts/devops/require-hemma-server.sh
source "${SCRIPT_DIR}/require-hemma-server.sh"
sir_convert_require_hemma_server "qwen-llama-provider-build"

LLAMA_CPP_SOURCE_ROOT="${SIR_CONVERT_A_LOT_LLAMA_CPP_SOURCE_ROOT:-/srv/scratch/sir-convert-a-lot/build/llama.cpp-qwen35}"
LLAMA_CPP_BUILD_DIR="${SIR_CONVERT_A_LOT_LLAMA_CPP_BUILD_DIR:-${LLAMA_CPP_SOURCE_ROOT}/build-hip}"
LLAMA_CPP_BUILD_JOBS="${SIR_CONVERT_A_LOT_LLAMA_CPP_BUILD_JOBS:-8}"
LLAMA_CPP_BUILD_NICE="${SIR_CONVERT_A_LOT_LLAMA_CPP_BUILD_NICE:-10}"
MAX_LLAMA_CPP_BUILD_JOBS=8
MIN_LLAMA_CPP_BUILD_NICE=10
CANONICAL_LLAMA_SERVER="/srv/scratch/sir-convert-a-lot/bin/llama-server"

require_integer() {
  local name="$1"
  local value="$2"
  if [[ ! "${value}" =~ ^[0-9]+$ ]]; then
    echo "qwen-llama-provider-build: ${name} must be a positive integer, got: ${value}" >&2
    exit 64
  fi
}

require_integer "SIR_CONVERT_A_LOT_LLAMA_CPP_BUILD_JOBS" "${LLAMA_CPP_BUILD_JOBS}"
require_integer "SIR_CONVERT_A_LOT_LLAMA_CPP_BUILD_NICE" "${LLAMA_CPP_BUILD_NICE}"

if (( LLAMA_CPP_BUILD_JOBS < 1 || LLAMA_CPP_BUILD_JOBS > MAX_LLAMA_CPP_BUILD_JOBS )); then
  echo "qwen-llama-provider-build: build jobs must be between 1 and ${MAX_LLAMA_CPP_BUILD_JOBS}; runbook default is -j8." >&2
  exit 64
fi

if (( LLAMA_CPP_BUILD_NICE < MIN_LLAMA_CPP_BUILD_NICE )); then
  echo "qwen-llama-provider-build: nice value must be >= ${MIN_LLAMA_CPP_BUILD_NICE}; runbook default is nice -n 10." >&2
  exit 64
fi

if [[ ! -d "${LLAMA_CPP_SOURCE_ROOT}" ]]; then
  echo "qwen-llama-provider-build: llama.cpp source root missing: ${LLAMA_CPP_SOURCE_ROOT}" >&2
  exit 66
fi

cmake -S "${LLAMA_CPP_SOURCE_ROOT}" -B "${LLAMA_CPP_BUILD_DIR}" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS=gfx1201 \
  -DGGML_HIP_GRAPHS=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON

nice -n "${LLAMA_CPP_BUILD_NICE}" ninja -C "${LLAMA_CPP_BUILD_DIR}" -j"${LLAMA_CPP_BUILD_JOBS}" llama-server

mkdir -p "$(dirname "${CANONICAL_LLAMA_SERVER}")"
ln -sfn "${LLAMA_CPP_BUILD_DIR}/bin/llama-server" "${CANONICAL_LLAMA_SERVER}"

printf 'llama_server=%s\n' "${CANONICAL_LLAMA_SERVER}"
printf 'source_root=%s\n' "${LLAMA_CPP_SOURCE_ROOT}"
printf 'build_dir=%s\n' "${LLAMA_CPP_BUILD_DIR}"
printf 'build_jobs=%s\n' "${LLAMA_CPP_BUILD_JOBS}"
printf 'build_nice=%s\n' "${LLAMA_CPP_BUILD_NICE}"
