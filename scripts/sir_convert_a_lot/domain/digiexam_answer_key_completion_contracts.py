"""DigiExam advisory answer-key completion report contracts.

Purpose:
    Define bounded candidate-lineage report value objects for local LLM
    answer-key completion without representing model output as parser/source
    provenance.

Relationships:
    - Produced by `domain.digiexam_answer_key_completion`.
    - Serialized by `infrastructure.digiexam_answer_key_completion_runtime`.
    - Mirrors the public `answer_key_completion_report_v1` artifact contract.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
)

CHOICE_PROMPT_TEMPLATE_VERSION = "digiexam_choice_answer_key_prompt_v1"
GAP_FILL_PROMPT_TEMPLATE_VERSION = "digiexam_gap_fill_answer_key_prompt_v1"
ANSWER_KEY_COMPLETION_SAFETY_MARGIN_TOKENS = 256
ANSWER_KEY_COMPLETION_MAX_OUTPUT_TOKENS = 4096
ANSWER_KEY_COMPLETION_SYSTEM_PROMPT = (
    "You propose only structured answer-key candidates for one exam item. "
    "Return no rationale, confidence, prose, or source/provenance claims."
)


class DigiExamAnswerKeyCompletionDecisionState(StrEnum):
    """Per-item advisory decision states in completion reports."""

    SUGGESTED = "suggested"
    MANUAL_FOLLOW_UP_REQUIRED = "manual_follow_up_required"
    SKIPPED = "skipped"


class DigiExamAnswerKeyCompletionValidationState(StrEnum):
    """Backend validation states for model output or skipped items."""

    VALID = "valid"
    INVALID = "invalid"
    MANUAL_FOLLOW_UP_REQUIRED = "manual_follow_up_required"
    SKIPPED = "skipped"


class DigiExamAnswerKeyCompletionFailureCode(StrEnum):
    """Stable advisory failure/skip codes for answer-key completion reports."""

    SOURCE_BOUND_ANSWER_KEY_EXISTS = "source_bound_answer_key_exists"
    UNSUPPORTED_ITEM_TYPE = "unsupported_item_type"
    UNSUPPORTED_ASSETS = "unsupported_assets"
    UNRELIABLE_STRUCTURE = "unreliable_structure"
    MISSING_CANDIDATE_STRUCTURE = "missing_candidate_structure"
    PROVIDER_CONFIG_MISSING = "provider_config_missing"
    PROVIDER_ROUTE_BLOCKED = "provider_route_blocked"
    OVER_BUDGET = "over_budget"
    LLM_OUTPUT_INVALID = "llm_output_invalid"


@dataclass(frozen=True)
class DigiExamAnswerKeyCompletionReportItem:
    """One item-addressable advisory completion report row."""

    item_id: str
    sequence: int
    item_type: str
    decision_state: DigiExamAnswerKeyCompletionDecisionState
    validation_state: DigiExamAnswerKeyCompletionValidationState
    candidate_id: str | None
    candidate_payload_digest: str | None
    answer_payload: dict[str, JsonValue] | None
    provider_profile_id: str | None
    model_profile: str | None
    schema_name: str | None
    schema_version: str | None
    prompt_template_version: str | None
    backend_status: str
    backend_failure_code: str | None


@dataclass(frozen=True)
class DigiExamAnswerKeyCompletionReport:
    """Advisory completion report without raw prompts or provider responses."""

    schema_version: str
    job_id: str
    completion_mode: str
    items: tuple[DigiExamAnswerKeyCompletionReportItem, ...]


def completion_report(
    *,
    job_id: str,
    completion_mode: str,
    items: tuple[DigiExamAnswerKeyCompletionReportItem, ...],
) -> DigiExamAnswerKeyCompletionReport:
    """Build a versioned advisory completion report."""

    return DigiExamAnswerKeyCompletionReport(
        schema_version=ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
        job_id=job_id,
        completion_mode=completion_mode,
        items=items,
    )


def report_to_json_payload(report: DigiExamAnswerKeyCompletionReport) -> dict[str, JsonValue]:
    """Return report JSON using only bounded candidate-lineage fields."""

    return _json_value(asdict(report))


def answer_key_candidate_payload_digest(payload: dict[str, JsonValue]) -> str:
    """Return the canonical digest for a backend-validated candidate payload."""

    return f"sha256:{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _canonical_json(payload: JsonValue) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_value(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError("answer-key completion report must serialize to an object")
    return {str(key): _json_child(child) for key, child in value.items()}


def _json_child(value: object) -> JsonValue:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_child(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_child(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported answer-key completion JSON value: {type(value).__name__}")
