"""Run real Hemma Docling GPU conversions with strict high-quality settings.

Purpose:
    Provide a committed, deterministic live-run command for validating the
    production-like Docling GPU path on real scientific-paper PDFs.

Relationships:
    - Calls the canonical v1 HTTP API exposed by `interfaces.http_api`.
    - Intended to run on Hemma via `pdm run run-hemma -- pdm run ...`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol

import httpx

DEFAULT_SERVICE_URL = "http://127.0.0.1:28085"
DEFAULT_CORPUS_DIR = Path(
    "/home/paunchygent/apps/huleedu/docs/research/research_papers/llm_as_a_annotater"
)
DEFAULT_OUTPUT_ROOT = Path("build/live-tests")


def utc_now_iso() -> str:
    """Return current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug_for_pdf(path: Path) -> str:
    """Return deterministic slug for one PDF file path."""
    normalized = "".join(
        character.lower() if character.isalnum() else "-" for character in path.stem
    )
    compact = "-".join(part for part in normalized.split("-") if part)
    digest = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:8]
    return f"{compact[:60] or 'doc'}-{digest}"


def parse_gpu_busy_peak(smi_output: str) -> int:
    """Parse maximum GPU busy percent from `rocm-smi --showuse` output."""
    peak = 0
    for match in re.finditer(r"GPU use \(%\):\s*([0-9]+)", smi_output):
        peak = max(peak, int(match.group(1)))
    return peak


def sample_gpu_busy_peak(previous_peak: int) -> int:
    """Sample `rocm-smi` once and return updated max busy percent."""
    result = subprocess.run(
        ["rocm-smi", "--showuse"],
        check=False,
        capture_output=True,
        text=True,
    )
    return max(previous_peak, parse_gpu_busy_peak(result.stdout))


def try_read_git_head() -> str | None:
    """Best-effort read of repository `HEAD` revision."""
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return output if output != "" else None


@dataclass(frozen=True)
class LiveRunSettings:
    """Runtime settings for Docling GPU live conversion run."""

    service_url: str
    api_key: str
    corpus_dir: Path
    output_root: Path
    ocr_mode: str
    table_mode: str
    normalize: str
    acceleration_policy: str
    priority: str
    document_timeout_seconds: int
    poll_interval_seconds: float
    max_wait_seconds: float
    expected_service_revision: str | None


@dataclass
class LiveJobRecord:
    """Per-document live run record."""

    source_file: str
    source_size_bytes: int
    document_slug: str
    job_id: str | None = None
    status: str = "failed"
    error_code: str | None = None
    backend_used: str | None = None
    acceleration_used: str | None = None
    ocr_enabled: bool | None = None
    warnings: list[str] = field(default_factory=list)
    gpu_busy_peak: int = 0
    latency_seconds: float = 0.0
    markdown_path: str | None = None
    metadata_path: str | None = None
    manifest_consistent: bool | None = None


@dataclass
class LiveRunSummary:
    """Aggregate live run summary."""

    started_at: str
    finished_at: str | None
    service_url: str
    service_revision: str | None
    corpus_dir: str
    output_root: str
    settings: dict[str, object]
    total: int
    succeeded: int
    failed: int
    metadata_mismatch: int
    manifest_inconsistent: int
    jobs: list[LiveJobRecord]


def build_job_spec(filename: str, settings: LiveRunSettings) -> dict[str, object]:
    """Build deterministic job spec for one file using strict Docling settings."""
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": "docling",
            "ocr_mode": settings.ocr_mode,
            "table_mode": settings.table_mode,
            "normalize": settings.normalize,
        },
        "execution": {
            "acceleration_policy": settings.acceleration_policy,
            "priority": settings.priority,
            "document_timeout_seconds": settings.document_timeout_seconds,
        },
        "retention": {"pin": False},
    }


def read_error_code(response: httpx.Response) -> str | None:
    """Extract API error code from standard envelope, if present."""
    try:
        payload = response.json()
    except Exception:
        return None
    error_obj = payload.get("error")
    if not isinstance(error_obj, dict):
        return None
    code_obj = error_obj.get("code")
    return code_obj if isinstance(code_obj, str) else None


