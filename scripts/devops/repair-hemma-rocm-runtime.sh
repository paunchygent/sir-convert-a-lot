#!/usr/bin/env bash
#
# Purpose:
#   Repair Hemma project torch runtime so pinned ROCm GPU execution is available.
#
# Relationships:
#   - Uses canonical wrapper `pdm run run-local-pdm run-hemma`.
#   - Validates with `gpu_runtime_probe` after reinstall.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

read_pyproject_rocm_runtime() {
  pdm run python - <<'PY'
import tomllib
from pathlib import Path

config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
runtime = config["tool"]["sir_convert_a_lot"]["rocm_runtime"]
print(runtime["torch_index_url"])
print(runtime["torch_version"])
print(runtime["torchvision_version"])
print(runtime["torchaudio_version"])
PY
}

run_remote_shell() {
  local command="$1"
  pdm run run-local-pdm run-hemma --shell "${command}"
}

cd "${REPO_ROOT}"
{
  IFS= read -r DEFAULT_TORCH_ROCM_INDEX_URL
  IFS= read -r DEFAULT_TORCH_VERSION_PIN
  IFS= read -r DEFAULT_TORCHVISION_VERSION_PIN
  IFS= read -r DEFAULT_TORCHAUDIO_VERSION_PIN
} < <(read_pyproject_rocm_runtime)

TORCH_ROCM_INDEX_URL="${SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL:-${DEFAULT_TORCH_ROCM_INDEX_URL}}"
TORCH_VERSION_PIN="${SIR_CONVERT_A_LOT_TORCH_VERSION_PIN:-${DEFAULT_TORCH_VERSION_PIN}}"
TORCHVISION_VERSION_PIN="${SIR_CONVERT_A_LOT_TORCHVISION_VERSION_PIN:-${DEFAULT_TORCHVISION_VERSION_PIN}}"
TORCHAUDIO_VERSION_PIN="${SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION_PIN:-${DEFAULT_TORCHAUDIO_VERSION_PIN}}"

TORCH_SPEC="torch==${TORCH_VERSION_PIN}"
TORCHVISION_SPEC="torchvision==${TORCHVISION_VERSION_PIN}"
TORCHAUDIO_SPEC="torchaudio==${TORCHAUDIO_VERSION_PIN}"

echo "[repair] validating host ROCm tools"
run_remote_shell "set -euo pipefail; rocm-smi --showproductname --showdriverversion >/dev/null"

echo "[repair] syncing project environment"
run_remote_shell "set -euo pipefail; pdm install --no-self"

echo "[repair] reinstalling pinned torch stack from ROCm index: ${TORCH_ROCM_INDEX_URL}"
echo "[repair] package pins: ${TORCH_SPEC} ${TORCHVISION_SPEC} ${TORCHAUDIO_SPEC}"
run_remote_shell "set -euo pipefail; pdm run python -m pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1 || true"
run_remote_shell "set -euo pipefail; pdm run python -m pip install --upgrade --no-cache-dir --index-url '${TORCH_ROCM_INDEX_URL}' '${TORCH_SPEC}' '${TORCHVISION_SPEC}' '${TORCHAUDIO_SPEC}'"

echo "[repair] validating probe after reinstall"
run_remote_shell "set -euo pipefail; pdm run python - <<'PY'
import json
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import probe_torch_gpu_runtime

probe = probe_torch_gpu_runtime()
print(json.dumps(probe.as_details(), sort_keys=True))
if probe.runtime_kind != 'rocm':
    raise SystemExit('repair failed: runtime_kind is not rocm')
if not probe.is_available:
    raise SystemExit('repair failed: torch runtime is not GPU-available')
if '+rocm' not in (probe.torch_version or ''):
    raise SystemExit(f'repair failed: torch build is not ROCm-tagged: {probe.torch_version!r}')
PY"

echo "[repair] Hemma ROCm runtime repair completed"
