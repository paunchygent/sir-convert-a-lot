"""DigiExam answer-key live-validation corpus manifests.

Purpose:
    Build item-addressable manifests for the answer-key live validation answer-key live-validation
    corpus so Hemma runs can bind every provider decision to a source file,
    source hash, item fingerprint, eligibility state, and golden-answer worklist
    without persisting prompts or provider responses.

Relationships:
    - Consumes `domain.digiexam_dxe_parser` and `domain.digiexam_ir_contracts`
      as the canonical DigiExam source and IR boundaries.
    - Uses `domain.digiexam_source_fingerprints` for answer-key independent
      item binding shared with overlay and readiness contracts.
    - Feeds answer-key live validation devops runners and report evaluators.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIrItem,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.digiexam_source_fingerprints import (
    source_item_fingerprint,
)

ANSWER_KEY_LIVE_VALIDATION_CORPUS_MANIFEST_SCHEMA_VERSION = (
    "digiexam_answer_key_live_validation_corpus_v1"
)
ANSWER_KEY_EXPECTED_ANSWER_WORKLIST_SCHEMA_VERSION = (
    "digiexam_answer_key_live_validation_expected_answer_worklist_v1"
)
ANSWER_KEY_LIVE_VALIDATION_CORPUS_ID = "digiexam-answer-key-2026-05-12-onedrive-pure-dxe"
ANSWER_KEY_LIVE_VALIDATION_FIXTURE_POLICY = "tracked_raw_dxe_fixture"


class AnswerKeyOutputMode(StrEnum):
    """Provider output modes selected for answer-key live validation manifest rows."""

    VLLM_CHOICE = "vllm_choice"
    JSON_SCHEMA = "json_schema"
    NOT_APPLICABLE = "not_applicable"


class AnswerKeySkipReason(StrEnum):
    """Stable answer-key live validation manifest skip reasons."""

    NONE = "none"
    SOURCE_BOUND_ANSWER_KEY_EXISTS = "source_bound_answer_key_exists"
    UNSUPPORTED_ITEM_TYPE = "unsupported_item_type"
    UNSUPPORTED_ASSETS = "unsupported_assets"
    UNRELIABLE_STRUCTURE = "unreliable_structure"
    MISSING_CANDIDATE_STRUCTURE = "missing_candidate_structure"


@dataclass(frozen=True)
class AnswerKeyCount:
    """One deterministic manifest count."""

    key: str
    count: int


@dataclass(frozen=True)
class AnswerKeyAssetEvalPolicy:
    """Eval-only embedded-asset eligibility policy for answer-key live validation."""

    allow_supported_embedded_assets: bool = False


@dataclass(frozen=True)
class AnswerKeyLiveValidationItem:
    """One item-addressable answer-key live validation validation manifest row."""

    source_filename: str
    source_sha256: str
    item_id: str
    sequence: int
    source_item_fingerprint: str
    item_type: str
    answer_key_provenance: str
    eligible: bool
    skip_reason: str
    output_mode: str
    warning_codes: tuple[str, ...]
    has_blocking_warning: bool
    embedded_asset_count: int
    candidate_count: int


@dataclass(frozen=True)
class AnswerKeyLiveValidationFile:
    """One source-file row in the answer-key live validation validation corpus manifest."""

    filename: str
    source_sha256: str
    byte_size: int
    parse_status: str
    renderer_ready: bool
    item_count: int
    items: tuple[AnswerKeyLiveValidationItem, ...]


@dataclass(frozen=True)
class AnswerKeyLiveValidationSummary:
    """Aggregate answer-key live validation validation corpus manifest summary."""

    file_count: int
    item_count: int
    eligible_item_count: int
    item_type_counts: tuple[AnswerKeyCount, ...]
    output_mode_counts: tuple[AnswerKeyCount, ...]
    skip_reason_counts: tuple[AnswerKeyCount, ...]
    answer_key_provenance_counts: tuple[AnswerKeyCount, ...]


@dataclass(frozen=True)
class AnswerKeyLiveValidationManifest:
    """answer-key live validation validation corpus manifest safe to commit."""

    schema_version: str
    corpus_id: str
    source_root_hint: str
    fixture_policy: str
    files: tuple[AnswerKeyLiveValidationFile, ...]
    summary: AnswerKeyLiveValidationSummary

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload without raw exam content."""

        return _json_object(asdict(self))


