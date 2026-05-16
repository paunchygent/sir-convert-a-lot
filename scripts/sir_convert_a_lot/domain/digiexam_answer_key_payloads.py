"""DigiExam answer-key candidate payload validation.

Purpose:
    Provide one shared validation and canonicalization boundary for advisory
    answer-key candidates and reviewed effective-IR application.

Relationships:
    - Consumed by `domain.digiexam_answer_key_completion` for Task 297 reports.
    - Consumed by `domain.digiexam_ingestion_overlay` for Task 306 reviewed
      application.
    - Keeps item-local answer payload semantics separate from provider
      transport, overlay parsing, and target renderers.
"""

from __future__ import annotations

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem


def answer_payload_from_model_content(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    """Return a validated candidate payload from one provider decision object."""

    decision_state = _string(content.get("decision_state"))
    manual_code = _string(content.get("manual_follow_up_code"))
    if decision_state != "answered" or manual_code is not None:
        return None
    if item.item_type in _CHOICE_ITEM_TYPES:
        return _validated_choice_payload(item=item, content=content)
    if item.item_type == DigiExamItemType.GAP_FILL:
        return _validated_gap_payload(item=item, content=content)
    return None


def validated_reviewed_answer_payload(
    *,
    item: DigiExamIrItem,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    """Return a validated candidate payload from reviewed overlay data."""

    kind = _string(payload.get("kind"))
    if kind == "choice" and item.item_type in _CHOICE_ITEM_TYPES:
        return _validated_choice_payload(item=item, content=payload)
    if kind == "gap_fill" and item.item_type == DigiExamItemType.GAP_FILL:
        return _validated_gap_payload(item=item, content=payload)
    return None


def _validated_choice_payload(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    ids = _int_tuple(content.get("correct_alternative_ids"))
    if not ids or len(set(ids)) != len(ids):
        return None
    valid_ids = {alternative.id for alternative in item.alternatives}
    if any(alternative_id not in valid_ids for alternative_id in ids):
        return None
    if item.item_type != DigiExamItemType.MULTIPLE_RESPONSE and len(ids) != 1:
        return None
    return {"kind": "choice", "correct_alternative_ids": list(ids)}


def _validated_gap_payload(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    numbered_payload = _validated_numbered_gap_payload(item=item, content=content)
    if numbered_payload is not None:
        return numbered_payload
    raw_gap_answers = content.get("gap_answers")
    if not isinstance(raw_gap_answers, list) or not raw_gap_answers:
        return None
    valid_gap_ids = {gap.guid for gap in item.gaps}
    seen_gap_ids: set[str] = set()
    gap_answers: list[JsonValue] = []
    for raw_answer in raw_gap_answers:
        if not isinstance(raw_answer, dict):
            return None
        gap_id = _string(raw_answer.get("gap_id"))
        accepted_values = _string_tuple(raw_answer.get("accepted_values"))
        if gap_id is None or gap_id not in valid_gap_ids or gap_id in seen_gap_ids:
            return None
        normalized_values = tuple(value.strip() for value in accepted_values)
        if not normalized_values or any(not value for value in normalized_values):
            return None
        if len(set(normalized_values)) != len(normalized_values):
            return None
        seen_gap_ids.add(gap_id)
        gap_answers.append({"gap_id": gap_id, "accepted_values": list(normalized_values)})
    if seen_gap_ids != valid_gap_ids:
        return None
    return {"kind": "gap_fill", "gap_answers": gap_answers}


def _validated_numbered_gap_payload(
    *,
    item: DigiExamIrItem,
    content: dict[str, JsonValue],
) -> dict[str, JsonValue] | None:
    if _string(content.get("manual_follow_up_code")) is not None:
        return None
    gap_answers: list[JsonValue] = []
    for index, gap in enumerate(item.gaps, start=1):
        value = _string(content.get(str(index)))
        if value is None:
            return None
        gap_answers.append({"gap_id": gap.guid, "accepted_values": [value.strip()]})
    if len(gap_answers) != len(item.gaps):
        return None
    return {"kind": "gap_fill", "gap_answers": gap_answers}


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        return ()
    integers: list[int] = []
    for entry in value:
        if not isinstance(entry, int) or isinstance(entry, bool):
            return ()
        integers.append(entry)
    return tuple(integers)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    strings: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            return ()
        strings.append(entry)
    return tuple(strings)


_CHOICE_ITEM_TYPES = frozenset(
    {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }
)
