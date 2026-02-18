"""Hemma v2 conversion smoke verification (Task 39).

Purpose:
    Produce deterministic evidence that the Hemma dockerized runtime can execute
    the critical multi-format conversion routes exposed via service API v2:
    `html -> pdf`, `md -> pdf`, `md -> docx`, and `pdf -> docx`, while also
    confirming the locked v1 `pdf -> md` route remains operational.

Relationships:
    - Called by `scripts/devops/verify-hemma-v2-conversions.sh` (remote mode).
    - Uses the typed HTTP clients:
        - `scripts.sir_convert_a_lot.interfaces.http_client.SirConvertALotClient` (v1)
        - `scripts.sir_convert_a_lot.interfaces.http_client_v2.SirConvertALotClientV2` (v2)
    - Writes evidence under `build/verification/task-39-v2-smoke/` (artifacts,
      responses, and a markdown + JSON report).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.interfaces.http_client import ClientError, SirConvertALotClient
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


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _require_json_object(payload: object, *, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} payload is not a JSON object.")
    return payload


def _run_checked(command: list[str], *, label: str) -> str:
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


def _probe_docker_runtime(*, prod_container: str, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    containers = _run_checked(
        ["sudo", "-n", "docker", "ps", "--format", "{{.Names}}"], label="docker ps"
    )
    if prod_container not in set(containers.splitlines()):
        raise SystemExit(
            f"Expected docker container '{prod_container}' not running. "
            f"Running containers: {containers!r}"
        )

    pandoc_version = _run_checked(
        ["sudo", "-n", "docker", "exec", prod_container, "pandoc", "--version"],
        label="pandoc --version",
    )
    (output_dir / "pandoc_version.txt").write_text(pandoc_version + "\n", encoding="utf-8")

    weasyprint_version = _run_checked(
        [
            "sudo",
            "-n",
            "docker",
            "exec",
            prod_container,
            "pdm",
            "run",
            "python",
            "-c",
            "import weasyprint; print(weasyprint.__version__)",
        ],
        label="weasyprint version",
    )
    (output_dir / "weasyprint_version.txt").write_text(weasyprint_version + "\n", encoding="utf-8")

    return {"pandoc_version": pandoc_version, "weasyprint_version": weasyprint_version}


def _fetch_json(
    client: httpx.Client, *, path: str, headers: dict[str, str], label: str
) -> dict[str, object]:
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

    return _require_json_object(payload, label=label)


def _assert_readyz_contract(*, readyz: dict[str, object], repo_head: str) -> None:
    if readyz.get("ready") is not True:
        raise SystemExit(f"readyz indicates not ready: reasons={readyz.get('reasons')!r}")
    service_revision = readyz.get("service_revision")
    if service_revision != repo_head:
        raise SystemExit(
            "readyz service_revision does not match repo HEAD: "
            f"service_revision={service_revision!r} repo_head={repo_head!r}"
        )


def _build_resources_zip(*, files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)
    return buffer.getvalue()


def _idempotency_key(*, scope: str, file_bytes: bytes) -> str:
    ts = int(time.time())
    digest = _sha256_bytes(file_bytes)[:10]
    return f"t39_{scope}_{digest}_{ts}"


def _run_v2_conversion(
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
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{label}{artifact_suffix}"

    file_bytes = source_path.read_bytes()
    idem = _idempotency_key(scope=label, file_bytes=file_bytes)
    correlation_id = f"corr_task39_{label}_{int(time.time())}"

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
        result_payload = _fetch_json(
            http_client,
            path=f"/v2/convert/jobs/{outcome.job_id}/result",
            headers={"X-API-Key": api_key, "X-Correlation-ID": correlation_id},
            label=f"{label} v2 result",
        )

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

    return (
        ArtifactEvidence(
            job_id=outcome.job_id,
            artifact_path=artifact_path,
            artifact_sha256=_sha256_bytes(artifact_path.read_bytes()),
            artifact_size_bytes=artifact_path.stat().st_size,
            pipeline_used=pipeline_used_obj if isinstance(pipeline_used_obj, str) else None,
            backend_used=backend_used_obj if isinstance(backend_used_obj, str) else None,
            acceleration_used=(
                acceleration_used_obj if isinstance(acceleration_used_obj, str) else None
            ),
        ),
        result_payload,
    )


def _run_v1_pdf_to_md(
    *,
    http_base_url: str,
    api_key: str,
    output_dir: Path,
    pdf_path: Path,
    wait_seconds: int,
    max_poll_seconds: float,
) -> tuple[ArtifactEvidence, dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "v1_pdf_to_md.md"

    file_bytes = pdf_path.read_bytes()
    idem = _idempotency_key(scope="v1_pdf_to_md", file_bytes=file_bytes)
    correlation_id = f"corr_task39_v1_pdf_to_md_{int(time.time())}"

    job_spec: dict[str, object] = {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": pdf_path.name},
        "conversion": {
            "output_format": "md",
            "backend_strategy": "auto",
            "ocr_mode": "auto",
            "table_mode": "accurate",
            "normalize": "strict",
        },
        "execution": {
            "acceleration_policy": "gpu_required",
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }

    with SirConvertALotClient(base_url=http_base_url, api_key=api_key) as client:
        outcome = client.convert_pdf_to_markdown(
            pdf_path=pdf_path,
            job_spec=job_spec,
            idempotency_key=idem,
            wait_seconds=wait_seconds,
            max_poll_seconds=max_poll_seconds,
            correlation_id=correlation_id,
        )
        artifact_path.write_text(outcome.markdown_content, encoding="utf-8")
        result_payload = client.fetch_result_payload(
            outcome.job_id, correlation_id=correlation_id, inline=True
        )

    if artifact_path.stat().st_size <= 0:
        raise SystemExit(f"v1 pdf->md produced empty artifact: {artifact_path}")

    metadata: dict[str, object] = {}
    result_obj = result_payload.get("result")
    if isinstance(result_obj, dict):
        metadata_obj = result_obj.get("conversion_metadata")
        if isinstance(metadata_obj, dict):
            metadata = metadata_obj

    pipeline_used_obj = metadata.get("pipeline_used")
    backend_used_obj = metadata.get("backend_used")
    acceleration_used_obj = metadata.get("acceleration_used")

    return (
        ArtifactEvidence(
            job_id=outcome.job_id,
            artifact_path=artifact_path,
            artifact_sha256=_sha256_bytes(artifact_path.read_bytes()),
            artifact_size_bytes=artifact_path.stat().st_size,
            pipeline_used=pipeline_used_obj if isinstance(pipeline_used_obj, str) else None,
            backend_used=backend_used_obj if isinstance(backend_used_obj, str) else None,
            acceleration_used=(
                acceleration_used_obj if isinstance(acceleration_used_obj, str) else None
            ),
        ),
        result_payload,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hemma v2 conversion smoke verifier (Task 39).")
    parser.add_argument(
        "--lane",
        choices=["docker", "host"],
        default=os.environ.get("SIR_CONVERT_A_LOT_VERIFY_LANE", "docker"),
        help="Verification lane: docker (8085) or host (28085).",
    )
    parser.add_argument(
        "--service-url",
        default=os.environ.get("SIR_CONVERT_A_LOT_VERIFY_SERVICE_URL", ""),
        help="Override service base URL (e.g. http://127.0.0.1:8085).",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("SIR_CONVERT_A_LOT_API_KEY", "dev-only-key"),
        help="X-API-Key value used for service requests.",
    )
    parser.add_argument(
        "--output-root",
        default="build/verification/task-39-v2-smoke",
        help="Output directory for evidence artifacts and reports.",
    )
    parser.add_argument(
        "--pdf-fixture",
        default=os.environ.get(
            "SIR_CONVERT_A_LOT_VERIFY_PDF_FIXTURE", "tests/fixtures/benchmark_pdfs/paper_alpha.pdf"
        ),
        help="PDF fixture path used for v1 pdf->md and v2 pdf->docx smoke.",
    )
    parser.add_argument(
        "--docker-prod-container",
        default=os.environ.get(
            "SIR_CONVERT_A_LOT_VERIFY_DOCKER_PROD_CONTAINER", "sir_convert_a_lot_prod"
        ),
        help="Docker container name for the prod service runtime (pandoc/weasyprint probe).",
    )
    parser.add_argument(
        "--wait-seconds", type=int, default=5, help="Create-job wait_seconds (0..20)."
    )
    parser.add_argument(
        "--max-poll-seconds",
        type=float,
        default=180.0,
        help="Maximum seconds to poll for terminal job status.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    service_url: str
    if args.service_url:
        service_url = str(args.service_url).rstrip("/")
    elif args.lane == "host":
        service_url = "http://127.0.0.1:28085"
    else:
        service_url = "http://127.0.0.1:8085"

    output_root = Path(args.output_root)
    fixtures_dir = output_root / "fixtures"
    artifacts_dir = output_root / "artifacts"
    responses_dir = output_root / "responses"
    runtime_dir = output_root / "runtime"
    output_root.mkdir(parents=True, exist_ok=True)
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    repo_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    (output_root / "repo_head.txt").write_text(repo_head + "\n", encoding="utf-8")

    with httpx.Client(base_url=service_url, timeout=10.0) as client:
        healthz = _fetch_json(
            client,
            path="/healthz",
            headers={"X-API-Key": args.api_key},
            label="healthz",
        )
        readyz = _fetch_json(
            client,
            path="/readyz",
            headers={"X-API-Key": args.api_key},
            label="readyz",
        )
    _write_json(output_root / "healthz.json", healthz)
    _write_json(output_root / "readyz.json", readyz)
    _assert_readyz_contract(readyz=readyz, repo_head=repo_head)

    runtime_versions = _probe_docker_runtime(
        prod_container=args.docker_prod_container,
        output_dir=runtime_dir,
    )

    html_path = fixtures_dir / "task39_smoke.html"
    md_path = fixtures_dir / "task39_smoke.md"
    css_path = fixtures_dir / "task39_smoke.css"
    html_path.write_text(
        "<!doctype html>\n"
        '<html><head><meta charset="utf-8"><title>Task 39 Smoke</title></head>\n'
        "<body>\n"
        "<h1>Task 39 v2 smoke: html -&gt; pdf</h1>\n"
        "<p>This verifies v2 route execution on Hemma docker lane.</p>\n"
        "</body></html>\n",
        encoding="utf-8",
    )
    md_path.write_text(
        "# Task 39 v2 smoke\n\n"
        "This verifies `md -> pdf` and `md -> docx` conversion routes.\n\n"
        "- alpha\n"
        "- beta\n\n"
        "**Bold** and `code`.\n",
        encoding="utf-8",
    )
    css_path.write_text("h1 { font-size: 22pt; }\n", encoding="utf-8")

    resources_zip_bytes = _build_resources_zip(files={css_path.name: css_path.read_bytes()})
    (fixtures_dir / "resources.zip").write_bytes(resources_zip_bytes)

    pdf_fixture = Path(args.pdf_fixture)
    if not pdf_fixture.exists():
        raise SystemExit(f"pdf fixture not found: {pdf_fixture}")

    v2_results: dict[str, ArtifactEvidence] = {}
    evidence_payloads: dict[str, dict[str, object]] = {}

    def _spec_v2(
        *, source: Path, source_format: str, output_format: str, css: bool
    ) -> dict[str, object]:
        conversion: dict[str, object] = {
            "output_format": output_format,
            "css_filenames": [css_path.name] if css else [],
            "reference_docx_filename": None,
        }
        spec: dict[str, object] = {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": source.name, "format": source_format},
            "conversion": conversion,
            "pdf_options": None,
            "execution": None,
            "retention": {"pin": False},
        }
        if source_format == "pdf":
            spec["pdf_options"] = {
                "backend_strategy": "auto",
                "ocr_mode": "auto",
                "table_mode": "accurate",
                "normalize": "strict",
            }
            spec["execution"] = {
                "acceleration_policy": "gpu_required",
                "priority": "normal",
                "document_timeout_seconds": 1800,
            }
        return spec

    try:
        html_ev, html_payload = _run_v2_conversion(
            http_base_url=service_url,
            api_key=args.api_key,
            output_dir=artifacts_dir,
            label="html_to_pdf",
            source_path=html_path,
            job_spec=_spec_v2(
                source=html_path,
                source_format="html",
                output_format="pdf",
                css=True,
            ),
            artifact_suffix=".pdf",
            wait_seconds=args.wait_seconds,
            max_poll_seconds=args.max_poll_seconds,
            resources_zip_bytes=resources_zip_bytes,
        )
        v2_results["html_to_pdf"] = html_ev
        evidence_payloads["html_to_pdf_result"] = html_payload

        md_pdf_ev, md_pdf_payload = _run_v2_conversion(
            http_base_url=service_url,
            api_key=args.api_key,
            output_dir=artifacts_dir,
            label="md_to_pdf",
            source_path=md_path,
            job_spec=_spec_v2(
                source=md_path,
                source_format="md",
                output_format="pdf",
                css=True,
            ),
            artifact_suffix=".pdf",
            wait_seconds=args.wait_seconds,
            max_poll_seconds=args.max_poll_seconds,
            resources_zip_bytes=resources_zip_bytes,
        )
        v2_results["md_to_pdf"] = md_pdf_ev
        evidence_payloads["md_to_pdf_result"] = md_pdf_payload

        md_docx_ev, md_docx_payload = _run_v2_conversion(
            http_base_url=service_url,
            api_key=args.api_key,
            output_dir=artifacts_dir,
            label="md_to_docx",
            source_path=md_path,
            job_spec=_spec_v2(
                source=md_path,
                source_format="md",
                output_format="docx",
                css=False,
            ),
            artifact_suffix=".docx",
            wait_seconds=args.wait_seconds,
            max_poll_seconds=args.max_poll_seconds,
            resources_zip_bytes=None,
        )
        v2_results["md_to_docx"] = md_docx_ev
        evidence_payloads["md_to_docx_result"] = md_docx_payload

        pdf_docx_ev, pdf_docx_payload = _run_v2_conversion(
            http_base_url=service_url,
            api_key=args.api_key,
            output_dir=artifacts_dir,
            label="pdf_to_docx",
            source_path=pdf_fixture,
            job_spec=_spec_v2(
                source=pdf_fixture,
                source_format="pdf",
                output_format="docx",
                css=False,
            ),
            artifact_suffix=".docx",
            wait_seconds=args.wait_seconds,
            max_poll_seconds=max(args.max_poll_seconds, 240.0),
            resources_zip_bytes=None,
        )
        v2_results["pdf_to_docx"] = pdf_docx_ev
        evidence_payloads["pdf_to_docx_result"] = pdf_docx_payload

        v1_ev, v1_payload = _run_v1_pdf_to_md(
            http_base_url=service_url,
            api_key=args.api_key,
            output_dir=artifacts_dir,
            pdf_path=pdf_fixture,
            wait_seconds=args.wait_seconds,
            max_poll_seconds=max(args.max_poll_seconds, 240.0),
        )
        evidence_payloads["v1_pdf_to_md_result"] = v1_payload
    except ClientError as exc:
        raise SystemExit(f"Verification failed: {exc.code} ({exc.message})") from exc

    for key, payload in evidence_payloads.items():
        _write_json(responses_dir / f"{key}.json", payload)

    pdf_docx_meta = v2_results["pdf_to_docx"]
    if pdf_docx_meta.backend_used is None or pdf_docx_meta.acceleration_used is None:
        raise SystemExit(
            "v2 pdf->docx result is missing backend_used/acceleration_used in conversion_metadata."
        )

    report: dict[str, object] = {
        "generated_at": _utc_now_iso(),
        "lane": args.lane,
        "service_url": service_url,
        "repo_head": repo_head,
        "runtime_versions": runtime_versions,
        "jobs": {
            "v2": {
                name: {
                    "job_id": ev.job_id,
                    "artifact_path": ev.artifact_path.as_posix(),
                    "artifact_size_bytes": ev.artifact_size_bytes,
                    "artifact_sha256": ev.artifact_sha256,
                    "pipeline_used": ev.pipeline_used,
                    "backend_used": ev.backend_used,
                    "acceleration_used": ev.acceleration_used,
                }
                for name, ev in v2_results.items()
            },
            "v1_pdf_to_md": {
                "job_id": v1_ev.job_id,
                "artifact_path": v1_ev.artifact_path.as_posix(),
                "artifact_size_bytes": v1_ev.artifact_size_bytes,
                "artifact_sha256": v1_ev.artifact_sha256,
                "pipeline_used": v1_ev.pipeline_used,
                "backend_used": v1_ev.backend_used,
                "acceleration_used": v1_ev.acceleration_used,
            },
        },
    }
    _write_json(output_root / "report.json", report)

    md_lines: list[str] = []
    md_lines.append("# Task 39 — Hemma v2 conversion smoke verification")
    md_lines.append("")
    md_lines.append(f"- generated_at: `{report['generated_at']}`")
    md_lines.append(f"- lane: `{args.lane}`")
    md_lines.append(f"- service_url: `{service_url}`")
    md_lines.append(f"- repo_head: `{repo_head}`")
    md_lines.append("")
    md_lines.append("## Runtime probes")
    md_lines.append("")
    md_lines.append(f"- pandoc: `{runtime_versions['pandoc_version'].splitlines()[0]}`")
    md_lines.append(f"- weasyprint: `{runtime_versions['weasyprint_version']}`")
    md_lines.append("")
    md_lines.append("## Route evidence")
    md_lines.append("")
    for name, ev in v2_results.items():
        md_lines.append(f"### v2 {name.replace('_', ' ')}")
        md_lines.append("")
        md_lines.append(f"- job_id: `{ev.job_id}`")
        md_lines.append(f"- artifact: `{ev.artifact_path}` ({ev.artifact_size_bytes} bytes)")
        if ev.pipeline_used is not None:
            md_lines.append(f"- pipeline_used: `{ev.pipeline_used}`")
        if ev.backend_used is not None:
            md_lines.append(f"- backend_used: `{ev.backend_used}`")
        if ev.acceleration_used is not None:
            md_lines.append(f"- acceleration_used: `{ev.acceleration_used}`")
        md_lines.append("")

    md_lines.append("### v1 pdf -> md")
    md_lines.append("")
    md_lines.append(f"- job_id: `{v1_ev.job_id}`")
    md_lines.append(f"- artifact: `{v1_ev.artifact_path}` ({v1_ev.artifact_size_bytes} bytes)")
    if v1_ev.backend_used is not None:
        md_lines.append(f"- backend_used: `{v1_ev.backend_used}`")
    if v1_ev.acceleration_used is not None:
        md_lines.append(f"- acceleration_used: `{v1_ev.acceleration_used}`")
    md_lines.append("")
    md_lines.append("## Files")
    md_lines.append("")
    md_lines.append(f"- report: `{(output_root / 'report.json').as_posix()}`")
    md_lines.append(f"- report_md: `{(output_root / 'report.md').as_posix()}`")
    md_lines.append(f"- artifacts: `{artifacts_dir.as_posix()}`")
    md_lines.append(f"- responses: `{responses_dir.as_posix()}`")
    md_lines.append(f"- runtime: `{runtime_dir.as_posix()}`")
    md_lines.append("")

    (output_root / "report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print((output_root / "report.md").as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
