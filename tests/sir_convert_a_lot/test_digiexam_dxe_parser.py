"""Tests for the Task 274 DigiExam `.dxe` parser contract.

Purpose:
    Prove fixture-backed `.dxe` parsing, canonical structure extraction, and
    correct-answer-only enrichment from sanitized DigiExam result PDFs.

Relationships:
    - Exercises `domain.digiexam_dxe_parser` as the `.dxe` parser boundary.
    - Reuses `infrastructure.digiexam_pdf_text` only to provide result-PDF text
      lines for the pure domain enrichment rules.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
    DigiExamParseStatus,
    DigiExamSourceLine,
    DigiExamWarningCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from scripts.sir_convert_a_lot.domain.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
    DigiExamResultPdfAnswerExtractor,
    DigiExamResultPdfAnswerItem,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_pdf_text import (
    DigiExamPdfTextExtractor,
)

_FIXTURE_DIR = Path("inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types")
_DXE = _FIXTURE_DIR / "1772718003-test-samma-prov-i-digiexam.dxe"
_DUPLICATE_DXE = _FIXTURE_DIR / "1772718003-test-duplicate.dxe"
_RESULT_PDF = _FIXTURE_DIR / "graded-student-result-sanitized.pdf"


def _result_pdf_evidence():
    _, lines = DigiExamPdfTextExtractor().extract(_RESULT_PDF)
    return DigiExamResultPdfAnswerExtractor(student_block_delimiter="Example Student").extract(
        lines
    )


def test_dxe_fixture_preserves_exact_observed_structure_without_answer_synthesis() -> None:
    result = DigiExamDxeParser().parse_file(_DXE)

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.metadata.filename == _DXE.name
    assert result.metadata.producer == "DigiExam .dxe"
    assert len(result.items) == 7
    assert [item.digiexam_type_code for item in result.items] == [0, 1, 1, 2, 2, 2, 3]
    assert [item.max_score for item in result.items] == [5, 2, 2, 2, 4, 6, 3]
    assert [item.item_type for item in result.items] == [
        DigiExamItemType.OPEN_ENDED,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    ]
    assert [item.header for item in result.items] == [
        "Fritextfråga",
        "Flervalsfråga typ 1",
        "Ytterligare en flervalsfråga",
        "Flera rätta svar (flervalsfråga)",
        "Fråga 5",
        "Fråga 6",
        "Lucktext",
    ]

    machine_marked = result.items[1:]
    assert all(
        item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT for item in machine_marked
    )
    assert all(item.correct_alternative_ids == () for item in machine_marked)
    assert all(item.correct_gap_values == () for item in machine_marked)


def test_dxe_fixture_preserves_alternatives_gaps_and_grading_policy() -> None:
    result = DigiExamDxeParser().parse_file(_DXE)
    items = {item.header: item for item in result.items}

    first_mcq = items["Flervalsfråga typ 1"]
    assert [alternative.id for alternative in first_mcq.alternatives] == [1, 2, 3, 4, 5]
    assert [alternative.title for alternative in first_mcq.alternatives] == [
        "Första alternativet ",
        "Andra alternativet",
        "Tredje alternativet",
        "Fjärde alternativet",
        "Ytterligare ett alternativ. Man kan lägga till hur många man vill",
    ]
    assert [alternative.right for alternative in first_mcq.alternatives] == [
        False,
        False,
        False,
        False,
        False,
    ]

    question_6 = items["Fråga 6"]
    assert question_6.grading_policy is not None
    assert question_6.grading_policy.grading_type == 2
    assert question_6.grading_policy.is_alternative_choice_limit_enabled is True
    assert question_6.grading_policy.alternative_choice_limit == 2

    gap_item = items["Lucktext"]
    assert [gap.guid for gap in gap_item.gaps] == [
        "84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1",
        "21d786a3-2f14-49f1-8ffc-388f06d9a20c",
        "b011fc52-c9b2-4d74-aa78-e94035e0599b",
    ]
    assert [gap.validations for gap in gap_item.gaps] == [(), (), ()]


def test_duplicate_dxe_fixture_proves_same_question_shape() -> None:
    parser = DigiExamDxeParser()
    primary = parser.parse_file(_DXE)
    duplicate = parser.parse_file(_DUPLICATE_DXE)

    assert [item.question_id for item in duplicate.items] == [
        item.question_id for item in primary.items
    ]
    assert [item.header for item in duplicate.items] == [item.header for item in primary.items]
    assert [item.digiexam_type_code for item in duplicate.items] == [
        item.digiexam_type_code for item in primary.items
    ]
    assert [item.max_score for item in duplicate.items] == [
        item.max_score for item in primary.items
    ]


def test_result_pdf_enrichment_imports_only_correct_machine_marked_answers() -> None:
    result = DigiExamDxeParser().parse_file(_DXE, answer_evidence=_result_pdf_evidence())
    items = {item.header: item for item in result.items}

    assert items["Fritextfråga"].answer_key_provenance == DigiExamAnswerKeyProvenance.NOT_APPLICABLE
    assert items["Flervalsfråga typ 1"].correct_alternative_ids == (2,)
    assert items["Ytterligare en flervalsfråga"].correct_alternative_ids == (2,)
    assert items["Flera rätta svar (flervalsfråga)"].correct_alternative_ids == (1, 2)
    assert items["Fråga 5"].correct_alternative_ids == (1, 2)
    assert items["Fråga 6"].correct_alternative_ids == (1, 2)
    assert items["Lucktext"].correct_gap_values == ("lucktext", "texten", "lång")
    assert [(answer.guid, answer.value) for answer in items["Lucktext"].correct_gap_answers] == [
        ("84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1", "lucktext"),
        ("21d786a3-2f14-49f1-8ffc-388f06d9a20c", "texten"),
        ("b011fc52-c9b2-4d74-aa78-e94035e0599b", "lång"),
    ]

    enriched_items = [
        item
        for item in result.items[1:]
        if item.answer_key_provenance != DigiExamAnswerKeyProvenance.NOT_APPLICABLE
    ]
    assert all(
        item.answer_key_provenance == DigiExamAnswerKeyProvenance.GRADED_RESULT_PDF_CORRECT_LABELS
        for item in enriched_items
    )
    assert 1 not in items["Flervalsfråga typ 1"].correct_alternative_ids
    assert "fel svar" not in items["Lucktext"].correct_gap_values


def test_result_pdf_answer_extractor_discards_student_specific_result_data() -> None:
    evidence = _result_pdf_evidence()

    flattened_alternatives = {
        answer for item in evidence.items for answer in item.correct_alternative_texts
    }
    flattened_gaps = {answer for item in evidence.items for answer in item.correct_gap_values}

    assert "Här är mitt svar på fritextfrågan" not in flattened_alternatives
    assert "Example Student" not in flattened_alternatives
    assert "Erhållen poäng: 4" not in flattened_alternatives
    assert "fel svar" not in flattened_gaps


def test_result_pdf_answer_extractor_uses_explicit_sanitized_block_delimiter() -> None:
    _, lines = DigiExamPdfTextExtractor().extract(_RESULT_PDF)
    redacted_lines = tuple(
        DigiExamSourceLine(
            page_number=line.page_number,
            line_number=line.line_number,
            text="Redacted Learner" if line.text.strip() == "Example Student" else line.text,
        )
        for line in lines
    )

    evidence = DigiExamResultPdfAnswerExtractor(student_block_delimiter="Redacted Learner").extract(
        redacted_lines
    )

    assert evidence.item_for_title("Lucktext") is not None


def test_result_pdf_duplicate_alternative_labels_fail_closed() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][1]["alternatives"][0]["title"] = "Andra alternativet"

    result = DigiExamDxeParser().parse_payload(
        payload,
        filename="duplicate-answer-label.dxe",
        answer_evidence=_result_pdf_evidence(),
    )

    item = result.items[1]
    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert item.correct_alternative_ids == ()
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT
    assert DigiExamWarningCode.UNSUPPORTED_STRUCTURE in {
        warning.code for warning in result.warnings
    }


def test_result_pdf_unmatched_alternative_label_fails_closed() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][1]["alternatives"][1]["title"] = "Inte korrekt label"

    result = DigiExamDxeParser().parse_payload(
        payload,
        filename="unmatched-answer-label.dxe",
        answer_evidence=_result_pdf_evidence(),
    )

    item = result.items[1]
    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert item.correct_alternative_ids == ()
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT
    assert DigiExamWarningCode.UNSUPPORTED_STRUCTURE in {
        warning.code for warning in result.warnings
    }


def test_result_pdf_gap_answer_count_mismatch_fails_closed_without_enrichment() -> None:
    evidence = DigiExamResultPdfAnswerEvidence(
        items=(
            DigiExamResultPdfAnswerItem(
                title="Lucktext",
                correct_alternative_texts=(),
                correct_gap_values=("lucktext",),
            ),
        )
    )

    result = DigiExamDxeParser().parse_file(_DXE, answer_evidence=evidence)

    item = result.items[-1]
    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert item.header == "Lucktext"
    assert item.correct_gap_values == ()
    assert item.correct_gap_answers == ()
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.ABSENT
    assert DigiExamWarningCode.UNSUPPORTED_STRUCTURE in {
        warning.code for warning in result.warnings
    }


def test_populated_dxe_right_flags_are_treated_as_dxe_answer_key_provenance() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][1]["alternatives"][1]["right"] = True

    result = DigiExamDxeParser().parse_payload(payload, filename="populated.dxe")

    item = result.items[1]
    assert item.answer_key_provenance == DigiExamAnswerKeyProvenance.DXE_POPULATED_KEY
    assert item.correct_alternative_ids == (2,)


def test_unsupported_dxe_question_type_fails_closed() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["type"] = 99

    result = DigiExamDxeParser().parse_payload(payload, filename="unknown-type.dxe")

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items[0].item_type == DigiExamItemType.UNKNOWN
    assert DigiExamWarningCode.UNKNOWN_SOURCE_SHAPE in {warning.code for warning in result.warnings}


def test_malformed_dxe_payload_fails_closed_without_untyped_exception() -> None:
    result = DigiExamDxeParser().parse_text("{", filename="broken.dxe")

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items == ()
    assert result.warnings[0].code == DigiExamWarningCode.MALFORMED_SOURCE


def test_missing_required_dxe_sections_fail_closed_without_untyped_exception() -> None:
    result = DigiExamDxeParser().parse_payload(
        {"exams": [{"title": "Broken"}]}, filename="missing.dxe"
    )

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items == ()
    assert result.warnings[0].code == DigiExamWarningCode.MALFORMED_SOURCE
