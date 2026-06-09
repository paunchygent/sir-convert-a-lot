"""DigiExam answer-key live-validation corpus coverage proof.

Purpose:
    Compare answer-key live validation validation manifest items with retained advisory report
    rows so live-validation evidence can prove which corpus items were
    exercised.

Relationships:
    - Consumes manifest keys loaded by `digiexam_answer_key_live_evaluation`.
    - Produces a JSON-safe coverage proof embedded in advisory evaluation
      reports and Markdown closeout.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AnswerKeyCoverageItemRef:
    """One manifest or report item key in the coverage proof."""

    source_filename: str
    item_id: str
    eligible: bool | None
    skip_reason: str | None


@dataclass(frozen=True)
class AnswerKeyCorpusCoverageProof:
    """Manifest-vs-report coverage proof for one live-validation run."""

    manifest_item_count: int
    manifest_eligible_item_count: int
    manifest_ineligible_item_count: int
    report_unique_item_count: int
    reported_manifest_item_count: int
    all_manifest_items_reported: bool
    all_eligible_items_reported: bool
    missing_manifest_item_count: int
    missing_eligible_item_count: int
    unexpected_report_item_count: int
    missing_manifest_items: tuple[AnswerKeyCoverageItemRef, ...]
    missing_eligible_items: tuple[AnswerKeyCoverageItemRef, ...]
    unexpected_report_items: tuple[AnswerKeyCoverageItemRef, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON-safe coverage proof."""

        payload = asdict(self)
        return {key: value for key, value in payload.items()}


def build_answer_key_corpus_coverage_proof(
    *,
    manifest_items: Mapping[tuple[str, str], Mapping[str, object]],
    report_keys: set[tuple[str, str]],
) -> AnswerKeyCorpusCoverageProof:
    """Build a coverage proof comparing manifest items to report rows."""

    manifest_keys = set(manifest_items)
    eligible_keys = {
        key for key, item in manifest_items.items() if _optional_bool(item, "eligible") is True
    }
    missing_manifest_keys = manifest_keys - report_keys
    missing_eligible_keys = eligible_keys - report_keys
    unexpected_report_keys = report_keys - manifest_keys
    reported_manifest_keys = manifest_keys & report_keys
    return AnswerKeyCorpusCoverageProof(
        manifest_item_count=len(manifest_keys),
        manifest_eligible_item_count=len(eligible_keys),
        manifest_ineligible_item_count=len(manifest_keys - eligible_keys),
        report_unique_item_count=len(report_keys),
        reported_manifest_item_count=len(reported_manifest_keys),
        all_manifest_items_reported=not missing_manifest_keys,
        all_eligible_items_reported=not missing_eligible_keys,
        missing_manifest_item_count=len(missing_manifest_keys),
        missing_eligible_item_count=len(missing_eligible_keys),
        unexpected_report_item_count=len(unexpected_report_keys),
        missing_manifest_items=_refs_for_manifest_keys(
            keys=missing_manifest_keys,
            manifest_items=manifest_items,
        ),
        missing_eligible_items=_refs_for_manifest_keys(
            keys=missing_eligible_keys,
            manifest_items=manifest_items,
        ),
        unexpected_report_items=_refs_for_unexpected_keys(unexpected_report_keys),
    )


def _refs_for_manifest_keys(
    *,
    keys: set[tuple[str, str]],
    manifest_items: Mapping[tuple[str, str], Mapping[str, object]],
) -> tuple[AnswerKeyCoverageItemRef, ...]:
    return tuple(
        AnswerKeyCoverageItemRef(
            source_filename=source_filename,
            item_id=item_id,
            eligible=_optional_bool(manifest_items[(source_filename, item_id)], "eligible"),
            skip_reason=_optional_str(manifest_items[(source_filename, item_id)], "skip_reason"),
        )
        for source_filename, item_id in sorted(keys)
    )


def _refs_for_unexpected_keys(
    keys: set[tuple[str, str]],
) -> tuple[AnswerKeyCoverageItemRef, ...]:
    return tuple(
        AnswerKeyCoverageItemRef(
            source_filename=source_filename,
            item_id=item_id,
            eligible=None,
            skip_reason=None,
        )
        for source_filename, item_id in sorted(keys)
    )


def _optional_bool(payload: Mapping[str, object], key: str) -> bool | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    return None


def _optional_str(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str):
        return value
    return None
