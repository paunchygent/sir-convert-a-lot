"""Hemma GPU runtime verification for deploy gate workflows.

Purpose:
    Execute deterministic ROCm/runtime/readiness/live-conversion checks on the
    remote Hemma repository as a committed Python surface (Task 76).

Relationships:
    - Invoked by `scripts/devops/verify-hemma-gpu-runtime.sh` in `--remote` mode.
    - Invoked by `scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify`.
    - Uses canonical API-key/lane contracts from
      `scripts.sir_convert_a_lot.devops.hemma_deploy_verification_contracts`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.hemma_deploy_verification_contracts import (
    VerificationContractError,
    port_for_lane,
    resolve_api_key,
    service_url_for_lane,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import probe_torch_gpu_runtime

DEFAULT_FIXTURE = Path("tests/fixtures/benchmark_pdfs/paper_alpha.pdf")
DEFAULT_OUTPUT_ROOT = Path("build/verification/task-76-hemma-deploy-verify/gpu-runtime")


@dataclass(frozen=True)
class RuntimeProbeResult:
    """Serialized runtime probe details for report output."""

    runtime_kind: str
    is_available: bool
    torch_version: str | None


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hemma GPU runtime verifier (Task 76).")
    parser.add_argument(
        "--lane",
        choices=["host", "docker"],
        default=os.environ.get("SIR_CONVERT_A_LOT_VERIFY_LANE", "host"),
        help="Verification lane: host (28085 canonical) or docker (8085 internal-only).",
    )
    parser.add_argument(
        "--service-url",
        default=os.environ.get("SIR_CONVERT_A_LOT_VERIFY_SERVICE_URL", "").strip(),
        help="Override service base URL (default derived from --lane).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="X-API-Key value. Precedence: --api-key > SIR_CONVERT_A_LOT_API_KEY.",
    )
    parser.add_argument(
        "--allow-dev-key",
        action="store_true",
        help="Allow implicit dev-only-key from environment for local/dev usage.",
    )
    parser.add_argument(
        "--fixture",
        default=os.environ.get("SIR_CONVERT_A_LOT_VERIFY_FIXTURE", str(DEFAULT_FIXTURE)),
        help="PDF fixture path used for live conversion verification.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.environ.get("SIR_CONVERT_A_LOT_VERIFY_TIMEOUT_SECONDS", "180")),
        help="Maximum poll window for live conversion terminal status.",
    )
    parser.add_argument(
        "--docker-prod-container",
        default=os.environ.get(
            "SIR_CONVERT_A_LOT_VERIFY_DOCKER_PROD_CONTAINER", "sir_convert_a_lot_prod"
        ),
        help="Docker container name for prod runtime when lane=docker.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Output directory for deterministic verification report.",
    )
    return parser.parse_args(argv)


def _read_pinned_torch_version() -> str:
    """Read pinned ROCm torch version from pyproject configuration."""
    pyproject_path = Path("pyproject.toml")
    config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    runtime_obj = config["tool"]["sir_convert_a_lot"]["rocm_runtime"]
    torch_version_obj = runtime_obj["torch_version"]
    if not isinstance(torch_version_obj, str) or torch_version_obj.strip() == "":
        raise SystemExit("pyproject torch_version pin is missing.")
    return torch_version_obj


def _run_checked(command: list[str], *, label: str) -> str:
    """Run command and return stdout; include stderr in failure diagnostics."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout


def _probe_torch_runtime_local(*, expected_torch_version: str) -> RuntimeProbeResult:
    """Validate local torch probe has ROCm runtime and pinned version."""
    probe = probe_torch_gpu_runtime()
    if probe.runtime_kind != "rocm":
        raise SystemExit(f"runtime_kind is not rocm: {probe.runtime_kind!r}")
    if not probe.is_available:
        raise SystemExit("torch runtime is not GPU-available")
    if "+rocm" not in (probe.torch_version or ""):
        raise SystemExit(f"torch build is not ROCm-tagged: {probe.torch_version!r}")
    if probe.torch_version != expected_torch_version:
        raise SystemExit(
            "torch version mismatch: "
            f"expected={expected_torch_version!r} actual={probe.torch_version!r}"
        )
    return RuntimeProbeResult(
        runtime_kind=probe.runtime_kind,
        is_available=probe.is_available,
        torch_version=probe.torch_version,
    )


