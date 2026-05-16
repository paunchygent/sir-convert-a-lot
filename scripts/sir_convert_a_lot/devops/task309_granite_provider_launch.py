"""Task 309 persistent Granite/vLLM provider launch planning.

Purpose:
    Build and optionally execute the named Docker launch command for the
    Granite/vLLM provider used by Task 309 live answer-key validation.

Relationships:
    - Uses `task309_granite_provider_contracts` for the retained launch plan
      and launch result contracts.
    - Complements `task309_granite_provider_status`, which verifies the
      launched provider without stopping or cleaning it up.
    - Follows the Hemma GPU runtime runbook: localhost-only host bind,
      scratch-backed Hugging Face cache, ROCm devices, and disabled request
      logging.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime

from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    DEFAULT_PROVIDER_CONTAINER_CACHE,
    DEFAULT_PROVIDER_CONTAINER_NAME,
    DEFAULT_PROVIDER_GPU_MEMORY_UTILIZATION,
    DEFAULT_PROVIDER_HOST_CACHE,
    DEFAULT_PROVIDER_IMAGE,
    DEFAULT_PROVIDER_MAX_MODEL_LEN,
    DEFAULT_PROVIDER_MODEL,
    DEFAULT_PROVIDER_PORT,
    TASK309_PROVIDER_PERSISTENT_POLICY,
    Task309ProviderLaunchPlan,
    Task309ProviderLaunchResult,
)

TASK309_PROVIDER_LAUNCH_PLAN_SCHEMA_VERSION = "task309_granite_provider_launch_plan_v1"
TASK309_PROVIDER_LAUNCH_RESULT_SCHEMA_VERSION = "task309_granite_provider_launch_result_v1"
DEFAULT_CONTAINER_PORT = 8000
DOCKER_COMMAND_PREFIX = ("sudo", "-n", "docker")
HEMMA_VIDEO_GROUP_ID = "44"
HEMMA_RENDER_GROUP_ID = "993"


def build_task309_provider_launch_plan(
    *,
    container_name: str = DEFAULT_PROVIDER_CONTAINER_NAME,
    image: str = DEFAULT_PROVIDER_IMAGE,
    model: str = DEFAULT_PROVIDER_MODEL,
    host_port: int = DEFAULT_PROVIDER_PORT,
    container_port: int = DEFAULT_CONTAINER_PORT,
    host_cache_path: str = DEFAULT_PROVIDER_HOST_CACHE,
    container_cache_path: str = DEFAULT_PROVIDER_CONTAINER_CACHE,
    dry_run: bool = True,
) -> Task309ProviderLaunchPlan:
    """Build the Docker command for the persistent Task 309 vLLM provider."""

    command = (
        *DOCKER_COMMAND_PREFIX,
        "run",
        "-d",
        "--name",
        container_name,
        "--restart",
        "unless-stopped",
        "--ipc=host",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
        "--group-add",
        HEMMA_VIDEO_GROUP_ID,
        "--group-add",
        HEMMA_RENDER_GROUP_ID,
        "-p",
        f"127.0.0.1:{host_port}:{container_port}",
        "-v",
        f"{host_cache_path}:{container_cache_path}",
        "-e",
        f"HF_HOME={container_cache_path}",
        "-e",
        f"HF_HUB_CACHE={container_cache_path}/hub",
        "-e",
        f"TRANSFORMERS_CACHE={container_cache_path}",
        image,
        "vllm",
        "serve",
        model,
        "--host",
        "0.0.0.0",
        "--port",
        str(container_port),
        "--max-model-len",
        str(DEFAULT_PROVIDER_MAX_MODEL_LEN),
        "--gpu-memory-utilization",
        DEFAULT_PROVIDER_GPU_MEMORY_UTILIZATION,
        "--disable-log-requests",
    )
    return Task309ProviderLaunchPlan(
        schema_version=TASK309_PROVIDER_LAUNCH_PLAN_SCHEMA_VERSION,
        generated_at=_utc_now_iso(),
        container_name=container_name,
        image=image,
        model=model,
        host_port=host_port,
        container_port=container_port,
        host_cache_path=host_cache_path,
        container_cache_path=container_cache_path,
        persistent_policy=TASK309_PROVIDER_PERSISTENT_POLICY,
        command=command,
        dry_run=dry_run,
    )


def launch_task309_provider(plan: Task309ProviderLaunchPlan) -> Task309ProviderLaunchResult:
    """Execute one persistent provider launch plan unless it is a dry run."""

    if plan.dry_run:
        return Task309ProviderLaunchResult(
            schema_version=TASK309_PROVIDER_LAUNCH_RESULT_SCHEMA_VERSION,
            launched_at=_utc_now_iso(),
            container_name=plan.container_name,
            dry_run=True,
            exit_code=None,
            container_id=None,
            ok=True,
            error_kind=None,
            plan=plan,
        )
    try:
        result = subprocess.run(
            list(plan.command),
            capture_output=True,
            check=False,
            text=True,
            timeout=1800,
        )
    except FileNotFoundError:
        return _failed_launch(plan, error_kind="FileNotFoundError")
    except subprocess.TimeoutExpired:
        return _failed_launch(plan, error_kind="TimeoutExpired")
    container_id = result.stdout.strip() if result.returncode == 0 else None
    return Task309ProviderLaunchResult(
        schema_version=TASK309_PROVIDER_LAUNCH_RESULT_SCHEMA_VERSION,
        launched_at=_utc_now_iso(),
        container_name=plan.container_name,
        dry_run=False,
        exit_code=result.returncode,
        container_id=container_id if container_id else None,
        ok=result.returncode == 0,
        error_kind=None if result.returncode == 0 else "DockerRunFailed",
        plan=plan,
    )


def _failed_launch(
    plan: Task309ProviderLaunchPlan,
    *,
    error_kind: str,
) -> Task309ProviderLaunchResult:
    return Task309ProviderLaunchResult(
        schema_version=TASK309_PROVIDER_LAUNCH_RESULT_SCHEMA_VERSION,
        launched_at=_utc_now_iso(),
        container_name=plan.container_name,
        dry_run=plan.dry_run,
        exit_code=None,
        container_id=None,
        ok=False,
        error_kind=error_kind,
        plan=plan,
    )


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
