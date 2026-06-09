"""Helper utilities for Hemma v2 conversion smoke verification scripts.

Purpose:
    Keep the v2 conversion smoke verification entrypoint small by extracting reusable
    helper functions and evidence dataclasses used by the Hemma v2 smoke flow.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions`.
    - Uses `interfaces.http_client_v2.SirConvertALotClientV2` for submission/poll/download.
    - Uses raw HTTP `GET /readyz` and `GET /v2/convert/jobs/{job_id}/result` for contract evidence.
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.interfaces.http_client_v2 import SirConvertALotClientV2


@dataclass(frozen=True)
class ArtifactEvidence:
    """Evidence for a successful conversion job."""

    job_id: str
    artifact_path: Path
    artifact_sha256: str
    artifact_size_bytes: int
    pipeline_used: str | None = None
    backend_used: str | None = None
    acceleration_used: str | None = None
    pages_per_minute: float | None = None
    phase_timings_ms: dict[str, int] | None = None
    ocr_enabled: bool | None = None
    ocr_engine_used: str | None = None
    ocr_languages_used: list[str] | None = None


def utc_now_iso() -> str:
    """Return current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_bytes(value: bytes) -> str:
    """Return hex SHA256 digest for bytes."""
    return hashlib.sha256(value).hexdigest()


def count_pdf_image_objects(pdf_bytes: bytes) -> int:
    """Return the number of embedded image objects in a PDF byte stream."""

    return pdf_bytes.count(b"/Subtype /Image")


def write_json(path: Path, payload: object) -> None:
    """Write payload as stable JSON file."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def require_json_object(payload: object, *, label: str) -> dict[str, object]:
    """Assert payload is a JSON object and return it."""
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} payload is not a JSON object.")
    return payload


def run_checked(command: list[str], *, label: str) -> str:
    """Run a subprocess command and return stdout; raise on non-zero exit."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        raise SystemExit(
            f"{label} failed (exit={result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    return result.stdout.strip()


def probe_docker_runtime(*, prod_container: str, output_dir: Path) -> dict[str, str]:
    """Probe Pandoc and WeasyPrint versions inside the prod container."""
    output_dir.mkdir(parents=True, exist_ok=True)

    containers = run_checked(
        ["sudo", "-n", "docker", "ps", "--format", "{{.Names}}"], label="docker ps"
    )
    if prod_container not in set(containers.splitlines()):
        raise SystemExit(
            f"Expected docker container '{prod_container}' not running. "
            f"Running containers: {containers!r}"
        )

    pandoc_version = run_checked(
        ["sudo", "-n", "docker", "exec", prod_container, "pandoc", "--version"],
        label="pandoc --version",
    )
    (output_dir / "pandoc_version.txt").write_text(pandoc_version + "\n", encoding="utf-8")

    weasyprint_version = run_checked(
        [
            "sudo",
            "-n",
            "docker",
            "exec",
            prod_container,
            "python",
            "-c",
            "import weasyprint; print(weasyprint.__version__)",
        ],
        label="weasyprint version",
    )
    (output_dir / "weasyprint_version.txt").write_text(weasyprint_version + "\n", encoding="utf-8")

    return {"pandoc_version": pandoc_version, "weasyprint_version": weasyprint_version}


def fetch_json(
    client: httpx.Client, *, path: str, headers: dict[str, str], label: str
) -> dict[str, object]:
    """Fetch JSON object from HTTP GET endpoint and raise on errors."""
    response = client.get(path, headers=headers)
    try:
        response.raise_for_status()
    except httpx.HTTPError as exc:
        body = response.text.strip()
        raise SystemExit(f"{label} request failed: {exc}\nbody:\n{body}") from exc

    payload: object
    try:
        payload = response.json()
    except ValueError as exc:
        raise SystemExit(f"{label} did not return JSON.") from exc

    return require_json_object(payload, label=label)


def assert_readyz_contract(*, readyz: dict[str, object], repo_head: str) -> None:
    """Validate readyz contract includes expected service revision."""
    if readyz.get("ready") is not True:
        raise SystemExit(f"readyz indicates not ready: reasons={readyz.get('reasons')!r}")
    service_revision = readyz.get("service_revision")
    if service_revision != repo_head:
        raise SystemExit(
            "readyz service_revision does not match repo HEAD: "
            f"service_revision={service_revision!r} repo_head={repo_head!r}"
        )