@dataclass(frozen=True)
class AnswerKeyExpectedAnswerWorklistItem:
    """One eligible item needing a teacher-verified expected answer."""

    source_filename: str
    source_sha256: str
    item_id: str
    sequence: int
    source_item_fingerprint: str
    item_type: str
    output_mode: str
    expected_answer_state: str
    adjudication_required: bool


@dataclass(frozen=True)
class AnswerKeyExpectedAnswerWorklist:
    """answer-key live validation golden-answer worklist before teacher verification is complete."""

    schema_version: str
    corpus_id: str
    items: tuple[AnswerKeyExpectedAnswerWorklistItem, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the expected-answer worklist."""

        return _json_object(asdict(self))


def build_answer_key_live_validation_manifest(
    corpus_root: Path,
    *,
    source_root_hint: str | None = None,
    asset_eval_policy: AnswerKeyAssetEvalPolicy = AnswerKeyAssetEvalPolicy(),
) -> AnswerKeyLiveValidationManifest:
    """Build the answer-key live validation corpus manifest from a versioned `.dxe` fixture root."""

    if not corpus_root.is_dir():
        raise ValueError(f"answer-key live validation corpus root does not exist: {corpus_root}")
    files = tuple(sorted(corpus_root.glob("*.dxe")))
    if not files:
        raise ValueError(
            f"answer-key live validation corpus contains no `.dxe` files: {corpus_root}"
        )

    parser = DigiExamDxeParser()
    manifest_files = tuple(
        _build_file(path, parser=parser, asset_eval_policy=asset_eval_policy) for path in files
    )
    return AnswerKeyLiveValidationManifest(
        schema_version=ANSWER_KEY_LIVE_VALIDATION_CORPUS_MANIFEST_SCHEMA_VERSION,
        corpus_id=ANSWER_KEY_LIVE_VALIDATION_CORPUS_ID,
        source_root_hint=source_root_hint
        if source_root_hint is not None
        else corpus_root.as_posix(),
        fixture_policy=ANSWER_KEY_LIVE_VALIDATION_FIXTURE_POLICY,
        files=manifest_files,
        summary=_build_summary(manifest_files),
    )


def build_answer_key_expected_answer_worklist(
    manifest: AnswerKeyLiveValidationManifest,
) -> AnswerKeyExpectedAnswerWorklist:
    """Build the eligible-item expected-answer worklist for answer-key live validation."""

    items = tuple(
        AnswerKeyExpectedAnswerWorklistItem(
            source_filename=item.source_filename,
            source_sha256=item.source_sha256,
            item_id=item.item_id,
            sequence=item.sequence,
            source_item_fingerprint=item.source_item_fingerprint,
            item_type=item.item_type,
            output_mode=item.output_mode,
            expected_answer_state="pending_teacher_verified_golden",
            adjudication_required=False,
        )
        for file_entry in manifest.files
        for item in file_entry.items
        if item.eligible
    )
    return AnswerKeyExpectedAnswerWorklist(
        schema_version=ANSWER_KEY_EXPECTED_ANSWER_WORKLIST_SCHEMA_VERSION,
        corpus_id=manifest.corpus_id,
        items=items,
    )


def write_answer_key_json(payload: dict[str, object], output_path: Path) -> None:
    """Write one deterministic answer-key live validation JSON artifact."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_file(
    path: Path,
    *,
    parser: DigiExamDxeParser,
    asset_eval_policy: AnswerKeyAssetEvalPolicy,
) -> AnswerKeyLiveValidationFile:
    source_sha256 = _source_sha256(path)
    parse_result = parser.parse_file(path)
    exam = build_digiexam_intermediate_exam(parse_result)
    items = tuple(
        _build_item(path.name, source_sha256, item, asset_eval_policy=asset_eval_policy)
        for item in exam.items
    )
    return AnswerKeyLiveValidationFile(
        filename=path.name,
        source_sha256=source_sha256,
        byte_size=path.stat().st_size,
        parse_status=exam.parse_status.value,
        renderer_ready=exam.renderer_ready,
        item_count=len(exam.items),
        items=items,
    )


