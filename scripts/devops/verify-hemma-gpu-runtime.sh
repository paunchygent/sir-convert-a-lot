#!/usr/bin/env bash
#
# Purpose:
#   Verify Hemma GPU runtime compliance for Sir Convert-a-Lot v2 single-runtime service.
#
# Relationships:
#   - Uses canonical wrapper `pdm run run-local-pdm run-hemma`.
#   - Validates `gpu_runtime_probe` + live conversion metadata truth.
#

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
VERIFY_LANE="${SIR_CONVERT_A_LOT_VERIFY_LANE:-host}"
VERIFY_FIXTURE="${SIR_CONVERT_A_LOT_VERIFY_FIXTURE:-tests/fixtures/benchmark_pdfs/paper_alpha.pdf}"
VERIFY_TIMEOUT_SECONDS="${SIR_CONVERT_A_LOT_VERIFY_TIMEOUT_SECONDS:-180}"
DOCKER_PROD_CONTAINER="${SIR_CONVERT_A_LOT_VERIFY_DOCKER_PROD_CONTAINER:-sir_convert_a_lot_prod}"

case "${VERIFY_LANE}" in
  host)
    SERVICE_URL="${SIR_CONVERT_A_LOT_VERIFY_SERVICE_URL:-http://127.0.0.1:28085}"
    REQUIRED_LISTENER_PORT=28085
    ;;
  docker)
    SERVICE_URL="${SIR_CONVERT_A_LOT_VERIFY_SERVICE_URL:-http://127.0.0.1:8085}"
    REQUIRED_LISTENER_PORT=8085
    ;;
  *)
    echo "[verify] unsupported lane '${VERIFY_LANE}' (expected: host or docker)" >&2
    exit 2
    ;;
esac

run_remote_shell() {
  local command="$1"
  pdm run run-local-pdm run-hemma --shell "${command}"
}

cd "${REPO_ROOT}"
PINNED_TORCH_VERSION="${SIR_CONVERT_A_LOT_VERIFY_TORCH_VERSION_PIN:-$(read_pyproject_rocm_runtime)}"

echo "[verify] checking ROCm visibility"
run_remote_shell "set -euo pipefail; rocm-smi --showproductname --showuse --showmemuse >/tmp/sir_rocm_verify.log; grep -Eq 'GPU\\[[0-9]+\\]' /tmp/sir_rocm_verify.log"

if [[ "${VERIFY_LANE}" == "docker" ]]; then
  echo "[verify] checking docker lane container + ROCm device passthrough"
  run_remote_shell "set -euo pipefail; sudo docker ps --format '{{.Names}}' | grep -qx '${DOCKER_PROD_CONTAINER}'"
  run_remote_shell "set -euo pipefail; sudo docker exec '${DOCKER_PROD_CONTAINER}' test -e /dev/kfd"
  run_remote_shell "set -euo pipefail; sudo docker exec '${DOCKER_PROD_CONTAINER}' test -d /dev/dri"
  echo "[verify] checking in-container torch runtime probe"
  run_remote_shell "set -euo pipefail; VERIFY_TORCH_VERSION_PIN='${PINNED_TORCH_VERSION}' sudo docker exec -e VERIFY_TORCH_VERSION_PIN='${PINNED_TORCH_VERSION}' '${DOCKER_PROD_CONTAINER}' pdm run python - <<'PY'
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
else
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
fi

echo "[verify] checking service listener + readiness"
run_remote_shell "set -euo pipefail; ss -ltn | grep -q ':${REQUIRED_LISTENER_PORT} '; curl -fsS '${SERVICE_URL}/readyz' >/dev/null"

echo "[verify] checking readiness contract details"
run_remote_shell "set -euo pipefail; VERIFY_SERVICE_URL='${SERVICE_URL}' pdm run python - <<'PY'
import json
import os
import subprocess

import httpx


def _require_ready_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise SystemExit('readyz payload is not an object')
    if payload.get('ready') is not True:
        raise SystemExit(f"readyz indicates not ready: reasons={payload.get('reasons')!r}")
    return payload


service_url = os.environ['VERIFY_SERVICE_URL'].rstrip('/')
repo_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()

with httpx.Client(timeout=10.0) as client:
    response = client.get(f'{service_url}/readyz')
    response.raise_for_status()
    payload = _require_ready_payload(response.json())

if payload.get('service_revision') != repo_head:
    raise SystemExit(
        'service_revision does not match repo HEAD: '
        f"service={payload.get('service_revision')!r} repo_head={repo_head!r}"
    )
if payload.get('service_profile') != 'prod':
    raise SystemExit(f"service_profile is not 'prod': {payload.get('service_profile')!r}")

result = {
    'repo_head': repo_head,
    'service_revision': payload.get('service_revision'),
    'expected_revision': payload.get('expected_revision'),
    'service_profile': payload.get('service_profile'),
    'data_root': payload.get('data_root'),
}
print(json.dumps(result, sort_keys=True))
PY"

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
    'api_version': 'v2',
    'source': {
        'kind': 'upload',
        'filename': fixture_path.name,
        'format': 'pdf',
    },
    'conversion': {
        'output_format': 'md',
        'template': None,
        'css_filenames': [],
        'reference_docx_filename': None,
    },
    'pdf_options': {
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
headers = {
    'X-API-Key': api_key,
    'Idempotency-Key': idem,
    'X-Correlation-ID': 'corr_verify_gpu_runtime',
}

gpu_busy_seen = 0

with httpx.Client(base_url=service_url, timeout=30.0) as client:
    response = client.post(
        '/v2/convert/jobs?wait_seconds=0',
        files={
            'file': (fixture_path.name, file_bytes, 'application/pdf'),
            'job_spec': (None, json.dumps(job_spec, separators=(',', ':'))),
        },
        headers=headers,
    )
    response.raise_for_status()
    payload = response.json()
    job_obj = payload.get('job', {})
    job_id = job_obj.get('job_id')
    if not isinstance(job_id, str):
        raise SystemExit('missing job_id in create response')

    deadline = time.monotonic() + timeout_seconds
    final_status: str | None = None
    while time.monotonic() < deadline:
        smi_output = subprocess.run(
            ['rocm-smi', '--showuse'],
            check=False,
            capture_output=True,
            text=True,
        ).stdout
        for match in re.finditer(r'GPU use \\(%\\):\\s*([0-9]+)', smi_output):
            gpu_busy_seen = max(gpu_busy_seen, int(match.group(1)))

        status_response = client.get(
            f'/v2/convert/jobs/{job_id}',
            headers={'X-API-Key': api_key, 'X-Correlation-ID': 'corr_verify_gpu_poll'},
        )
        status_response.raise_for_status()
        status_payload = status_response.json()
        final_status_obj = status_payload.get('job', {}).get('status')
        final_status = str(final_status_obj) if final_status_obj is not None else None
        if final_status in {'succeeded', 'failed', 'canceled'}:
            break
        time.sleep(0.2)

    if final_status != 'succeeded':
        raise SystemExit(f'job did not succeed, status={final_status!r}')

    result_response = client.get(
        f'/v2/convert/jobs/{job_id}/result',
        headers={'X-API-Key': api_key, 'X-Correlation-ID': 'corr_verify_gpu_result'},
    )
    result_response.raise_for_status()
    result_payload = result_response.json()
    result_obj = result_payload.get('result', {})
    metadata = result_obj.get('conversion_metadata', {})
    warnings_obj = result_obj.get('warnings', [])

    if metadata.get('acceleration_used') != 'cuda':
        raise SystemExit(f"acceleration_used mismatch: {metadata.get('acceleration_used')!r}")
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