def build_resources_zip(*, files: dict[str, bytes]) -> bytes:
    """Build a deterministic resources zip payload from file bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)
    return buffer.getvalue()


def idempotency_key(*, scope: str, file_bytes: bytes) -> str:
    """Create a time-scoped idempotency key for smoke verification requests."""
    ts = int(time.time())
    digest = sha256_bytes(file_bytes)[:10]
    return f"t39_{scope}_{digest}_{ts}"


def run_v2_conversion(
    *,
    http_base_url: str,
    api_key: str,
    output_dir: Path,
    label: str,
    source_path: Path,
    job_spec: dict[str, object],
    artifact_suffix: str,
    wait_seconds: int,
    max_poll_seconds: float,
    resources_zip_bytes: bytes | None = None,
) -> tuple[ArtifactEvidence, dict[str, object]]:
    """Execute one v2 conversion and return artifact + result payload evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{label}{artifact_suffix}"

    file_bytes = source_path.read_bytes()
    idem = idempotency_key(scope=label, file_bytes=file_bytes)
    correlation_id = f"corr_conversion_smoke_{label}_{int(time.time())}"

    with SirConvertALotClientV2(base_url=http_base_url, api_key=api_key) as client:
        outcome = client.convert_upload_to_artifact(
            source_path=source_path,
            job_spec=job_spec,
            idempotency_key=idem,
            wait_seconds=wait_seconds,
            max_poll_seconds=max_poll_seconds,
            correlation_id=correlation_id,
            resources_zip_bytes=resources_zip_bytes,
            reference_docx_bytes=None,
        )
        artifact_path.write_bytes(outcome.artifact_bytes)

    if artifact_path.stat().st_size <= 0:
        raise SystemExit(f"{label} produced empty artifact: {artifact_path}")

    with httpx.Client(base_url=http_base_url, timeout=30.0) as http_client:
        status_payload = fetch_json(
            http_client,
            path=f"/v2/convert/jobs/{outcome.job_id}",
            headers={"X-API-Key": api_key, "X-Correlation-ID": correlation_id},
            label=f"{label} v2 status",
        )
        result_payload = fetch_json(
            http_client,
            path=f"/v2/convert/jobs/{outcome.job_id}/result",
            headers={"X-API-Key": api_key, "X-Correlation-ID": correlation_id},
            label=f"{label} v2 result",
        )

    job_obj = status_payload.get("job") if isinstance(status_payload, dict) else None
    progress_obj: object = None
    if isinstance(job_obj, dict):
        progress_obj = job_obj.get("progress")
    progress = progress_obj if isinstance(progress_obj, dict) else {}

    pages_per_minute_obj = progress.get("pages_per_minute")
    pages_per_minute: float | None = None
    if isinstance(pages_per_minute_obj, (int, float)):
        pages_per_minute = float(pages_per_minute_obj)

    phase_timings_obj = progress.get("phase_timings_ms")
    phase_timings_ms: dict[str, int] | None = None
    if isinstance(phase_timings_obj, dict):
        phase_timings_ms = {
            str(key): int(value)
            for key, value in phase_timings_obj.items()
            if isinstance(key, str) and isinstance(value, (int, float))
        }

    result_obj = result_payload.get("result")
    conversion_metadata_obj: object = None
    if isinstance(result_obj, dict):
        conversion_metadata_obj = result_obj.get("conversion_metadata")
    conversion_metadata = (
        conversion_metadata_obj if isinstance(conversion_metadata_obj, dict) else {}
    )

    pipeline_used_obj = conversion_metadata.get("pipeline_used")
    backend_used_obj = conversion_metadata.get("backend_used")
    acceleration_used_obj = conversion_metadata.get("acceleration_used")
    ocr_enabled_obj = conversion_metadata.get("ocr_enabled")
    ocr_engine_used_obj = conversion_metadata.get("ocr_engine_used")
    ocr_languages_used_obj = conversion_metadata.get("ocr_languages_used")

    return (
        ArtifactEvidence(
            job_id=outcome.job_id,
            artifact_path=artifact_path,
            artifact_sha256=sha256_bytes(artifact_path.read_bytes()),
            artifact_size_bytes=artifact_path.stat().st_size,
            pipeline_used=pipeline_used_obj if isinstance(pipeline_used_obj, str) else None,
            backend_used=backend_used_obj if isinstance(backend_used_obj, str) else None,
            acceleration_used=(
                acceleration_used_obj if isinstance(acceleration_used_obj, str) else None
            ),
            pages_per_minute=pages_per_minute,
            phase_timings_ms=phase_timings_ms,
            ocr_enabled=ocr_enabled_obj if isinstance(ocr_enabled_obj, bool) else None,
            ocr_engine_used=(ocr_engine_used_obj if isinstance(ocr_engine_used_obj, str) else None),
            ocr_languages_used=(
                [item for item in ocr_languages_used_obj if isinstance(item, str)]
                if isinstance(ocr_languages_used_obj, list)
                else None
            ),
        ),
        result_payload,
    )
