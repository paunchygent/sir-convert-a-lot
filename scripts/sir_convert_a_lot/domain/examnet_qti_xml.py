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

from xml.etree import ElementTree

from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchPair,
)

QTI_NAMESPACE = "http://www.imsglobal.org/xsd/imsqti_v2p1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
QTI_SCHEMA_LOCATION = (
    "http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
)
MATCH_CORRECT_TEMPLATE = "http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"


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
    _append_prompt(item_body, item.prompt_lines)
    _append_images(item_body, item.image_resources, image_paths)
    _append_interaction(item_body, item)
    if item.evaluation_mode == ExamNetQtiEvaluationMode.AUTOMATIC and item.interaction_type in {
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
        ExamNetQtiInteractionType.MATCHING,
    }:
        ElementTree.SubElement(
            root,
            _qti("responseProcessing"),
            {"template": MATCH_CORRECT_TEMPLATE},
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
        ElementTree.SubElement(
            root,
            _qti("responseDeclaration"),
            {
                "identifier": "RESPONSE",
                "cardinality": "single",
                "baseType": "string",
            },
        )
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


def _append_choice_interaction(parent: ElementTree.Element, item: ExamNetQtiItem) -> None:
    max_choices = "1"
    if item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
        max_choices = str(len(item.correct_choice_identifiers) or len(item.choices))
    interaction = ElementTree.SubElement(
        parent,
        _qti("choiceInteraction"),
        {
            "responseIdentifier": "RESPONSE",
            "shuffle": "false",
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
            "shuffle": "false",
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