def _probe_torch_runtime_in_docker(
    *, container: str, expected_torch_version: str
) -> RuntimeProbeResult:
    """Validate in-container torch runtime has ROCm runtime and pinned version."""
    containers = _run_checked(
        ["sudo", "-n", "docker", "ps", "--format", "{{.Names}}"],
        label="docker ps",
    )
    if container not in set(containers.splitlines()):
        raise SystemExit(f"Expected container not running: {container!r}")

    _run_checked(
        ["sudo", "-n", "docker", "exec", container, "test", "-e", "/dev/kfd"],
        label="docker /dev/kfd check",
    )
    _run_checked(
        ["sudo", "-n", "docker", "exec", container, "test", "-d", "/dev/dri"],
        label="docker /dev/dri check",
    )

    probe_import = (
        "from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import "
        "probe_torch_gpu_runtime; "
    )
    python_snippet = (
        "import json; "
        f"{probe_import}"
        "probe=probe_torch_gpu_runtime(); "
        "print(json.dumps(probe.as_details(), sort_keys=True)); "
        "assert probe.runtime_kind == 'rocm', 'runtime_kind is not rocm'; "
        "assert probe.is_available, 'torch runtime is not GPU-available'; "
        "assert '+rocm' in (probe.torch_version or ''), 'torch build is not ROCm-tagged'; "
        f"assert probe.torch_version == {expected_torch_version!r}, "
        "'torch version mismatch';"
    )
    probe_output = _run_checked(
        [
            "sudo",
            "-n",
            "docker",
            "exec",
            container,
            "pdm",
            "run",
            "python",
            "-c",
            python_snippet,
        ],
        label="docker torch runtime probe",
    ).strip()

    try:
        payload = json.loads(probe_output.splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise SystemExit("Unable to parse docker runtime probe JSON output.") from exc

    runtime_kind_obj = payload.get("runtime_kind")
    is_available_obj = payload.get("is_available")
    torch_version_obj = payload.get("torch_version")
    if not isinstance(runtime_kind_obj, str) or not isinstance(is_available_obj, bool):
        raise SystemExit("Docker runtime probe payload is malformed.")
    if torch_version_obj is not None and not isinstance(torch_version_obj, str):
        raise SystemExit("Docker runtime probe torch_version is malformed.")

    return RuntimeProbeResult(
        runtime_kind=runtime_kind_obj,
        is_available=is_available_obj,
        torch_version=torch_version_obj,
    )


def _extract_gpu_busy_peak(smi_output: str) -> int:
    """Extract maximum GPU busy value from rocm-smi output."""
    peak = 0
    for match in re.finditer(r"GPU use \\(%\\):\\s*([0-9]+)", smi_output):
        peak = max(peak, int(match.group(1)))
    return peak


def _sample_gpu_busy_peak(previous_peak: int) -> int:
    """Sample rocm-smi GPU busy percentage and update max peak."""
    smi_output = _run_checked(["rocm-smi", "--showuse"], label="rocm-smi --showuse")
    return max(previous_peak, _extract_gpu_busy_peak(smi_output))


def _assert_listener_bound(*, port: int) -> None:
    """Ensure local listener port is bound before readiness checks."""
    listeners = _run_checked(["ss", "-ltn"], label="ss -ltn")
    if f":{port} " not in listeners:
        raise SystemExit(f"Listener port {port} is not bound.")


def _fetch_readyz(*, service_url: str) -> dict[str, object]:
    """Fetch and validate JSON readiness payload shape."""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{service_url}/readyz")
        response.raise_for_status()
        payload_obj: object = response.json()

    if not isinstance(payload_obj, dict):
        raise SystemExit("readyz payload is not an object")
    if payload_obj.get("ready") is not True:
        raise SystemExit(f"readyz indicates not ready: reasons={payload_obj.get('reasons')!r}")
    return payload_obj


def _run_live_conversion_smoke(
    *,
    service_url: str,
    api_key: str,
    fixture_path: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    """Run one live GPU-required conversion and validate acceleration metadata."""
    if not fixture_path.exists():
        raise SystemExit(f"fixture not found: {fixture_path}")

    file_bytes = fixture_path.read_bytes()
    idempotency_key = (
        "verify_gpu_" + hashlib.sha256(file_bytes).hexdigest()[:24] + f"_{int(time.time())}"
    )
    job_spec = {
        "api_version": "v2",
        "source": {
            "kind": "upload",
            "filename": fixture_path.name,
            "format": "pdf",
        },
        "conversion": {
            "output_format": "md",
            "template": None,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "pdf_options": {
            "backend_strategy": "auto",
            "ocr_mode": "off",
            "table_mode": "accurate",
            "normalize": "standard",
        },
        "execution": {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }
    headers = {
        "X-API-Key": api_key,
        "Idempotency-Key": idempotency_key,
        "X-Correlation-ID": "corr_task76_gpu_runtime",
    }

    gpu_busy_peak = 0
    with httpx.Client(base_url=service_url, timeout=30.0) as client:
        create_response = client.post(
            "/v2/convert/jobs?wait_seconds=0",
            files={
                "file": (fixture_path.name, file_bytes, "application/pdf"),
                "job_spec": (None, json.dumps(job_spec, separators=(",", ":"))),
            },
            headers=headers,
        )
        create_response.raise_for_status()
        create_payload_obj: object = create_response.json()
        if not isinstance(create_payload_obj, dict):
            raise SystemExit("create response payload is not a JSON object")
        create_payload = create_payload_obj
        job_obj = create_payload.get("job")
        if not isinstance(job_obj, dict):
            raise SystemExit("create response missing job object")
        job_id_obj = job_obj.get("job_id")
        if not isinstance(job_id_obj, str) or job_id_obj.strip() == "":
            raise SystemExit("create response missing job_id")
        job_id = job_id_obj

        deadline = time.monotonic() + timeout_seconds
        final_status: str | None = None
        while time.monotonic() < deadline:
            gpu_busy_peak = _sample_gpu_busy_peak(gpu_busy_peak)
            status_response = client.get(
                f"/v2/convert/jobs/{job_id}",
                headers={
                    "X-API-Key": api_key,
                    "X-Correlation-ID": "corr_task76_gpu_runtime_poll",
                },
            )
            status_response.raise_for_status()
            status_payload_obj: object = status_response.json()
            if not isinstance(status_payload_obj, dict):
                raise SystemExit("status response payload is not a JSON object")
            status_payload = status_payload_obj
            status_job_obj = status_payload.get("job")
            if not isinstance(status_job_obj, dict):
                raise SystemExit("status response missing job object")
            status_obj = status_job_obj.get("status")
            final_status = str(status_obj) if status_obj is not None else None
            if final_status in {"succeeded", "failed", "canceled"}:
                break
            time.sleep(0.2)

        if final_status != "succeeded":
            raise SystemExit(f"job did not succeed, status={final_status!r}")

        result_response = client.get(
            f"/v2/convert/jobs/{job_id}/result",
            headers={
                "X-API-Key": api_key,
                "X-Correlation-ID": "corr_task76_gpu_runtime_result",
            },
        )
        result_response.raise_for_status()
        result_payload_obj: object = result_response.json()
        if not isinstance(result_payload_obj, dict):
            raise SystemExit("result payload is not a JSON object")
        result_payload = result_payload_obj

    result_obj = result_payload.get("result")
    if not isinstance(result_obj, dict):
        raise SystemExit("result payload missing result object")
    metadata_obj = result_obj.get("conversion_metadata")
    warnings_obj = result_obj.get("warnings")
    metadata = metadata_obj if isinstance(metadata_obj, dict) else {}
    warnings_list = warnings_obj if isinstance(warnings_obj, list) else []

    acceleration_used_obj = metadata.get("acceleration_used")
    if acceleration_used_obj != "cuda":
        raise SystemExit(f"acceleration_used mismatch: {acceleration_used_obj!r}")
    if any("docling_cuda_unavailable_fallback_cpu" in str(item) for item in warnings_list):
        raise SystemExit("unexpected cpu fallback warning in conversion result")
    if gpu_busy_peak <= 0:
        raise SystemExit("rocm-smi never observed non-zero GPU busy during conversion")

    return {
        "job_id": job_id,
        "status": "succeeded",
        "acceleration_used": acceleration_used_obj,
        "gpu_busy_peak": gpu_busy_peak,
    }


def main(argv: list[str] | None = None) -> int:
    """Run Task 76 GPU runtime verification checks and emit deterministic report."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    try:
        resolved_api_key = resolve_api_key(
            api_key_arg=args.api_key,
            environ=os.environ,
            allow_dev_key=bool(args.allow_dev_key),
        )
    except VerificationContractError as exc:
        raise SystemExit(str(exc)) from exc

    service_url = (
        args.service_url.rstrip("/") if args.service_url else service_url_for_lane(args.lane)
    )
    lane_port = port_for_lane(args.lane)
    fixture_path = Path(args.fixture)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    expected_torch_version = _read_pinned_torch_version()
    _run_checked(
        ["rocm-smi", "--showproductname", "--showuse", "--showmemuse"],
        label="rocm-smi visibility",
    )

    if args.lane == "docker":
        runtime_probe = _probe_torch_runtime_in_docker(
            container=args.docker_prod_container,
            expected_torch_version=expected_torch_version,
        )
    else:
        runtime_probe = _probe_torch_runtime_local(expected_torch_version=expected_torch_version)

    _assert_listener_bound(port=lane_port)
    readyz_payload = _fetch_readyz(service_url=service_url)
    repo_head = _run_checked(["git", "rev-parse", "HEAD"], label="git rev-parse HEAD").strip()

    service_revision_obj = readyz_payload.get("service_revision")
    service_profile_obj = readyz_payload.get("service_profile")
    if not isinstance(service_revision_obj, str) or service_revision_obj.strip() == "":
        raise SystemExit("readyz payload missing service_revision")
    if service_revision_obj != repo_head:
        raise SystemExit(
            "service_revision does not match repo HEAD: "
            f"service_revision={service_revision_obj!r} repo_head={repo_head!r}"
        )
    if service_profile_obj != "prod":
        raise SystemExit(f"service_profile is not 'prod': {service_profile_obj!r}")

    smoke_result = _run_live_conversion_smoke(
        service_url=service_url,
        api_key=resolved_api_key.value,
        fixture_path=fixture_path,
        timeout_seconds=float(args.timeout_seconds),
    )

    report = {
        "lane": args.lane,
        "service_url": service_url,
        "listener_port": lane_port,
        "repo_head": repo_head,
        "service_revision": service_revision_obj,
        "service_profile": service_profile_obj,
        "runtime_probe": {
            "runtime_kind": runtime_probe.runtime_kind,
            "is_available": runtime_probe.is_available,
            "torch_version": runtime_probe.torch_version,
        },
        "smoke": smoke_result,
    }
    report_path = output_root / "gpu_runtime_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
