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

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamItemType,
    DigiExamMatchingStructure,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamEffectiveItemPatchSummary,
    DigiExamIngestionOverlayItem,
    DigiExamOverlayChoiceItemPatch,
    DigiExamOverlayGapFillItemPatch,
    DigiExamOverlayMatchingItemPatch,
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
    if isinstance(patch, DigiExamOverlayGapFillItemPatch):
        return _apply_gap_fill_patch(item=item, patch=patch)
    return _apply_matching_patch(item=item, patch=patch)


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


def _apply_matching_patch(
    *,
    item: DigiExamIrItem,
    patch: DigiExamOverlayMatchingItemPatch,
) -> DigiExamEffectiveItemPatchResult:
    if item.item_type != DigiExamItemType.MATCHING or item.matching is None:
        return _rejected("patch_item_type_mismatch", "Matching patch on non-matching item.")
    left_indices = tuple(override.index for override in patch.left_overrides)
    right_indices = tuple(override.index for override in patch.right_overrides)
    if len(set(left_indices)) != len(left_indices):
        return _rejected("duplicate_patch_left_index", "Matching patch duplicates left indices.")
    if len(set(right_indices)) != len(right_indices):
        return _rejected("duplicate_patch_right_index", "Matching patch duplicates right indices.")
    if any(index > len(item.matching.left_prompts) for index in left_indices):
        return _rejected(
            "unknown_patch_left_index", "Matching patch references unknown left items."
        )
    if any(index > len(item.matching.right_options) for index in right_indices):
        return _rejected(
            "unknown_patch_right_index", "Matching patch references unknown right items."
        )

    item_after_text, changed_fields = _apply_visible_text_patch(item=item, patch=patch)
    matching = item_after_text.matching
    if matching is None:
        return _rejected(
            "patch_item_type_mismatch", "Matching patch on missing matching structure."
        )
    left_prompts = _replace_by_one_based_index(
        values=matching.left_prompts,
        replacements={override.index: override.text for override in patch.left_overrides},
    )
    right_options = _replace_by_one_based_index(
        values=matching.right_options,
        replacements={override.index: override.text for override in patch.right_overrides},
    )
    if left_prompts != matching.left_prompts:
        changed_fields = (*changed_fields, "matching_left_overrides")
    if right_options != matching.right_options:
        changed_fields = (*changed_fields, "matching_right_overrides")
    replacement = replace(
        item_after_text,
        matching=DigiExamMatchingStructure(
            left_prompts=left_prompts,
            right_options=right_options,
            blank_row_evidence=matching.blank_row_evidence,
        ),
    )
    return _accepted(
        item=item,
        replacement=replacement,
        changed_fields=changed_fields,
        patched_matching_left_indices=left_indices,
        patched_matching_right_indices=right_indices,
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


def _replace_by_one_based_index(
    *,
    values: tuple[str, ...],
    replacements: dict[int, str],
) -> tuple[str, ...]:
    return tuple(replacements.get(index, value) for index, value in enumerate(values, start=1))


def _accepted(
    *,
    item: DigiExamIrItem,
    replacement: DigiExamIrItem,
    changed_fields: tuple[str, ...],
    patched_alternative_ids: tuple[int, ...] = (),
    patched_gap_ids: tuple[str, ...] = (),
    patched_matching_left_indices: tuple[int, ...] = (),
    patched_matching_right_indices: tuple[int, ...] = (),
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
                patched_matching_left_indices=patched_matching_left_indices,
                patched_matching_right_indices=patched_matching_right_indices,
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