def manifest_is_consistent(result_payload: dict[str, object]) -> bool:
    """Return `True` when inline markdown matches declared artifact hash and size."""
    artifact_obj = result_payload.get("artifact")
    markdown_obj = result_payload.get("markdown_content")
    if not isinstance(artifact_obj, dict) or not isinstance(markdown_obj, str):
        return False

    sha_obj = artifact_obj.get("sha256")
    size_obj = artifact_obj.get("size_bytes")
    if not isinstance(sha_obj, str) or not isinstance(size_obj, int):
        return False

    markdown_bytes = markdown_obj.encode("utf-8")
    inline_sha = hashlib.sha256(markdown_bytes).hexdigest()
    inline_size = len(markdown_bytes)
    return inline_sha == sha_obj and inline_size == size_obj


def fetch_result_with_manifest_check(
    *,
    fetch_result: Callable[[str, dict[str, str]], FetchResultResponse],
    job_id: str,
    api_key: str,
    max_attempts: int = 3,
    retry_delay_seconds: float = 0.2,
) -> tuple[dict[str, object], bool]:
    """Fetch inline result and validate manifest consistency with bounded retries."""
    attempts = max(1, max_attempts)
    last_result_payload: dict[str, object] | None = None

    for attempt in range(attempts):
        try:
            response = fetch_result(
                f"/v1/convert/jobs/{job_id}/result?inline=true",
                {"X-API-Key": api_key},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            if attempt >= attempts - 1:
                raise
            time.sleep(retry_delay_seconds)
            continue

        if not isinstance(payload, dict):
            if attempt >= attempts - 1:
                raise ValueError("result response payload is not a JSON object")
            time.sleep(retry_delay_seconds)
            continue

        result_obj = payload.get("result")
        if not isinstance(result_obj, dict):
            if attempt >= attempts - 1:
                raise ValueError("result response is missing result object")
            time.sleep(retry_delay_seconds)
            continue

        normalized_result = {str(k): v for k, v in result_obj.items()}
        last_result_payload = normalized_result
        if manifest_is_consistent(normalized_result):
            return normalized_result, True

        if attempt < attempts - 1:
            time.sleep(retry_delay_seconds)

    if last_result_payload is None:
        raise ValueError("unable to fetch conversion result payload")
    return last_result_payload, False


def run_live_test(settings: LiveRunSettings) -> tuple[LiveRunSummary, Path]:
    """Execute live conversion run and return summary + summary file path."""
    pdf_paths = sorted(path for path in settings.corpus_dir.glob("*.pdf") if path.is_file())
    if not pdf_paths:
        raise ValueError(f"No PDF files found in corpus path: {settings.corpus_dir}")

    run_id = f"docling-gpu-high-quality-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_output_root = settings.output_root / run_id
    markdown_dir = run_output_root / "markdown"
    meta_dir = run_output_root / "meta"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    summary = LiveRunSummary(
        started_at=utc_now_iso(),
        finished_at=None,
        service_url=settings.service_url,
        service_revision=None,
        corpus_dir=str(settings.corpus_dir),
        output_root=str(run_output_root),
        settings={
            "backend_strategy": "docling",
            "ocr_mode": settings.ocr_mode,
            "table_mode": settings.table_mode,
            "normalize": settings.normalize,
            "acceleration_policy": settings.acceleration_policy,
            "expected_service_revision": settings.expected_service_revision,
        },
        total=len(pdf_paths),
        succeeded=0,
        failed=0,
        metadata_mismatch=0,
        manifest_inconsistent=0,
        jobs=[],
    )

    timeout = httpx.Timeout(timeout=60.0, connect=10.0)
    with httpx.Client(base_url=settings.service_url, timeout=timeout) as client:
        health_response = client.get("/healthz")
        health_response.raise_for_status()
        health_payload = health_response.json()
        if not isinstance(health_payload, dict) or health_payload.get("status") != "ok":
            raise ValueError("Service health endpoint did not return status=ok payload.")
        revision_obj = health_payload.get("service_revision")
        if not isinstance(revision_obj, str) or revision_obj.strip() == "":
            raise ValueError("Service health payload is missing service_revision.")
        summary.service_revision = revision_obj
        if settings.expected_service_revision is not None and (
            revision_obj != settings.expected_service_revision
        ):
            raise ValueError(
                "Service revision mismatch: "
                f"expected={settings.expected_service_revision} actual={revision_obj}"
            )

        for index, pdf_path in enumerate(pdf_paths, start=1):
            file_bytes = pdf_path.read_bytes()
            document_slug = slug_for_pdf(pdf_path)
            print(f"[live] ({index}/{len(pdf_paths)}) submit: {pdf_path.name}", flush=True)

            record = LiveJobRecord(
                source_file=pdf_path.name,
                source_size_bytes=len(file_bytes),
                document_slug=document_slug,
            )
            started = time.monotonic()

            idempotency_key = (
                "live_docling_gpu_"
                + hashlib.sha256(file_bytes).hexdigest()[:16]
                + f"_{int(time.time())}_{index:02d}"
            )
            create_response = client.post(
                "/v1/convert/jobs?wait_seconds=0",
                headers={
                    "X-API-Key": settings.api_key,
                    "Idempotency-Key": idempotency_key,
                },
                files={
                    "file": (pdf_path.name, file_bytes, "application/pdf"),
                    "job_spec": (
                        None,
                        json.dumps(build_job_spec(pdf_path.name, settings), separators=(",", ":")),
                    ),
                },
            )
            if create_response.status_code not in {200, 202}:
                record.error_code = read_error_code(create_response)
                record.latency_seconds = round(time.monotonic() - started, 6)
                summary.failed += 1
                summary.jobs.append(record)
                print(f"[live] create failed: {pdf_path.name} -> {record.error_code}", flush=True)
                continue

            create_payload = create_response.json()
            record.job_id = str(create_payload["job"]["job_id"])

            deadline = time.monotonic() + settings.max_wait_seconds
            peak = 0
            final_status = "unknown"
            while time.monotonic() < deadline:
                peak = sample_gpu_busy_peak(peak)
                status_response = client.get(
                    f"/v1/convert/jobs/{record.job_id}",
                    headers={"X-API-Key": settings.api_key},
                )
                status_response.raise_for_status()
                final_status = str(status_response.json()["job"]["status"])
                if final_status in {"succeeded", "failed", "canceled"}:
                    break
                time.sleep(settings.poll_interval_seconds)

            record.status = final_status
            record.gpu_busy_peak = peak
            record.latency_seconds = round(time.monotonic() - started, 6)

            if final_status == "succeeded":
                try:
                    result_payload, manifest_consistent = fetch_result_with_manifest_check(
                        fetch_result=lambda url, headers: client.get(url, headers=headers),
                        job_id=record.job_id,
                        api_key=settings.api_key,
                    )
                except (httpx.HTTPError, ValueError):
                    record.error_code = "result_fetch_failed"
                    summary.failed += 1
                    summary.jobs.append(record)
                    print(
                        f"[live] result fetch failed: {pdf_path.name} job_id={record.job_id}",
                        flush=True,
                    )
                    continue

                conversion_metadata_obj = result_payload.get("conversion_metadata")
                if not isinstance(conversion_metadata_obj, dict):
                    record.error_code = "result_metadata_missing"
                    summary.failed += 1
                    summary.jobs.append(record)
                    print(
                        f"[live] metadata missing: {pdf_path.name} job_id={record.job_id}",
                        flush=True,
                    )
                    continue

                conversion_metadata = conversion_metadata_obj
                warnings_obj = result_payload.get("warnings", [])
                markdown_content = str(result_payload["markdown_content"])
                record.manifest_consistent = manifest_consistent
                if not manifest_consistent:
                    summary.manifest_inconsistent += 1
                    record.error_code = "manifest_inconsistent"

                record.backend_used = str(conversion_metadata.get("backend_used"))
                record.acceleration_used = str(conversion_metadata.get("acceleration_used"))
                record.ocr_enabled = bool(conversion_metadata.get("ocr_enabled"))
                record.warnings = (
                    [str(item) for item in warnings_obj] if isinstance(warnings_obj, list) else []
                )

                markdown_path = markdown_dir / f"{document_slug}.md"
                metadata_path = meta_dir / f"{document_slug}.meta.json"
                markdown_path.write_text(markdown_content, encoding="utf-8")
                metadata_path.write_text(
                    json.dumps(asdict(record), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                record.markdown_path = markdown_path.as_posix()
                record.metadata_path = metadata_path.as_posix()

                backend_ok = record.backend_used == "docling"
                acceleration_ok = record.acceleration_used == "cuda"
                if not (backend_ok and acceleration_ok):
                    summary.metadata_mismatch += 1
                    print(
                        "[live] metadata mismatch "
                        + (
                            f"{pdf_path.name}: backend={record.backend_used} "
                            f"acceleration={record.acceleration_used}"
                        ),
                        flush=True,
                    )
                elif not manifest_consistent:
                    print(
                        f"[live] manifest mismatch {pdf_path.name}: job_id={record.job_id}",
                        flush=True,
                    )
                else:
                    print(
                        f"[live] succeeded {pdf_path.name} in {record.latency_seconds:.2f}s "
                        f"gpu_peak={record.gpu_busy_peak}%",
                        flush=True,
                    )
                summary.succeeded += 1
            else:
                result_response = client.get(
                    f"/v1/convert/jobs/{record.job_id}/result",
                    headers={"X-API-Key": settings.api_key},
                )
                record.error_code = read_error_code(result_response)
                summary.failed += 1
                print(
                    f"[live] terminal failure {pdf_path.name}: "
                    f"status={final_status} error={record.error_code}",
                    flush=True,
                )

            summary.jobs.append(record)

    summary.finished_at = utc_now_iso()
    summary_path = run_output_root / "summary.json"
    payload = asdict(summary)
    payload["jobs"] = [asdict(record) for record in summary.jobs]
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary, summary_path


def parse_args() -> LiveRunSettings:
    """Parse CLI arguments into typed live-run settings."""
    parser = argparse.ArgumentParser(description="Run real Hemma Docling GPU live conversion test.")
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--api-key", default="dev-only-key")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--ocr-mode", default="auto")
    parser.add_argument("--table-mode", default="accurate")
    parser.add_argument("--normalize", default="strict")
    parser.add_argument("--acceleration-policy", default="gpu_required")
    parser.add_argument("--priority", default="normal")
    parser.add_argument("--document-timeout-seconds", type=int, default=7200)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.5)
    parser.add_argument("--max-wait-seconds", type=float, default=7200.0)
    parser.add_argument("--expected-service-revision", default=None)
    args = parser.parse_args()
    expected_service_revision: str | None
    if args.expected_service_revision is None or args.expected_service_revision.strip() == "":
        expected_service_revision = try_read_git_head()
    else:
        expected_service_revision = str(args.expected_service_revision)

    return LiveRunSettings(
        service_url=args.service_url,
        api_key=args.api_key,
        corpus_dir=args.corpus_dir,
        output_root=args.output_root,
        ocr_mode=args.ocr_mode,
        table_mode=args.table_mode,
        normalize=args.normalize,
        acceleration_policy=args.acceleration_policy,
        priority=args.priority,
        document_timeout_seconds=args.document_timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        max_wait_seconds=args.max_wait_seconds,
        expected_service_revision=expected_service_revision,
    )


def main() -> None:
    """Run the live test and return non-zero on failures or metadata mismatches."""
    settings = parse_args()
    summary, summary_path = run_live_test(settings)
    print(
        json.dumps(
            {
                "summary_path": str(summary_path),
                "output_root": summary.output_root,
                "total": summary.total,
                "succeeded": summary.succeeded,
                "failed": summary.failed,
                "metadata_mismatch": summary.metadata_mismatch,
                "manifest_inconsistent": summary.manifest_inconsistent,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if summary.failed > 0 or summary.metadata_mismatch > 0 or summary.manifest_inconsistent > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()


class FetchResultResponse(Protocol):
    """Protocol for result response methods used by manifest integrity checks."""

    def raise_for_status(self) -> object: ...

    def json(self) -> object: ...
