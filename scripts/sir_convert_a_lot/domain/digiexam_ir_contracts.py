"""DigiExam renderer-neutral intermediate exam representation.

Purpose:
    Define the Sir Convert-owned intermediate exam model that sits between
    DigiExam parsers and later renderer/import targets.

Relationships:
    - Consumes `domain.digiexam_contracts` parser outputs without changing
      parser semantics.
    - Feeds future EPIC-10 renderer, parity-report, and bulk-workflow slices.
    - Intentionally avoids Exam.net, QTI, PDF-layout, service-route, and bulk
      orchestration details.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAlternative,
    DigiExamAnswerKeyProvenance,
    DigiExamEmbeddedAsset,
    DigiExamEmbeddedAssetReference,
    DigiExamGap,
    DigiExamGapAnswer,
    DigiExamGradingPolicy,
    DigiExamItem,
    DigiExamItemType,
    DigiExamMatchingStructure,
    DigiExamParseResult,
    DigiExamParseStatus,
    DigiExamSourceSpan,
    DigiExamWarning,
)

DIGIEXAM_IR_SCHEMA_VERSION: Literal["digiexam_intermediate_exam_v2"] = (
    "digiexam_intermediate_exam_v2"
)
DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION: Literal["digiexam_ir_manifest_v2"] = "digiexam_ir_manifest_v2"


class DigiExamIrManualFollowUpReason(StrEnum):
    """Manual follow-up reasons preserved by the renderer-neutral IR."""

    MANUAL_MARKING_REQUIRED = "manual_marking_required"
    MANUAL_ANSWER_KEY_REQUIRED = "manual_answer_key_required"
    UNSUPPORTED_ITEM_TYPE = "unsupported_item_type"
    PARSER_WARNING_BLOCKS_RENDERING = "parser_warning_blocks_rendering"


@dataclass(frozen=True)
class DigiExamIrAnswerKey:
    """Answer-key data and provenance kept separate from item structure."""

    provenance: DigiExamAnswerKeyProvenance
    correct_alternative_ids: tuple[int, ...]
    correct_gap_answers: tuple[DigiExamGapAnswer, ...]


@dataclass(frozen=True)
class DigiExamIrManualFollowUp:
    """One explicit manual action required before complete migration."""

    item_id: str
    reason: DigiExamIrManualFollowUpReason
    message: str
    source_span: DigiExamSourceSpan | None


@dataclass(frozen=True)
class DigiExamIrItem:
    """One renderer-neutral exam item with source structure and provenance."""

    item_id: str
    sequence: int
    title: str
    item_type: DigiExamItemType
    source_span: DigiExamSourceSpan
    prompt_html: str | None
    prompt_lines: tuple[str, ...]
    max_score: int | None
    digiexam_type_code: int | None
    options: tuple[str, ...]
    alternatives: tuple[DigiExamAlternative, ...]
    matching: DigiExamMatchingStructure | None
    gaps: tuple[DigiExamGap, ...]
    grading_policy: DigiExamGradingPolicy | None
    answer_key: DigiExamIrAnswerKey
    warnings: tuple[DigiExamWarning, ...]
    embedded_assets: tuple[DigiExamEmbeddedAsset, ...]
    embedded_asset_references: tuple[DigiExamEmbeddedAssetReference, ...]


@dataclass(frozen=True)
class DigiExamIntermediateExam:
    """Top-level renderer-neutral DigiExam exam representation."""

    schema_version: Literal["digiexam_intermediate_exam_v2"]
    source_filename: str
    source_producer: str | None
    parse_status: DigiExamParseStatus
    renderer_ready: bool
    items: tuple[DigiExamIrItem, ...]
    warnings: tuple[DigiExamWarning, ...]
    manual_follow_ups: tuple[DigiExamIrManualFollowUp, ...]


@dataclass(frozen=True)
class DigiExamIrManifestAssetSummary:
    """Deterministic asset summary for parity consumers."""

    item_id: str
    asset_id: str
    source_image_index: int
    sha256: str
    media_type: str
    byte_length: int
    width_px: int
    height_px: int
    reference_count: int
    reference_orders: tuple[int, ...]


@dataclass(frozen=True)
class DigiExamIrManifestItemSummary:
    """Deterministic item summary for parity and audit manifests."""

    item_id: str
    sequence: int
    title: str
    item_type: DigiExamItemType
    source_item_fingerprint: str
    answer_key_provenance: DigiExamAnswerKeyProvenance
    manual_follow_up_required: bool
    asset_summaries: tuple[DigiExamIrManifestAssetSummary, ...]


@dataclass(frozen=True)
class DigiExamIrManifest:
    """Deterministic renderer-neutral DigiExam manifest summary."""

    schema_version: Literal["digiexam_ir_manifest_v2"]
    exam_schema_version: Literal["digiexam_intermediate_exam_v2"]
    source_filename: str
    source_producer: str | None
    parse_status: DigiExamParseStatus
    renderer_ready: bool
    item_count: int
    asset_count: int
    asset_summaries: tuple[DigiExamIrManifestAssetSummary, ...]
    warning_count: int
    manual_follow_up_count: int
    item_summaries: tuple[DigiExamIrManifestItemSummary, ...]


def build_digiexam_intermediate_exam(parse_result: DigiExamParseResult) -> DigiExamIntermediateExam:
    """Build a renderer-neutral IR from one DigiExam parser result."""

    items: list[DigiExamIrItem] = []
    manual_follow_ups: list[DigiExamIrManualFollowUp] = []
    for sequence, source_item in enumerate(parse_result.items, start=1):
        item_id = _item_id(sequence)
        items.append(
            DigiExamIrItem(
                item_id=item_id,
                sequence=sequence,
                title=source_item.header,
                item_type=source_item.item_type,
                source_span=source_item.source_span,
                prompt_html=source_item.prompt_html,
                prompt_lines=source_item.prompt_lines,
                max_score=source_item.max_score,
                digiexam_type_code=source_item.digiexam_type_code,
                options=source_item.options,
                alternatives=source_item.alternatives,
                matching=source_item.matching,
                gaps=source_item.gaps,
                grading_policy=source_item.grading_policy,
                answer_key=DigiExamIrAnswerKey(
                    provenance=source_item.answer_key_provenance,
                    correct_alternative_ids=source_item.correct_alternative_ids,
                    correct_gap_answers=source_item.correct_gap_answers,
                ),
                warnings=source_item.warnings,
                embedded_assets=source_item.embedded_assets,
                embedded_asset_references=source_item.embedded_asset_references,
            )
        )
        manual_follow_ups.extend(_item_manual_follow_ups(item_id, source_item))

    for warning in parse_result.warnings:
        if warning.blocking:
            manual_follow_ups.append(
                DigiExamIrManualFollowUp(
                    item_id="exam",
                    reason=DigiExamIrManualFollowUpReason.PARSER_WARNING_BLOCKS_RENDERING,
                    message=warning.message,
                    source_span=warning.source_span,
                )
            )

    return DigiExamIntermediateExam(
        schema_version=DIGIEXAM_IR_SCHEMA_VERSION,
        source_filename=parse_result.metadata.filename,
        source_producer=parse_result.metadata.producer,
        parse_status=parse_result.status,
        renderer_ready=parse_result.renderer_ready,
        items=tuple(items),
        warnings=parse_result.warnings,
        manual_follow_ups=tuple(manual_follow_ups),
    )


def build_digiexam_ir_manifest(exam: DigiExamIntermediateExam) -> DigiExamIrManifest:
    """Build a deterministic manifest summary from a DigiExam IR exam."""

    from scripts.sir_convert_a_lot.domain.digiexam_source_fingerprints import (
        source_item_fingerprint,
    )

    manual_item_ids = {follow_up.item_id for follow_up in exam.manual_follow_ups}
    item_summaries = tuple(
        DigiExamIrManifestItemSummary(
            item_id=item.item_id,
            sequence=item.sequence,
            title=item.title,
            item_type=item.item_type,
            source_item_fingerprint=source_item_fingerprint(item),
            answer_key_provenance=item.answer_key.provenance,
            manual_follow_up_required=item.item_id in manual_item_ids,
            asset_summaries=_asset_summaries(item),
        )
        for item in exam.items
    )
    asset_summaries = tuple(
        asset_summary
        for item_summary in item_summaries
        for asset_summary in item_summary.asset_summaries
    )
    return DigiExamIrManifest(
        schema_version=DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION,
        exam_schema_version=exam.schema_version,
        source_filename=exam.source_filename,
        source_producer=exam.source_producer,
        parse_status=exam.parse_status,
        renderer_ready=exam.renderer_ready,
        item_count=len(exam.items),
        asset_count=len(asset_summaries),
        asset_summaries=asset_summaries,
        warning_count=len(exam.warnings),
        manual_follow_up_count=len(exam.manual_follow_ups),
        item_summaries=item_summaries,
    )


def _item_manual_follow_ups(
    item_id: str, source_item: DigiExamItem
) -> tuple[DigiExamIrManualFollowUp, ...]:
    follow_ups: list[DigiExamIrManualFollowUp] = []
    if source_item.item_type == DigiExamItemType.UNKNOWN:
        follow_ups.append(
            DigiExamIrManualFollowUp(
                item_id=item_id,
                reason=DigiExamIrManualFollowUpReason.UNSUPPORTED_ITEM_TYPE,
                message=f"Unsupported DigiExam item type for '{source_item.header}'.",
                source_span=source_item.source_span,
            )
        )
    if source_item.item_type == DigiExamItemType.OPEN_ENDED:
        follow_ups.append(
            DigiExamIrManualFollowUp(
                item_id=item_id,
                reason=DigiExamIrManualFollowUpReason.MANUAL_MARKING_REQUIRED,
                message=f"Manual marking is required for open-ended item '{source_item.header}'.",
                source_span=source_item.source_span,
            )
        )
    if (
        source_item.item_type in _MACHINE_MARKED_ITEM_TYPES
        and source_item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT
    ):
        follow_ups.append(
            DigiExamIrManualFollowUp(
                item_id=item_id,
                reason=DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED,
                message=f"Manual answer key is required for '{source_item.header}'.",
                source_span=source_item.source_span,
            )
        )
    for warning in source_item.warnings:
        if warning.blocking:
            follow_ups.append(
                DigiExamIrManualFollowUp(
                    item_id=item_id,
                    reason=DigiExamIrManualFollowUpReason.PARSER_WARNING_BLOCKS_RENDERING,
                    message=warning.message,
                    source_span=warning.source_span,
                )
            )
    return tuple(follow_ups)


def _item_id(sequence: int) -> str:
    return f"item-{sequence:03d}"


def _asset_summaries(item: DigiExamIrItem) -> tuple[DigiExamIrManifestAssetSummary, ...]:
    summaries: list[DigiExamIrManifestAssetSummary] = []
    for asset in item.embedded_assets:
        reference_orders = tuple(
            reference.reference_order
            for reference in item.embedded_asset_references
            if reference.asset_id == asset.asset_id
        )
        summaries.append(
            DigiExamIrManifestAssetSummary(
                item_id=item.item_id,
                asset_id=asset.asset_id,
                source_image_index=asset.source_image_index,
                sha256=asset.sha256,
                media_type=asset.media_type,
                byte_length=asset.byte_length,
                width_px=asset.width_px,
                height_px=asset.height_px,
                reference_count=len(reference_orders),
                reference_orders=reference_orders,
            )
        )
    return tuple(summaries)


_MACHINE_MARKED_ITEM_TYPES = frozenset(
    {
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
        DigiExamItemType.MATCHING,
    }
)
