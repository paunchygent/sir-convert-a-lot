"""DigiExam point-correction application for effective renderer input.

Purpose:
    Validate and apply source-bound teacher corrections for item point values
    without changing parser-owned DigiExam source IR or answer-key provenance.

Relationships:
    - Consumes overlay DTOs from `domain.digiexam_ingestion_overlay_contracts`.
    - Called by `domain.digiexam_ingestion_overlay` during effective overlay
      application.
    - Feeds PDF/QTI renderers through corrected effective `DigiExamIrItem`
      values and effective-report summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamEffectivePointCorrection,
    DigiExamIngestionOverlayError,
    DigiExamIngestionOverlayItem,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem


@dataclass(frozen=True)
class DigiExamPointCorrectionApplication:
    """Applied point-correction result for overlay coordination."""

    item: DigiExamIrItem
    summary: DigiExamEffectivePointCorrection


def apply_point_correction(
    *,
    entry: DigiExamIngestionOverlayItem,
    item: DigiExamIrItem,
) -> DigiExamPointCorrectionApplication | None:
    """Return an effective item with corrected points when requested."""

    correction = entry.point_correction
    if correction is None:
        return None
    if item.item_type not in _SUPPORTED_POINT_CORRECTION_ITEM_TYPES:
        raise DigiExamIngestionOverlayError(
            "digiexam_ingestion_overlay_point_correction_target_incompatible",
            "Point correction is unsupported for this DigiExam item type.",
            {
                "item_id": entry.item_id,
                "sequence": entry.sequence,
                "item_type": item.item_type.value,
            },
        )
    corrected_item = replace(item, max_score=correction.max_score)
    return DigiExamPointCorrectionApplication(
        item=corrected_item,
        summary=DigiExamEffectivePointCorrection(
            kind=correction.kind,
            source_max_score=item.max_score,
            effective_max_score=correction.max_score,
            source_item_fingerprint=entry.source_item_fingerprint,
        ),
    )


_SUPPORTED_POINT_CORRECTION_ITEM_TYPES = frozenset(
    {
        DigiExamItemType.OPEN_ENDED,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    }
)