def _build_item(
    source_filename: str,
    source_sha256: str,
    item: DigiExamIrItem,
    *,
    asset_eval_policy: AnswerKeyAssetEvalPolicy,
) -> AnswerKeyLiveValidationItem:
    skip_reason = _skip_reason(item, asset_eval_policy=asset_eval_policy)
    output_mode = _output_mode(item, skip_reason)
    return AnswerKeyLiveValidationItem(
        source_filename=source_filename,
        source_sha256=source_sha256,
        item_id=item.item_id,
        sequence=item.sequence,
        source_item_fingerprint=source_item_fingerprint(item),
        item_type=item.item_type.value,
        answer_key_provenance=item.answer_key.provenance.value,
        eligible=skip_reason == AnswerKeySkipReason.NONE,
        skip_reason=skip_reason.value,
        output_mode=output_mode.value,
        warning_codes=tuple(sorted(warning.code.value for warning in item.warnings)),
        has_blocking_warning=any(warning.blocking for warning in item.warnings),
        embedded_asset_count=len(item.embedded_assets),
        candidate_count=_candidate_count(item),
    )


def _skip_reason(
    item: DigiExamIrItem,
    *,
    asset_eval_policy: AnswerKeyAssetEvalPolicy,
) -> AnswerKeySkipReason:
    if item.item_type not in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    }:
        return AnswerKeySkipReason.UNSUPPORTED_ITEM_TYPE
    if item.answer_key.provenance not in {
        DigiExamAnswerKeyProvenance.ABSENT,
        DigiExamAnswerKeyProvenance.NOT_APPLICABLE,
    }:
        return AnswerKeySkipReason.SOURCE_BOUND_ANSWER_KEY_EXISTS
    if any(warning.blocking for warning in item.warnings):
        return AnswerKeySkipReason.UNRELIABLE_STRUCTURE
    if item.embedded_assets or item.embedded_asset_references:
        if asset_eval_policy.allow_supported_embedded_assets and _supported_asset_item(item):
            pass
        else:
            return AnswerKeySkipReason.UNSUPPORTED_ASSETS
    if item.item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        alternative_ids = tuple(alternative.id for alternative in item.alternatives)
        if not alternative_ids or len(set(alternative_ids)) != len(alternative_ids):
            return AnswerKeySkipReason.MISSING_CANDIDATE_STRUCTURE
        return AnswerKeySkipReason.NONE
    if item.item_type == DigiExamItemType.GAP_FILL:
        if not item.gaps or any(not gap.guid.strip() for gap in item.gaps):
            return AnswerKeySkipReason.MISSING_CANDIDATE_STRUCTURE
        return AnswerKeySkipReason.NONE
    return AnswerKeySkipReason.UNSUPPORTED_ITEM_TYPE


def _supported_asset_item(item: DigiExamIrItem) -> bool:
    if not item.embedded_assets or not item.embedded_asset_references:
        return False
    supported_media = {"image/png", "image/jpeg"}
    asset_ids = {asset.asset_id for asset in item.embedded_assets}
    reference_asset_ids = {reference.asset_id for reference in item.embedded_asset_references}
    return asset_ids == reference_asset_ids and all(
        asset.media_type in supported_media and asset.content_base64
        for asset in item.embedded_assets
    )


def _output_mode(item: DigiExamIrItem, skip_reason: AnswerKeySkipReason) -> AnswerKeyOutputMode:
    if skip_reason != AnswerKeySkipReason.NONE:
        return AnswerKeyOutputMode.NOT_APPLICABLE
    if item.item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        return AnswerKeyOutputMode.VLLM_CHOICE
    return AnswerKeyOutputMode.JSON_SCHEMA


def _candidate_count(item: DigiExamIrItem) -> int:
    if item.item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        return len(item.alternatives)
    if item.item_type == DigiExamItemType.GAP_FILL:
        return len(item.gaps)
    return 0


def _build_summary(
    files: tuple[AnswerKeyLiveValidationFile, ...],
) -> AnswerKeyLiveValidationSummary:
    items = tuple(item for file_entry in files for item in file_entry.items)
    return AnswerKeyLiveValidationSummary(
        file_count=len(files),
        item_count=len(items),
        eligible_item_count=sum(1 for item in items if item.eligible),
        item_type_counts=_count_values(item.item_type for item in items),
        output_mode_counts=_count_values(item.output_mode for item in items),
        skip_reason_counts=_count_values(item.skip_reason for item in items),
        answer_key_provenance_counts=_count_values(item.answer_key_provenance for item in items),
    )


def _source_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _count_values(values: Iterable[str]) -> tuple[AnswerKeyCount, ...]:
    counter = Counter(values)
    return tuple(AnswerKeyCount(key=key, count=counter[key]) for key in sorted(counter))


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("answer-key live validation manifest must serialize to a JSON object.")
    return {str(key): _json_value(child) for key, child in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(
        f"Unsupported answer-key live validation manifest JSON value: {type(value).__name__}"
    )
