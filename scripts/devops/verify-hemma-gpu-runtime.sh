#!/usr/bin/env bash
#
# Purpose:
#   Verify Hemma GPU runtime compliance for Sir Convert-a-Lot before Task 12 runs.
#
# Relationships:
#   - Uses canonical wrapper `pdm run run-local-pdm run-hemma`.
#   - Validates `gpu_runtime_probe` + live conversion metadata truth.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

read_pyproject_rocm_runtime() {
  pdm run python - <<'PY'
import tomllib
from pathlib import Path

config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
runtime = config["tool"]["sir_convert_a_lot"]["rocm_runtime"]
print(runtime["torch_version"])
PY
}

API_KEY="${SIR_CONVERT_A_LOT_API_KEY:-dev-only-key}"
SERVICE_URL="${SIR_CONVERT_A_LOT_VERIFY_SERVICE_URL:-http://127.0.0.1:28085}"
EVAL_URL="${SIR_CONVERT_A_LOT_VERIFY_EVAL_URL:-http://127.0.0.1:28086}"
VERIFY_FIXTURE="${SIR_CONVERT_A_LOT_VERIFY_FIXTURE:-tests/fixtures/benchmark_pdfs/paper_alpha.pdf}"
VERIFY_TIMEOUT_SECONDS="${SIR_CONVERT_A_LOT_VERIFY_TIMEOUT_SECONDS:-180}"

run_remote_shell() {
  local command="$1"
  pdm run run-local-pdm run-hemma --shell "${command}"
}

cd "${REPO_ROOT}"
PINNED_TORCH_VERSION="${SIR_CONVERT_A_LOT_VERIFY_TORCH_VERSION_PIN:-$(read_pyproject_rocm_runtime)}"

echo "[verify] checking ROCm visibility"
run_remote_shell "set -euo pipefail; rocm-smi --showproductname --showuse --showmemuse >/tmp/sir_rocm_verify.log; grep -Eq 'GPU\\[[0-9]+\\]' /tmp/sir_rocm_verify.log"

echo "[verify] checking torch runtime probe"
run_remote_shell "set -euo pipefail; VERIFY_TORCH_VERSION_PIN='${PINNED_TORCH_VERSION}' pdm run python - <<'PY'
import json
import os
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import probe_torch_gpu_runtime

probe = probe_torch_gpu_runtime()
print(json.dumps(probe.as_details(), sort_keys=True))
if probe.runtime_kind != 'rocm':
    raise SystemExit('runtime_kind is not rocm')
if not probe.is_available:
    raise SystemExit('torch runtime is not GPU-available')
if '+rocm' not in (probe.torch_version or ''):
    raise SystemExit(f'torch build is not ROCm-tagged: {probe.torch_version!r}')
expected_torch_version = os.environ['VERIFY_TORCH_VERSION_PIN']
if expected_torch_version and probe.torch_version != expected_torch_version:
    raise SystemExit(
        f'torch version mismatch: expected={expected_torch_version!r} actual={probe.torch_version!r}'
    )
PY"

echo "[verify] checking service listener + health"
run_remote_shell "set -euo pipefail; ss -ltn | grep -q ':28085 '; curl -fsS '${SERVICE_URL}/healthz' >/dev/null"

echo "[verify] checking optional evaluation listener + health"
run_remote_shell "set -euo pipefail; if ss -ltn | grep -q ':28086 '; then curl -fsS '${EVAL_URL}/healthz' >/dev/null; else echo '[verify] eval service not running on 28086 (optional)'; fi"

echo "[verify] running live conversion + GPU utilization sampling"
run_remote_shell "set -euo pipefail; VERIFY_API_KEY='${API_KEY}' VERIFY_SERVICE_URL='${SERVICE_URL}' VERIFY_FIXTURE='${VERIFY_FIXTURE}' VERIFY_TIMEOUT_SECONDS='${VERIFY_TIMEOUT_SECONDS}' pdm run python - <<'PY'
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import httpx

service_url = os.environ['VERIFY_SERVICE_URL']
api_key = os.environ['VERIFY_API_KEY']
fixture_path = Path(os.environ['VERIFY_FIXTURE'])
timeout_seconds = float(os.environ['VERIFY_TIMEOUT_SECONDS'])

if not fixture_path.exists():
    raise SystemExit(f'fixture not found: {fixture_path}')

job_spec = {
    'api_version': 'v1',
    'source': {'kind': 'upload', 'filename': fixture_path.name},
    'conversion': {
        'output_format': 'md',
        'backend_strategy': 'auto',
        'ocr_mode': 'off',
        'table_mode': 'accurate',
        'normalize': 'standard',
    },
    'execution': {
        'acceleration_policy': 'gpu_required',
        'priority': 'normal',
        'document_timeout_seconds': 1800,
    },
    'retention': {'pin': False},
}

file_bytes = fixture_path.read_bytes()
idem = 'verify_gpu_' + hashlib.sha256(file_bytes).hexdigest()[:24] + '_' + str(int(time.time()))

headers = {'X-API-Key': api_key, 'Idempotency-Key': idem}
gpu_busy_seen = 0

with httpx.Client(base_url=service_url, timeout=30.0) as client:
    response = client.post(
        '/v1/convert/jobs?wait_seconds=0',
        files={
            'file': (fixture_path.name, file_bytes, 'application/pdf'),
            'job_spec': (None, json.dumps(job_spec, separators=(',', ':'))),
        },
        headers=headers,
    )
    response.raise_for_status()
    payload = response.json()
    job = payload.get('job', {})
    job_id = job.get('job_id')
    if not isinstance(job_id, str):
        raise SystemExit('missing job_id in create response')

    deadline = time.monotonic() + timeout_seconds
    final_status = None
    while time.monotonic() < deadline:
        smi_output = subprocess.run(
            ['rocm-smi', '--showuse'],
            check=False,
            capture_output=True,
            text=True,
        ).stdout
        for match in re.finditer(r'GPU use \\(%\\):\\s*([0-9]+)', smi_output):
            gpu_busy_seen = max(gpu_busy_seen, int(match.group(1)))

        status_response = client.get(f'/v1/convert/jobs/{job_id}', headers={'X-API-Key': api_key})
        status_response.raise_for_status()
        status_payload = status_response.json()
        final_status = status_payload.get('job', {}).get('status')
        if final_status in {'succeeded', 'failed', 'canceled'}:
            break
        time.sleep(0.2)

    if final_status != 'succeeded':
        raise SystemExit(f'job did not succeed, status={final_status!r}')

    result_response = client.get(
        f'/v1/convert/jobs/{job_id}/result?inline=true',
        headers={'X-API-Key': api_key},
    )
    result_response.raise_for_status()
    result_payload = result_response.json()
    result_obj = result_payload.get('result', {})
    metadata = result_obj.get('conversion_metadata', {})
    warnings_obj = result_obj.get('warnings', [])
    if metadata.get('acceleration_used') != 'cuda':
        raise SystemExit(f'acceleration_used mismatch: {metadata.get(\"acceleration_used\")!r}')
    if any('docling_cuda_unavailable_fallback_cpu' in str(item) for item in warnings_obj):
        raise SystemExit('unexpected cpu-fallback warning found in result')
    if gpu_busy_seen <= 0:
        raise SystemExit('rocm-smi never observed non-zero GPU busy during conversion')

    print(
        json.dumps(
            {
                'job_id': job_id,
                'acceleration_used': metadata.get('acceleration_used'),
                'gpu_busy_peak': gpu_busy_seen,
            },
            sort_keys=True,
        )
    )
PY"

echo "[verify] Hemma GPU runtime verification passed"
