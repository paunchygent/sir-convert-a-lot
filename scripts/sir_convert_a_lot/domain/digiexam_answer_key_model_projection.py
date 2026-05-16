"""Model-facing DigiExam answer-key completion projections.

Purpose:
    Convert source-bound DigiExam IR items into readable, item-local payloads
    for advisory answer-key completion without changing parser provenance or
    renderer input.

Relationships:
    - Consumed by `digiexam_answer_key_completion_candidates` before provider
      request construction.
    - Keeps provider guidance and model-facing prompt projection separate from
      candidate decoding and advisory report lineage.
    - Uses DigiExam gap IDs from source HTML so gap-fill output can bind back
      to the source item contract.
"""

from __future__ import annotations

from html.parser import HTMLParser

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamItemType
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem

BASE_ANSWER_KEY_SYSTEM_PROMPT = (
    "You propose only structured answer-key candidates for one exam item. "
    "Return no rationale, confidence, prose, or source/provenance claims."
)

CHOICE_ANSWER_KEY_SYSTEM_PROMPT = (
    f"{BASE_ANSWER_KEY_SYSTEM_PROMPT} For choice items, infer the "
    "teacher-intended correct alternative id or ids from the visible item text "
    "and alternatives. If the item is ambiguous, prefer manual follow-up over "
    "a plausible wrong key."
)

GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT = (
    f"{BASE_ANSWER_KEY_SYSTEM_PROMPT} For gap-fill items, infer the "
    "teacher-intended accepted value for each visible gap marker from the "
    "surrounding cloze text and any word bank. If a gap is ambiguous, prefer "
    "manual follow-up over a plausible wrong key."
)


def system_prompt_for_answer_key_item(item_type: DigiExamItemType) -> str:
    """Return type-specific system guidance for one answer-key candidate."""

    if item_type in {
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
    }:
        return CHOICE_ANSWER_KEY_SYSTEM_PROMPT
    if item_type == DigiExamItemType.GAP_FILL:
        return GAP_FILL_ANSWER_KEY_SYSTEM_PROMPT
    return BASE_ANSWER_KEY_SYSTEM_PROMPT


def choice_answer_key_model_payload(
    item: DigiExamIrItem,
    *,
    provider_output_mode: str = "json_schema",
) -> dict[str, object]:
    """Build the model-facing payload for a choice-style DigiExam item."""

    alternative_ids = tuple(alternative.id for alternative in item.alternatives)
    maximum_answers = (
        len(alternative_ids) if item.item_type == DigiExamItemType.MULTIPLE_RESPONSE else 1
    )
    return {
        "task": {
            "name": "select_teacher_intended_choice_answer_key",
            "item_type": item.item_type.value,
            "instruction": _choice_user_instruction(item.item_type),
        },
        "item": {
            "item_id": item.item_id,
            "title": item.title,
            "stem": _prompt_text(item),
        },
        "choices": [
            {
                "choice_value": str(alternative.id),
                "alternative_id": alternative.id,
                "text": alternative.title,
            }
            for alternative in item.alternatives
        ],
        "selection_rules": {"min_choices": 1, "max_choices": maximum_answers},
        "output": {
            "provider_output_mode": provider_output_mode,
            "answer_shape": _choice_answer_shape(provider_output_mode),
        },
    }


def gap_fill_answer_key_model_payload(
    item: DigiExamIrItem,
    *,
    provider_output_mode: str = "json_schema",
) -> dict[str, object]:
    """Build the model-facing payload for a gap-fill DigiExam item."""

    gap_entries = [{"gap_number": index} for index, _gap in enumerate(item.gaps, start=1)]
    return {
        "task": {
            "name": "complete_teacher_intended_gap_fill_answer_key",
            "item_type": item.item_type.value,
            "instruction": (
                "Read the cloze item as a teacher-authored exam question. "
                "Each [number] marker is one blank. Choose the "
                "teacher-intended accepted value for every numbered blank."
            ),
        },
        "item": {
            "item_id": item.item_id,
            "title": item.title,
            "cloze_text": _numbered_gap_prompt_text(item),
        },
        "gaps": gap_entries,
        "output": {
            "provider_output_mode": provider_output_mode,
            "json_shape": (
                'Return one JSON object. Use string keys "1" through '
                f'"{len(gap_entries)}" for the numbered blanks, and set '
                "manual_follow_up_code to null when all blanks are answered."
            ),
            "accepted_values": (
                "Each numbered key value must be exactly one short answer "
                "string. Preserve word-bank spelling when a word bank is visible."
            ),
        },
    }


def _choice_user_instruction(item_type: DigiExamItemType) -> str:
    if item_type == DigiExamItemType.MULTIPLE_RESPONSE:
        return (
            "Read the item as a teacher-authored exam question. Select all "
            "teacher-intended correct choices from the listed choices. Use "
            "only the provided choice_value values."
        )
    return (
        "Read the item as a teacher-authored exam question. Select exactly one "
        "teacher-intended correct choice from the listed choices. Use only the "
        "provided choice_value values."
    )


def _choice_answer_shape(provider_output_mode: str) -> str:
    if provider_output_mode == "vllm_structured_choice":
        return (
            "The provider will force one bounded choice_value. For "
            "multiple-response items, a choice_value may contain "
            "comma-separated alternative ids in ascending order."
        )
    return (
        "Return a JSON object with decision_state, correct_alternative_ids, "
        "and manual_follow_up_code. Use only the listed alternative_id values."
    )


def _prompt_text(item: DigiExamIrItem) -> str:
    lines = tuple(line.strip() for line in item.prompt_lines if line.strip())
    if lines:
        return "\n".join(lines)
    if item.prompt_html:
        return _html_text(item.prompt_html)
    return item.title


def _gap_prompt_text(item: DigiExamIrItem) -> str:
    if item.prompt_html:
        return _html_text_with_gap_markers(item.prompt_html)
    return _prompt_text(item)


def _numbered_gap_prompt_text(item: DigiExamIrItem) -> str:
    if item.prompt_html:
        gap_numbers = {gap.guid: index for index, gap in enumerate(item.gaps, start=1)}
        return _html_text_with_gap_markers(item.prompt_html, gap_numbers=gap_numbers)
    return _prompt_text(item)


def _html_text(html: str) -> str:
    parser = _TextProjectionParser()
    parser.feed(html)
    return parser.text()


def _html_text_with_gap_markers(html: str, *, gap_numbers: dict[str, int] | None = None) -> str:
    parser = _TextProjectionParser(gap_numbers=gap_numbers)
    parser.feed(html)
    return parser.text()


class _TextProjectionParser(HTMLParser):
    """Extract readable text while preserving DigiExam gap bindings."""

    _BLOCK_TAGS = frozenset({"br", "div", "li", "ol", "p", "tr", "ul"})

    def __init__(self, *, gap_numbers: dict[str, int] | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._gap_numbers = gap_numbers

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value for name, value in attrs if value is not None}
        gap_id = attributes.get("dx-wg-id")
        if tag == "span" and gap_id is not None and gap_id.strip():
            if self._gap_numbers is None:
                self._chunks.append(f" [[gap:{gap_id.strip()}]] ")
            else:
                gap_number = self._gap_numbers.get(gap_id.strip())
                if gap_number is not None:
                    self._chunks.append(f" [{gap_number}] ")
            return
        if tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks).replace("\xa0", " ")
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        text = "\n".join(line for line in lines if line)
        return _remove_space_before_punctuation(text)


def _remove_space_before_punctuation(text: str) -> str:
    result = text
    for mark in (".", ",", ":", ";", "?", "!"):
        result = result.replace(f" {mark}", mark)
    return result
