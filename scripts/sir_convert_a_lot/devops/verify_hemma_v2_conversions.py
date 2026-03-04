"""Hemma v2 conversion smoke verification (Task 39).

Purpose:
    Produce deterministic evidence that the Hemma dockerized runtime can execute
    the critical multi-format conversion routes exposed via service API v2:
    `html -> pdf`, `md -> pdf`, `md -> docx`, `pdf -> docx`, and `pdf -> md`.

Relationships:
    - Called by `scripts/devops/verify-hemma-v2-conversions.sh` (remote mode).
    - Uses the typed HTTP clients:
        - `scripts.sir_convert_a_lot.interfaces.http_client_v2.SirConvertALotClientV2` (v2)
    - Writes evidence under `build/verification/task-39-v2-smoke/` (artifacts,
      responses, and a markdown + JSON report).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions_helpers import (
    ArtifactEvidence,
    assert_readyz_contract,
    build_resources_zip,
    fetch_json,
    probe_docker_runtime,
    run_v2_conversion,
    utc_now_iso,
    write_json,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2 import ClientErrorV2


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
        help="PDF fixture path used for v2 `pdf -> md` and `pdf -> docx` smoke.",
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
        healthz = fetch_json(
            client,
            path="/healthz",
            headers={"X-API-Key": args.api_key},
            label="healthz",
        )
        readyz = fetch_json(
            client,
            path="/readyz",
            headers={"X-API-Key": args.api_key},
            label="readyz",
        )
    write_json(output_root / "healthz.json", healthz)
    write_json(output_root / "readyz.json", readyz)
    assert_readyz_contract(readyz=readyz, repo_head=repo_head)

    runtime_versions = probe_docker_runtime(
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

    resources_zip_bytes = build_resources_zip(files={css_path.name: css_path.read_bytes()})
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
        html_ev, html_payload = run_v2_conversion(
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

        md_pdf_ev, md_pdf_payload = run_v2_conversion(
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

        md_docx_ev, md_docx_payload = run_v2_conversion(
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

        pdf_docx_ev, pdf_docx_payload = run_v2_conversion(
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

        pdf_md_ev, pdf_md_payload = run_v2_conversion(
            http_base_url=service_url,
            api_key=args.api_key,
            output_dir=artifacts_dir,
            label="pdf_to_md",
            source_path=pdf_fixture,
            job_spec=_spec_v2(
                source=pdf_fixture,
                source_format="pdf",
                output_format="md",
                css=False,
            ),
            artifact_suffix=".md",
            wait_seconds=args.wait_seconds,
            max_poll_seconds=max(args.max_poll_seconds, 240.0),
            resources_zip_bytes=None,
        )
        v2_results["pdf_to_md"] = pdf_md_ev
        evidence_payloads["pdf_to_md_result"] = pdf_md_payload
    except ClientErrorV2 as exc:
        raise SystemExit(f"Verification failed: {exc.code} ({exc.message})") from exc

    for key, payload in evidence_payloads.items():
        write_json(responses_dir / f"{key}.json", payload)

    pdf_docx_meta = v2_results["pdf_to_docx"]
    if pdf_docx_meta.backend_used is None or pdf_docx_meta.acceleration_used is None:
        raise SystemExit(
            "v2 pdf->docx result is missing backend_used/acceleration_used in conversion_metadata."
        )

    report: dict[str, object] = {
        "generated_at": utc_now_iso(),
        "lane": args.lane,
        "service_url": service_url,
        "repo_head": repo_head,
        "runtime_versions": runtime_versions,
        "jobs": {
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
    }
    write_json(output_root / "report.json", report)

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
