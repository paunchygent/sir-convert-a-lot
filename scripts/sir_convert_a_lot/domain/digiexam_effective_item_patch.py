"""DigiExam effective item-content patch application.

Purpose:
    Apply source-bound teacher repairs to visible DigiExam item content in the
    effective renderer input while preserving parser-owned source IR.

Relationships:
    - Consumes overlay patch DTOs from `domain.digiexam_ingestion_overlay_contracts`.
    - Returns patched `DigiExamIrItem` values to `domain.digiexam_ingestion_overlay`.
    - Keeps answer-key overlays and review decisions outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamEffectiveItemPatchSummary,
    DigiExamIngestionOverlayItem,
    DigiExamOverlayChoiceItemPatch,
    DigiExamOverlayGapFillItemPatch,
    DigiExamOverlayVisibleTextPatch,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem


@dataclass(frozen=True)
class DigiExamEffectiveItemPatchRejection:
    """Semantic patch rejection after source binding has already passed."""

    reason_code: str
    message: str


@dataclass(frozen=True)
class DigiExamEffectiveItemPatchApplication:
    """Result from applying one effective item-content patch."""

    item: DigiExamIrItem
    summary: DigiExamEffectiveItemPatchSummary


@dataclass(frozen=True)
class DigiExamEffectiveItemPatchResult:
    """Accepted or rejected effective item-content patch result."""

    application: DigiExamEffectiveItemPatchApplication | None
    rejection: DigiExamEffectiveItemPatchRejection | None


def apply_effective_item_patch(
    *,
    entry: DigiExamIngestionOverlayItem,
    item: DigiExamIrItem,
) -> DigiExamEffectiveItemPatchResult:
    """Apply one source-bound visible item patch to an effective IR item."""

    patch = entry.effective_item_patch
    if patch is None:
        return DigiExamEffectiveItemPatchResult(application=None, rejection=None)
    if isinstance(patch, DigiExamOverlayChoiceItemPatch):
        return _apply_choice_patch(item=item, patch=patch)
    return _apply_gap_fill_patch(item=item, patch=patch)


def _apply_choice_patch(
    *,
    item: DigiExamIrItem,
    patch: DigiExamOverlayChoiceItemPatch,
) -> DigiExamEffectiveItemPatchResult:
    if item.item_type not in _CHOICE_ITEM_TYPES:
        return _rejected("patch_item_type_mismatch", "Choice patch on non-choice item.")
    valid_ids = {alternative.id for alternative in item.alternatives}
    requested_ids = tuple(override.alternative_id for override in patch.alternative_overrides)
    if len(set(requested_ids)) != len(requested_ids):
        return _rejected("duplicate_patch_alternative_id", "Choice patch contains duplicate IDs.")
    if any(alternative_id not in valid_ids for alternative_id in requested_ids):
        return _rejected("unknown_patch_alternative_id", "Choice patch references unknown IDs.")

    item_after_text, changed_fields = _apply_visible_text_patch(item=item, patch=patch)
    replacement_titles = {
        override.alternative_id: override.text for override in patch.alternative_overrides
    }
    alternatives = tuple(
        replace(alternative, title=replacement_titles.get(alternative.id, alternative.title))
        for alternative in item_after_text.alternatives
    )
    if alternatives != item_after_text.alternatives:
        changed_fields = (*changed_fields, "alternative_overrides")
    replacement = replace(
        item_after_text,
        alternatives=alternatives,
        options=tuple(alternative.title for alternative in alternatives),
    )
    return _accepted(
        item=item,
        replacement=replacement,
        changed_fields=changed_fields,
        patched_alternative_ids=requested_ids,
    )


def _apply_gap_fill_patch(
    *,
    item: DigiExamIrItem,
    patch: DigiExamOverlayGapFillItemPatch,
) -> DigiExamEffectiveItemPatchResult:
    if item.item_type != DigiExamItemType.GAP_FILL:
        return _rejected("patch_item_type_mismatch", "Gap-fill patch on non-gap item.")
    replacement, changed_fields = _apply_visible_text_patch(item=item, patch=patch)
    return _accepted(
        item=item,
        replacement=replacement,
        changed_fields=changed_fields,
    )


def _apply_visible_text_patch(
    *,
    item: DigiExamIrItem,
    patch: DigiExamOverlayVisibleTextPatch,
) -> tuple[DigiExamIrItem, tuple[str, ...]]:
    changed_fields: tuple[str, ...] = ()
    title = item.title
    if patch.title is not None:
        title = patch.title
        if title != item.title:
            changed_fields = (*changed_fields, "title")
    prompt_html = item.prompt_html
    if patch.prompt_html is not None:
        prompt_html = patch.prompt_html
        if prompt_html != item.prompt_html:
            changed_fields = (*changed_fields, "prompt_html")
    prompt_lines = item.prompt_lines
    if patch.prompt_lines is not None:
        prompt_lines = patch.prompt_lines
        if prompt_lines != item.prompt_lines:
            changed_fields = (*changed_fields, "prompt_lines")
    return (
        replace(
            item,
            title=title,
            prompt_html=prompt_html,
            prompt_lines=prompt_lines,
        ),
        changed_fields,
    )


def _accepted(
    *,
    item: DigiExamIrItem,
    replacement: DigiExamIrItem,
    changed_fields: tuple[str, ...],
    patched_alternative_ids: tuple[int, ...] = (),
    patched_gap_ids: tuple[str, ...] = (),
) -> DigiExamEffectiveItemPatchResult:
    if replacement == item or not changed_fields:
        return DigiExamEffectiveItemPatchResult(application=None, rejection=None)
    return DigiExamEffectiveItemPatchResult(
        application=DigiExamEffectiveItemPatchApplication(
            item=replacement,
            summary=DigiExamEffectiveItemPatchSummary(
                changed_fields=changed_fields,
                patched_alternative_ids=patched_alternative_ids,
                patched_gap_ids=patched_gap_ids,
            ),
        ),
        rejection=None,
    )


def _rejected(reason_code: str, message: str) -> DigiExamEffectiveItemPatchResult:
    return DigiExamEffectiveItemPatchResult(
        application=None,
        rejection=DigiExamEffectiveItemPatchRejection(reason_code=reason_code, message=message),
    )


_CHOICE_ITEM_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)
