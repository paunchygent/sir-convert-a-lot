"""Filesystem materialization for Exam.net-oriented QTI packages.

Purpose:
    Write deterministic QTI zip packages and validation reports from the
    filesystem-free domain package plan.

Relationships:
    - Consumes `domain.examnet_qti_package` plans.
    - Uses `domain.examnet_qti_validation` to produce the companion
      `qti_validation_report` artifact after package bytes are available.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
    ExamNetQtiValidationReport,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_validation import (
    build_examnet_qti_validation_report,
    examnet_qti_validation_report_to_json_data,
)

_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class ExamNetQtiWrittenArtifacts:
    """Materialized QTI artifact paths and validation report."""

    package_path: Path | None
    report_path: Path
    report: ExamNetQtiValidationReport


def write_examnet_qti_artifacts(
    *,
    plan: ExamNetQtiPackagePlan,
    output_dir: Path,
    package_filename: str = "qti-package.zip",
    report_filename: str = "qti-validation-report.json",
    report_package_filename: str | None = None,
) -> ExamNetQtiWrittenArtifacts:
    """Write a QTI package, when available, and its validation report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    package_path: Path | None = None
    package_bytes: bytes | None = None
    if plan.status == ExamNetQtiPackageStatus.PASSED:
        package_path = output_dir / package_filename
        package_bytes = build_examnet_qti_zip_bytes(plan)
        package_path.write_bytes(package_bytes)

    report = build_examnet_qti_validation_report(
        plan=plan,
        package_filename=report_package_filename or package_filename,
        package_bytes=package_bytes,
    )
    report_path = output_dir / report_filename
    report_data = examnet_qti_validation_report_to_json_data(report)
    report_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ExamNetQtiWrittenArtifacts(
        package_path=package_path,
        report_path=report_path,
        report=report,
    )


def build_examnet_qti_zip_bytes(plan: ExamNetQtiPackagePlan) -> bytes:
    """Return deterministic zip bytes for a passed QTI package plan."""

    if plan.status != ExamNetQtiPackageStatus.PASSED:
        raise ValueError("Only passed QTI package plans can be materialized as zip bytes.")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in plan.files:
            info = zipfile.ZipInfo(file.relative_path, date_time=_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, file.payload)
    return buffer.getvalue()
