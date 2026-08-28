"""QTI 2.1 item XML serialization for Exam.net-oriented packages.

Purpose:
    Serialize governed Exam.net QTI items to assessmentItem XML without file
    system or service-route concerns.

Relationships:
    - Consumes `domain.examnet_qti_contracts` item value objects.
    - Used by QTI package planning before deterministic zip materialization and
      validation-report assembly.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from xml.etree import ElementTree

from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchPair,
    ExamNetQtiTextEntryGap,
)

QTI_NAMESPACE = "http://www.imsglobal.org/xsd/imsqti_v2p1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
QTI_SCHEMA_LOCATION = (
    "http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
)
MAP_RESPONSE_TEMPLATE = "http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"
FREE_TEXT_CRITERION_MAP_KEY = "CRITERION_FULL"
_GAP_MARKER_PATTERN = re.compile(r"(?:\[_+\]|_{3,})")


def serialize_qti_assessment_item(
    item: ExamNetQtiItem,
    *,
    image_paths: tuple[str, ...] = (),
) -> bytes:
    """Serialize one governed QTI item to UTF-8 XML bytes."""

    ElementTree.register_namespace("", QTI_NAMESPACE)
    ElementTree.register_namespace("xsi", XSI_NAMESPACE)
    root = ElementTree.Element(
        _qti("assessmentItem"),
        {
            "identifier": item.item_id,
            "title": item.title,
            "adaptive": "false",
            "timeDependent": "false",
            _xsi("schemaLocation"): QTI_SCHEMA_LOCATION,
        },
    )
    _append_response_declaration(root, item)
    _append_score_outcome(root, item)
    item_body = ElementTree.SubElement(root, _qti("itemBody"))
    if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
        _append_gap_fill_body(item_body, item)
        _append_images(item_body, item.image_resources, image_paths)
    else:
        _append_prompt(item_body, item.prompt_lines)
        _append_images(item_body, item.image_resources, image_paths)
        _append_interaction(item_body, item)
    if _emits_map_response(item):
        ElementTree.SubElement(
            root,
            _qti("responseProcessing"),
            {"template": MAP_RESPONSE_TEMPLATE},
        )

    ElementTree.indent(root, space="  ")
    xml_text = ElementTree.tostring(
        root,
        encoding="unicode",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_text}\n'.encode("utf-8")


def _append_response_declaration(
    root: ElementTree.Element,
    item: ExamNetQtiItem,
) -> None:
    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        declaration = ElementTree.SubElement(
            root,
            _qti("responseDeclaration"),
            {
                "identifier": "RESPONSE",
                "cardinality": "single",
                "baseType": "string",
            },
        )
        if item.free_text_criterion_points is not None:
            points = str(item.free_text_criterion_points)
            mapping = ElementTree.SubElement(
                declaration,
                _qti("mapping"),
                {"defaultValue": "0", "lowerBound": "0", "upperBound": points},
            )
            ElementTree.SubElement(
                mapping,
                _qti("mapEntry"),
                {"mapKey": FREE_TEXT_CRITERION_MAP_KEY, "mappedValue": points},
            )
        return

    if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
        gap_point_values = _gap_point_values(item)
        for index, gap in enumerate(item.text_entry_gaps):
            gap_points = None if gap_point_values is None else gap_point_values[index]
            _append_gap_response_declaration(root, gap, gap_points)
        return

    cardinality = "multiple"
    base_type = "identifier"
    values: tuple[str, ...]
    if item.interaction_type == ExamNetQtiInteractionType.SINGLE_CHOICE:
        cardinality = "single"
        values = item.correct_choice_identifiers
    elif item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
        values = item.correct_choice_identifiers
    else:
        base_type = "directedPair"
        values = tuple(
            f"{pair.left_identifier} {pair.right_identifier}" for pair in item.match_pairs
        )

    declaration = ElementTree.SubElement(
        root,
        _qti("responseDeclaration"),
        {
            "identifier": "RESPONSE",
            "cardinality": cardinality,
            "baseType": base_type,
        },
    )
    if values:
        correct_response = ElementTree.SubElement(declaration, _qti("correctResponse"))
        for value in values:
            value_element = ElementTree.SubElement(correct_response, _qti("value"))
            value_element.text = value
    if (
        values
        and item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC
        and item.max_score is not None
    ):
        mapped_values = _split_point_values(item.max_score, len(values))
        mapping = ElementTree.SubElement(
            declaration,
            _qti("mapping"),
            {"defaultValue": "0", "lowerBound": "0", "upperBound": str(item.max_score)},
        )
        for value, mapped_value in zip(values, mapped_values, strict=True):
            ElementTree.SubElement(
                mapping,
                _qti("mapEntry"),
                {"mapKey": value, "mappedValue": mapped_value},
            )


def _append_gap_response_declaration(
    root: ElementTree.Element,
    gap: ExamNetQtiTextEntryGap,
    gap_points: str | None,
) -> None:
    values = tuple(value.strip() for value in gap.accepted_values if value.strip())
    declaration = ElementTree.SubElement(
        root,
        _qti("responseDeclaration"),
        {
            "identifier": gap.response_identifier,
            "cardinality": "single",
            "baseType": "string",
        },
    )
    if not values:
        return
    correct_response = ElementTree.SubElement(declaration, _qti("correctResponse"))
    value_element = ElementTree.SubElement(correct_response, _qti("value"))
    value_element.text = values[0]
    if gap_points is None:
        return
    mapping = ElementTree.SubElement(
        declaration,
        _qti("mapping"),
        {"defaultValue": "0", "lowerBound": "0", "upperBound": gap_points},
    )
    for value in values:
        ElementTree.SubElement(
            mapping,
            _qti("mapEntry"),
            {"mapKey": value, "mappedValue": gap_points, "caseSensitive": "false"},
        )


def _gap_point_values(item: ExamNetQtiItem) -> tuple[str, ...] | None:
    if item.max_score is None or not item.text_entry_gaps:
        return None
    return _split_point_values(item.max_score, len(item.text_entry_gaps))


def _split_point_values(total: int, count: int) -> tuple[str, ...]:
    cents_total = total * 100
    base_cents = cents_total // count
    extra_cents = cents_total - base_cents * count
    return tuple(
        _format_cents(base_cents + (1 if index < extra_cents else 0)) for index in range(count)
    )


def _format_cents(cents: int) -> str:
    whole, rest = divmod(cents, 100)
    if rest == 0:
        return str(whole)
    return f"{whole}.{rest:02d}".rstrip("0")


def _emits_map_response(item: ExamNetQtiItem) -> bool:
    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        return item.free_text_criterion_points is not None
    if item.interaction_type == ExamNetQtiInteractionType.GAP_FILL:
        return False
    return item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC


def _append_score_outcome(root: ElementTree.Element, item: ExamNetQtiItem) -> None:
    outcome = ElementTree.SubElement(
        root,
        _qti("outcomeDeclaration"),
        {
            "identifier": "SCORE",
            "cardinality": "single",
            "baseType": "float",
        },
    )
    default_value = ElementTree.SubElement(outcome, _qti("defaultValue"))
    value = ElementTree.SubElement(default_value, _qti("value"))
    value.text = "0"
    max_score = ElementTree.SubElement(
        root,
        _qti("outcomeDeclaration"),
        {
            "identifier": "MAXSCORE",
            "cardinality": "single",
            "baseType": "float",
        },
    )
    max_default = ElementTree.SubElement(max_score, _qti("defaultValue"))
    max_value = ElementTree.SubElement(max_default, _qti("value"))
    max_value.text = str(item.max_score or 0)


def _append_prompt(parent: ElementTree.Element, prompt_lines: tuple[str, ...]) -> None:
    for line in prompt_lines:
        text = " ".join(line.split())
        if text:
            paragraph = ElementTree.SubElement(parent, _qti("p"))
            paragraph.text = text


def _append_images(
    parent: ElementTree.Element,
    images: tuple[ExamNetQtiImageResource, ...],
    image_paths: tuple[str, ...],
) -> None:
    for image, image_path in zip(images, image_paths, strict=True):
        paragraph = ElementTree.SubElement(parent, _qti("p"))
        ElementTree.SubElement(
            paragraph,
            _qti("img"),
            {
                "src": image_path,
                "alt": image.alt_text,
            },
        )


def _append_interaction(parent: ElementTree.Element, item: ExamNetQtiItem) -> None:
    if item.interaction_type in {
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    }:
        _append_choice_interaction(parent, item)
        return
    if item.interaction_type == ExamNetQtiInteractionType.FREE_TEXT:
        ElementTree.SubElement(
            parent,
            _qti("extendedTextInteraction"),
            {
                "responseIdentifier": "RESPONSE",
                "expectedLines": "8",
            },
        )
        return
    _append_match_interaction(parent, item.match_pairs)


def _append_gap_fill_body(parent: ElementTree.Element, item: ExamNetQtiItem) -> None:
    gaps = iter(item.text_entry_gaps)
    used_count = 0
    for line in _expanded_prompt_lines(item.prompt_lines):
        used_count += _append_gap_prompt_line(parent, line, gaps)
    remaining_gaps = item.text_entry_gaps[used_count:]
    for gap in remaining_gaps:
        paragraph = ElementTree.SubElement(parent, _qti("p"))
        paragraph.text = f"{gap.label}: "
        ElementTree.SubElement(
            paragraph,
            _qti("textEntryInteraction"),
            {
                "responseIdentifier": gap.response_identifier,
                "expectedLength": _expected_text_entry_length(gap),
            },
        )


def _expanded_prompt_lines(prompt_lines: tuple[str, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for prompt_line in prompt_lines:
        child_lines = tuple(line.strip() for line in prompt_line.splitlines() if line.strip())
        lines.extend(child_lines or (prompt_line,))
    return tuple(lines)


def _append_gap_prompt_line(
    parent: ElementTree.Element,
    line: str,
    gaps: Iterator[ExamNetQtiTextEntryGap],
) -> int:
    paragraph = ElementTree.SubElement(parent, _qti("p"))
    consumed = 0
    position = 0
    tail_target: ElementTree.Element | None = None
    for match in _GAP_MARKER_PATTERN.finditer(line):
        text_before_gap = line[position : match.start()]
        if tail_target is None:
            paragraph.text = (paragraph.text or "") + text_before_gap
        else:
            tail_target.tail = (tail_target.tail or "") + text_before_gap
        gap = next(gaps, None)
        if gap is None:
            if tail_target is None:
                paragraph.text = (paragraph.text or "") + match.group(0)
            else:
                tail_target.tail = (tail_target.tail or "") + match.group(0)
        else:
            tail_target = ElementTree.SubElement(
                paragraph,
                _qti("textEntryInteraction"),
                {
                    "responseIdentifier": gap.response_identifier,
                    "expectedLength": _expected_text_entry_length(gap),
                },
            )
            consumed += 1
        position = match.end()
    remaining_text = line[position:]
    if tail_target is None:
        paragraph.text = (paragraph.text or "") + remaining_text
    else:
        tail_target.tail = (tail_target.tail or "") + remaining_text
    return consumed


def _expected_text_entry_length(gap: ExamNetQtiTextEntryGap) -> str:
    values = tuple(value.strip() for value in gap.accepted_values if value.strip())
    if not values:
        return "20"
    return str(max(8, min(max(len(value) for value in values), 80)))


def _append_choice_interaction(parent: ElementTree.Element, item: ExamNetQtiItem) -> None:
    max_choices = "1"
    if item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
        max_choices = str(len(item.correct_choice_identifiers) or len(item.choices))
    interaction = ElementTree.SubElement(
        parent,
        _qti("choiceInteraction"),
        {
            "responseIdentifier": "RESPONSE",
            "maxChoices": max_choices,
        },
    )
    for choice in item.choices:
        _append_simple_choice(interaction, choice)


def _append_simple_choice(parent: ElementTree.Element, choice: ExamNetQtiChoice) -> None:
    choice_element = ElementTree.SubElement(
        parent,
        _qti("simpleChoice"),
        {"identifier": choice.identifier},
    )
    choice_element.text = choice.text


def _append_match_interaction(
    parent: ElementTree.Element,
    pairs: tuple[ExamNetQtiMatchPair, ...],
) -> None:
    interaction = ElementTree.SubElement(
        parent,
        _qti("matchInteraction"),
        {
            "responseIdentifier": "RESPONSE",
            "maxAssociations": str(len(pairs)),
        },
    )
    left_set = ElementTree.SubElement(interaction, _qti("simpleMatchSet"))
    right_set = ElementTree.SubElement(interaction, _qti("simpleMatchSet"))
    for pair in pairs:
        _append_associable_choice(left_set, pair.left_identifier, pair.left_text)
        _append_associable_choice(right_set, pair.right_identifier, pair.right_text)


def _append_associable_choice(parent: ElementTree.Element, identifier: str, text: str) -> None:
    choice = ElementTree.SubElement(
        parent,
        _qti("simpleAssociableChoice"),
        {"identifier": identifier, "matchMax": "1"},
    )
    choice.text = text


def _qti(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _xsi(local_name: str) -> str:
    return f"{{{XSI_NAMESPACE}}}{local_name}"
