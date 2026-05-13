"""Exam.net-oriented DigiExam PDF renderer infrastructure.

Purpose:
    Materialize the domain Exam.net PDF renderer plan as local HTML, image
    assets, and a WeasyPrint-generated PDF artifact.

Relationships:
    - Consumes `domain.digiexam_examnet_pdf` document plans.
    - Reuses `infrastructure.weasyprint_html_to_pdf` for bounded local PDF
      generation and resource access control.
    - Leaves service/API route wiring and bulk artifact orchestration to later
      EPIC-10 workflow slices.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarning,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
)
from scripts.sir_convert_a_lot.infrastructure.weasyprint_html_to_pdf import (
    convert_html_to_pdf,
)


@dataclass(frozen=True)
class DigiExamExamNetPdfArtifacts:
    """Materialized Exam.net-oriented PDF renderer artifacts."""

    status: DigiExamExamNetPdfStatus
    pdf_path: Path
    html_path: Path | None
    asset_paths: tuple[Path, ...]
    warnings: tuple[DigiExamExamNetPdfWarning, ...]


def render_digiexam_examnet_pdf(
    *,
    exam: DigiExamIntermediateExam,
    output_pdf_path: Path,
    work_dir: Path | None = None,
) -> DigiExamExamNetPdfArtifacts:
    """Render one DigiExam IR exam to an Exam.net-oriented PDF artifact."""

    document = build_digiexam_examnet_pdf_document(exam)
    if document.status == DigiExamExamNetPdfStatus.BLOCKED:
        return DigiExamExamNetPdfArtifacts(
            status=document.status,
            pdf_path=output_pdf_path,
            html_path=None,
            asset_paths=(),
            warnings=document.warnings,
        )

    resolved_work_dir = work_dir or output_pdf_path.parent / f"{output_pdf_path.stem}-examnet-pdf"
    resolved_work_dir.mkdir(parents=True, exist_ok=True)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    html_path = resolved_work_dir / "examnet-import.html"
    html_path.write_text(document.html, encoding="utf-8")

    asset_paths: list[Path] = []
    for asset_file in document.asset_files:
        asset_path = resolved_work_dir / asset_file.relative_path
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(asset_file.payload)
        asset_paths.append(asset_path)

    convert_html_to_pdf(
        html_path=html_path,
        output_pdf_path=output_pdf_path,
        base_url=f"{resolved_work_dir.resolve().as_uri()}/",
        allowed_resource_root=resolved_work_dir,
    )
    return DigiExamExamNetPdfArtifacts(
        status=document.status,
        pdf_path=output_pdf_path,
        html_path=html_path,
        asset_paths=tuple(asset_paths),
        warnings=(),
    )
