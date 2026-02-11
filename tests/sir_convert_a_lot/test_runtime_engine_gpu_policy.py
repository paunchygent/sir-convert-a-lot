"""Runtime GPU policy tests for Sir Convert-a-Lot.

Purpose:
    Validate GPU-first rollout lock behavior at runtime configuration level and
    confirm explicit test-only CPU overrides remain available.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.runtime_engine`.
    - Complements HTTP contract tests in `test_api_contract_v1.py`.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobSpec, JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_engine import (
    ServiceConfig,
    ServiceRuntime,
    service_config_from_env,
)


def _job_spec(filename: str, acceleration_policy: str) -> JobSpec:
    return JobSpec.model_validate(
        {
            "api_version": "v1",
            "source": {"kind": "upload", "filename": filename},
            "conversion": {
                "output_format": "md",
                "backend_strategy": "auto",
                "ocr_mode": "auto",
                "table_mode": "fast",
                "normalize": "standard",
            },
            "execution": {
                "acceleration_policy": acceleration_policy,
                "priority": "normal",
                "document_timeout_seconds": 1800,
            },
            "retention": {"pin": False},
        }
    )


def _wait_for_terminal(
    runtime: ServiceRuntime, job_id: str, timeout_seconds: float = 4.0
) -> JobStatus:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = runtime.get_job(job_id)
        assert job is not None
        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            return job.status
        time.sleep(0.05)
    raise AssertionError("job did not reach terminal status before timeout")


def test_service_config_from_env_rejects_cpu_unlock_env_flags(monkeypatch) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_ALLOW_CPU_ONLY", "1")
    with pytest.raises(ValueError, match="CPU unlock env vars are disabled"):
        service_config_from_env()


def test_test_only_cpu_unlock_path_sets_cpu_acceleration(tmp_path: Path) -> None:
    runtime = ServiceRuntime(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "runtime_data",
            gpu_available=False,
            allow_cpu_only=True,
            allow_cpu_fallback=False,
            processing_delay_seconds=0.05,
        )
    )

    spec = _job_spec("cpu-mode.pdf", "cpu_only")
    job = runtime.create_job(
        spec=spec,
        upload_bytes=b"%PDF-1.4\n% cpu-mode\n%%EOF\n",
        source_filename="cpu-mode.pdf",
    )

    runtime.run_job_async(job.job_id)
    status = _wait_for_terminal(runtime, job.job_id)
    assert status == JobStatus.SUCCEEDED

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.acceleration_used == "cpu"
