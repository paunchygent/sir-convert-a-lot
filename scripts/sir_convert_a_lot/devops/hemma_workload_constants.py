"""Fixed identities, paths, and policies for Sir Hemma GPU workloads.

Purpose:
    Hold the host identity, resource claims, workload IDs, container names,
    host state paths, Docker inspect formats, readiness timeouts, restart
    policies, and privileged Docker prefix shared by the Sir workload binding.

Relationships:
    - Imported by `hemma_workload.py`, which re-exports every constant as the
      public surface for the CLI and tests.
    - Imported by `hemma_workload_inventory.py` and
      `hemma_workload_container_adapter.py` for container names and commands.
"""

from __future__ import annotations

from pathlib import Path

HOST_IDENTITY = "hemma"
GPU_CLAIM = "gpu:amdgpu"
PRODUCT_RESOURCE_CLAIM = "product:sir"
PRODUCTION_WORKLOAD_ID = "sir-production"
STT_WORKLOAD_ID = "sir-stt-sidecar"
RESERVED_EDGE_WORKLOAD_ID = "sir-public-reserved-edge"
API_CONTAINER = "sir_convert_a_lot_prod"
GPU_WORKER_CONTAINER = "sir_convert_a_lot_gpu_worker"
STT_CONTAINER = "sir_convert_a_lot_stt_sidecar"
RESERVED_EDGE_CONTAINER = "sir_convert_a_lot_public_reserved"
PRODUCTION_CONTAINERS = (API_CONTAINER, GPU_WORKER_CONTAINER)
DECLARED_GPU_CONTAINERS = (GPU_WORKER_CONTAINER, STT_CONTAINER)
HOST_STATE_ROOT = Path("/var/lib/hemma/workload-switch")
RECEIPT_PATH = HOST_STATE_ROOT / "active-receipt.json"
LOCK_PATH = HOST_STATE_ROOT / "active.lock"
CONTAINER_STATE_FORMAT = "{{.State.Status}}\t{{.HostConfig.RestartPolicy.Name}}"
CONTAINER_HEALTH_FORMAT = (
    "{{if .Config.Healthcheck}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}"
)
SIDECAR_READINESS_TIMEOUT_SECONDS = 15 * 60.0
SIDECAR_READINESS_INTERVAL_SECONDS = 2.0
PRODUCTION_RESTART_POLICY = "no"
SIDECAR_RESTART_POLICY = "unless-stopped"
DOCKER_COMMAND = ("sudo", "-n", "docker")
