"""DigiExam answer-key structured-output specs.

Purpose:
    Build JSON Schema and bounded-choice output specs for DigiExam answer-key
    completion candidate planners.

Relationships:
    - Consumed by `digiexam_answer_key_completion_candidates` for provider
      request planning.
    - Uses DigiExam IR item alternatives to derive vLLM bounded choice values.
    - Shares schema versions with the advisory answer-key report contracts.
"""

from __future__ import annotations

import itertools

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import StructuredOutputSpec


def choice_decision_output_spec() -> StructuredOutputSpec:
    """Return the provider-neutral choice decision JSON Schema spec."""

    return StructuredOutputSpec(
        schema_name=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "correct_alternative_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["correct_alternative_ids"],
        },
    )


def vllm_choice_output_spec(choice_values: tuple[str, ...]) -> StructuredOutputSpec:
    """Return the vLLM bounded-choice output spec."""

    return StructuredOutputSpec(
        schema_name=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"choice": {"type": "string", "enum": list(choice_values)}},
            "required": ["choice"],
        },
        choice_values=choice_values,
    )


def gap_fill_output_spec() -> StructuredOutputSpec:
    """Return the gap-fill decision JSON Schema spec."""

    return StructuredOutputSpec(
        schema_name=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "gap_answers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "gap_id": {"type": "string"},
                            "accepted_values": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["gap_id", "accepted_values"],
                    },
                },
            },
            "required": ["gap_answers"],
        },
    )


def numbered_gap_fill_output_spec(gap_count: int) -> StructuredOutputSpec:
    """Return a numbered gap-fill facit JSON Schema spec."""

    if gap_count <= 0:
        raise ValueError("Numbered gap-fill output spec requires at least one gap.")
    answer_keys = tuple(str(index) for index in range(1, gap_count + 1))
    properties: dict[str, JsonValue] = {key: {"type": "string"} for key in answer_keys}
    return StructuredOutputSpec(
        schema_name=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": [*answer_keys],
        },
    )


def valid_alternative_ids(item: DigiExamIrItem) -> tuple[int, ...]:
    """Return unique alternative IDs or an empty tuple when invalid."""

    ids = tuple(alternative.id for alternative in item.alternatives)
    if not ids or len(set(ids)) != len(ids):
        return ()
    return ids


def vllm_choice_values(item: DigiExamIrItem, *, max_values: int) -> tuple[str, ...]:
    """Return bounded vLLM choice values for one choice-style item."""

    alternative_ids = valid_alternative_ids(item)
    if item.item_type != DigiExamItemType.MULTIPLE_RESPONSE:
        return tuple(encode_choice_value((alternative_id,)) for alternative_id in alternative_ids)
    combinations: list[str] = []
    for size in range(1, len(alternative_ids) + 1):
        for selected_ids in itertools.combinations(alternative_ids, size):
            combinations.append(encode_choice_value(selected_ids))
            if len(combinations) > max_values:
                return ()
    return tuple(combinations)


def encode_choice_value(alternative_ids: tuple[int, ...]) -> str:
    """Encode one ordered alternative-ID tuple as a vLLM choice value."""

    return ",".join(str(alternative_id) for alternative_id in alternative_ids)


def decode_choice_value(value: str) -> tuple[int, ...]:
    """Decode a vLLM choice value into alternative IDs."""

    ids: list[int] = []
    for part in value.split(","):
        if not part.isdecimal():
            return ()
        ids.append(int(part))
    return tuple(ids)
