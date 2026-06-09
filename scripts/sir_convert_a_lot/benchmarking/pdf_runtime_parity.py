"""Hemma deploy verification runtime parity ingestion for PDF throughput benchmark evidence.

Purpose:
    Parse Hemma deploy verification parity reports or explicit CLI parity flags into the runtime
    parity summary embedded in PDF throughput lane/PDF throughput benchmark payloads.

Relationships:
    - Used by `pdf_throughput_profile_runner` when building the PDF throughput benchmark evidence
      bundle.
    - Keeps dirty PDF OCR benchmark dirty-corpus benchmark evidence tied to deploy/runtime
      parity instead of harness-only measurements.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .pdf_throughput_types import (
    DeployParityReportChecks,
    DeployParityReportPayload,
    RuntimeParitySummary,
    RuntimeSurface,
)


@dataclass(frozen=True)
class RuntimeParityInputs:
    """Optional Hemma deploy verification parity metadata provided to the benchmark harness."""

    report_json_path: Path | None
    status: str | None
    lane: str | None
    expected_revision: str | None
    remote_revision: str | None
    service_revision: str | None
    expected_revision_matches_remote: bool | None
    service_revision_matches_remote: bool | None
    live_smoke_passed: bool | None
    metrics_scan_passed: bool | None


def coerce_optional_str(value: object) -> str | None:
    """Return a stripped string value or `None`."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def _coerce_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _read_runtime_parity_report(report_json_path: Path) -> DeployParityReportPayload:
    payload_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
    if not isinstance(payload_obj, dict):
        raise ValueError(
            "Hemma deploy verification parity report must contain a JSON object at the root."
        )
    raw_checks = payload_obj.get("checks")
    checks_obj: object = raw_checks if isinstance(raw_checks, dict) else {}
    checks: DeployParityReportChecks = {
        "expected_revision_matches_remote": _coerce_optional_bool(
            checks_obj.get("expected_revision_matches_remote")
            if isinstance(checks_obj, dict)
            else None
        ),
        "service_revision_matches_remote": _coerce_optional_bool(
            checks_obj.get("service_revision_matches_remote")
            if isinstance(checks_obj, dict)
            else None
        ),
        "live_smoke_passed": _coerce_optional_bool(
            checks_obj.get("live_smoke_passed") if isinstance(checks_obj, dict) else None
        ),
        "metrics_scan_passed": _coerce_optional_bool(
            checks_obj.get("metrics_scan_passed") if isinstance(checks_obj, dict) else None
        ),
    }
    return {
        "status": coerce_optional_str(payload_obj.get("status")),
        "lane": coerce_optional_str(payload_obj.get("lane")),
        "expected_revision": coerce_optional_str(payload_obj.get("expected_revision")),
        "remote_revision": coerce_optional_str(payload_obj.get("remote_revision")),
        "service_revision": coerce_optional_str(payload_obj.get("service_revision")),
        "checks": checks,
    }


def build_runtime_parity_summary(
    *,
    inputs: RuntimeParityInputs,
) -> tuple[RuntimeSurface, RuntimeParitySummary]:
    """
    Build PDF throughput benchmark runtime surface and Hemma deploy verification parity summaries.
    """
    parity_source = "none"
    status = inputs.status
    lane = inputs.lane
    expected_revision = inputs.expected_revision
    remote_revision = inputs.remote_revision
    service_revision = inputs.service_revision
    expected_revision_matches_remote = inputs.expected_revision_matches_remote
    service_revision_matches_remote = inputs.service_revision_matches_remote
    live_smoke_passed = inputs.live_smoke_passed
    metrics_scan_passed = inputs.metrics_scan_passed

    if inputs.report_json_path is not None:
        report_payload = _read_runtime_parity_report(inputs.report_json_path)
        checks_obj = report_payload["checks"]
        parity_source = f"deploy_parity_report_json:{inputs.report_json_path.as_posix()}"
        status = report_payload["status"] or status
        lane = report_payload["lane"] or lane
        expected_revision = report_payload["expected_revision"] or expected_revision
        remote_revision = report_payload["remote_revision"] or remote_revision
        service_revision = report_payload["service_revision"] or service_revision
        expected_revision_matches_remote = checks_obj["expected_revision_matches_remote"]
        if expected_revision_matches_remote is None:
            expected_revision_matches_remote = inputs.expected_revision_matches_remote
        service_revision_matches_remote = checks_obj["service_revision_matches_remote"]
        if service_revision_matches_remote is None:
            service_revision_matches_remote = inputs.service_revision_matches_remote
        live_smoke_passed = checks_obj["live_smoke_passed"]
        if live_smoke_passed is None:
            live_smoke_passed = inputs.live_smoke_passed
        metrics_scan_passed = checks_obj["metrics_scan_passed"]
        if metrics_scan_passed is None:
            metrics_scan_passed = inputs.metrics_scan_passed
    elif any(
        value is not None
        for value in [
            status,
            lane,
            expected_revision,
            remote_revision,
            service_revision,
            expected_revision_matches_remote,
            service_revision_matches_remote,
            live_smoke_passed,
            metrics_scan_passed,
        ]
    ):
        parity_source = "cli_flags"

    notes: list[str] = []
    parity_proven = True
    if status != "passed":
        parity_proven = False
        notes.append("Hemma deploy verification parity status is not `passed`.")
    if expected_revision is None or remote_revision is None or service_revision is None:
        parity_proven = False
        notes.append("Missing expected/remote/service revision metadata.")
    if expected_revision_matches_remote is not True:
        parity_proven = False
        notes.append("`expected_revision_matches_remote` is not true.")
    if service_revision_matches_remote is not True:
        parity_proven = False
        notes.append("`service_revision_matches_remote` is not true.")
    if live_smoke_passed is not True:
        parity_proven = False
        notes.append("Hemma deploy verification live smoke proof is missing or failed.")
    if metrics_scan_passed is not True:
        parity_proven = False
        notes.append("Hemma deploy verification metrics safety proof is missing or failed.")

    runtime_surface: RuntimeSurface = {
        "mode": "in_process_app",
        "host": None,
        "service_url": None,
        "parity_source": parity_source,
    }
    runtime_parity: RuntimeParitySummary = {
        "status": status,
        "lane": lane,
        "expected_revision": expected_revision,
        "remote_revision": remote_revision,
        "service_revision": service_revision,
        "expected_revision_matches_remote": expected_revision_matches_remote,
        "service_revision_matches_remote": service_revision_matches_remote,
        "live_smoke_passed": live_smoke_passed,
        "metrics_scan_passed": metrics_scan_passed,
        "parity_proven": parity_proven,
        "notes": notes,
    }
    return runtime_surface, runtime_parity
