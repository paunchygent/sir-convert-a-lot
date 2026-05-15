"""Exam.net-oriented DigiExam PDF renderer coordinator.

Purpose:
    Coordinate target-specific asset, item, and HTML planning for a
    WeasyPrint-backed PDF intended for Exam.net's PDF converter.

Relationships:
    - Consumes renderer-neutral IR from `domain.digiexam_ir_contracts`.
    - Delegates SRP work to Exam.net PDF asset, item, and HTML modules.
    - Feeds `infrastructure.digiexam_examnet_pdf_renderer` without handling
      filesystem or WeasyPrint concerns.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamParseStatus
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_assets import (
    prepare_examnet_pdf_assets,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfDocument,
    DigiExamExamNetPdfRenderPolicy,
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
    blocking_examnet_pdf_warnings,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_html import (
    build_examnet_pdf_html,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_items import (
    render_examnet_pdf_items,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
)


def build_digiexam_examnet_pdf_document(
    exam: DigiExamIntermediateExam,
    *,
    accepted_current_state_item_ids: tuple[str, ...] = (),
) -> DigiExamExamNetPdfDocument:
    """Build an Exam.net PDF-converter HTML plan from a DigiExam IR exam."""

    readiness_warnings = _readiness_warnings(exam)
    if readiness_warnings:
        return _blocked(readiness_warnings)

    asset_preparation = prepare_examnet_pdf_assets(exam)
    if asset_preparation.warnings:
        return _blocked(asset_preparation.warnings)

    item_result = render_examnet_pdf_items(
        exam=exam,
        asset_paths_by_reference=asset_preparation.asset_paths_by_reference,
        render_policy=DigiExamExamNetPdfRenderPolicy(
            accepted_current_state_item_ids=accepted_current_state_item_ids
        ),
    )
    if blocking_examnet_pdf_warnings(item_result.warnings):
        return _blocked(item_result.warnings)

    return DigiExamExamNetPdfDocument(
        status=DigiExamExamNetPdfStatus.SUCCESS,
        html=build_examnet_pdf_html(source_filename=exam.source_filename, items=item_result.items),
        asset_files=asset_preparation.asset_files,
        warnings=item_result.warnings,
    )


def _readiness_warnings(
    exam: DigiExamIntermediateExam,
) -> tuple[DigiExamExamNetPdfWarning, ...]:
    if exam.parse_status == DigiExamParseStatus.SUCCESS and exam.renderer_ready:
        return ()
    return (
        DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.PARSER_RESULT_BLOCKS_RENDERING,
            message="The DigiExam IR is not renderer-ready.",
            item_id=None,
        ),
    )


def _blocked(
    warnings: tuple[DigiExamExamNetPdfWarning, ...],
) -> DigiExamExamNetPdfDocument:
    return DigiExamExamNetPdfDocument(
        status=DigiExamExamNetPdfStatus.BLOCKED,
        html="",
        asset_files=(),
        warnings=warnings,
    )
