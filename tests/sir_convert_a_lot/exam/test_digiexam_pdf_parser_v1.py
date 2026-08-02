"""Tests for the DigiExam parser v1 contract.

Purpose:
    Prove fixture-backed DigiExam PDF parsing, deterministic item baselines, and
    fail-closed confidence semantics for unknown or degraded source shapes.

Relationships:
    - Exercises `domain.digiexam_parser` as the parser contract boundary.
    - Exercises `infrastructure.digiexam_pdf_text` only as the PyMuPDF text-line
      adapter for checked-in DigiExam PDF fixtures.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_parser import (
    DigiExamAnswerKeyProvenance,
    DigiExamDocumentMetadata,
    DigiExamItemType,
    DigiExamParser,
    DigiExamParseResult,
    DigiExamParseStatus,
    DigiExamSourceLine,
    DigiExamWarningCode,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_pdf_text import (
    DigiExamPdfTextExtractor,
)

_FIXTURE_DIR = Path("inputs/examples/digiexam-exports")
_ECOLOGY_PDF = _FIXTURE_DIR / "_-25cEkologiprov51-55.pdf"
_CHEMISTRY_PDF = _FIXTURE_DIR / "_-Kemikapitel2ht2525dECA.pdf"


def _parse_pdf(path: Path) -> DigiExamParseResult:
    metadata, lines = DigiExamPdfTextExtractor().extract(path)
    return DigiExamParser().parse(metadata=metadata, lines=lines)


def _metadata() -> DigiExamDocumentMetadata:
    return DigiExamDocumentMetadata(filename="synthetic.pdf", page_count=1, producer="test")


def _line(number: int, text: str) -> DigiExamSourceLine:
    return DigiExamSourceLine(page_number=1, line_number=number, text=text)


def test_ecology_pdf_fixture_matches_exact_open_ended_baseline() -> None:
    result = _parse_pdf(_ECOLOGY_PDF)

    assert result.status == DigiExamParseStatus.SUCCESS
    assert result.renderer_ready is True
    assert result.metadata.page_count == 3
    assert result.metadata.producer == "jsPDF 2.5.1"
    assert len(result.items) == 15
    assert [item.header for item in result.items] == [f"Fråga {number}" for number in range(1, 16)]
    assert Counter(item.item_type for item in result.items) == {
        DigiExamItemType.OPEN_ENDED: 15,
    }
    assert [item.point_marker.points if item.point_marker else None for item in result.items] == [
        1,
        1,
        1,
        1,
        1,
        3,
        3,
        3,
        3,
        3,
        2,
        3,
        2,
        2,
        3,
    ]
    assert result.warnings == ()

    question_14 = result.items[13]
    assert question_14.source_span.start_page == 2
    assert question_14.source_span.end_page == 3


def test_chemistry_pdf_fixture_matches_exact_mixed_item_baseline() -> None:
    result = _parse_pdf(_CHEMISTRY_PDF)

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.metadata.page_count == 3
    assert len(result.items) == 12
    assert [item.header for item in result.items] == [
        "Materia",
        "Para ihop",
        "Grundämnen",
        "Atomen",
        "Ämnen",
        "Joner",
        "Emulsion",
        "Separera",
        "Reaktion",
        "Förklara",
        "Te",
        "Dela upp färg",
    ]
    assert Counter(item.item_type for item in result.items) == {
        DigiExamItemType.MULTIPLE_CHOICE: 3,
        DigiExamItemType.OPEN_ENDED: 8,
        DigiExamItemType.UNKNOWN: 1,
    }
    assert [item.point_marker.points if item.point_marker else None for item in result.items] == [
        None,
        None,
        None,
        4,
        4,
        None,
        2,
        3,
        3,
        3,
        3,
        3,
    ]


def test_examnet_style_pdf_matching_is_not_digiexam_canonical_structure() -> None:
    result = _parse_pdf(_CHEMISTRY_PDF)
    matching_item = result.items[1]

    assert matching_item.header == "Para ihop"
    assert matching_item.item_type == DigiExamItemType.UNKNOWN
    assert matching_item.answer_key_provenance == DigiExamAnswerKeyProvenance.NOT_APPLICABLE
    assert matching_item.prompt_lines == (
        "Skriv rätt bokstav i ordluckan.",
        "1. Kolatom",
        "2. Syreatom",
        "3. Syremolekyl",
        "4. Koldioxid",
        "a. O 2",
        "b. O",
        "c. CO 2",
        "d. C",
        "1 = 1. 2 = 2. 3 = 3. 4 = 4.",
    )

    assert DigiExamWarningCode.UNKNOWN_SOURCE_SHAPE in {
        warning.code for warning in matching_item.warnings
    }

    missing_key_warnings = [
        warning
        for warning in result.warnings
        if warning.code == DigiExamWarningCode.MISSING_ANSWER_KEY_PROVENANCE
    ]
    assert len(missing_key_warnings) == 3
    assert all(not warning.blocking for warning in missing_key_warnings)


def test_chemistry_multiple_choice_prompt_and_options_are_exact() -> None:
    result = _parse_pdf(_CHEMISTRY_PDF)
    items = {item.header: item for item in result.items}

    assert items["Materia"].prompt_lines == ("Vilka av alternativen är exempel på materia?",)
    assert items["Materia"].options == ("sten", "syre", "värme", "socker", "skugga")

    assert items["Grundämnen"].prompt_lines == ("Vilka av ämnena är grundämnen ?",)
    assert items["Grundämnen"].options == (
        "silver",
        "mjölk",
        "helium",
        "olja",
        "guld",
        "vatten",
    )

    assert items["Joner"].prompt_lines == (
        "Naturen består av olika kemiska föreningar. Många av dessa föreningar "
        "är uppbyggda av joner. Vilket av alternativen",
        "stämmer?",
    )
    assert items["Joner"].options == (
        "En jon har lika många elektroner och protoner.",
        "En jon har olika många elektroner och protoner.",
        "En jon har olika många neutroner och elektroner.",
        "En jon har lika många neutroner och protoner.",
    )


def test_chemistry_page_boundary_option_does_not_leak_into_atomen_prompt() -> None:
    result = _parse_pdf(_CHEMISTRY_PDF)
    items = {item.header: item for item in result.items}

    assert items["Atomen"].prompt_lines == (
        "a) Vad heter de tre slag partiklar som en atom består av?",
        "b) Var hittar man dem i atomen?",
        "c) Vilka egenskaper har de?",
        "d) Rita en atommodell och sätt ut delarna.",
    )
    assert "vatten" not in items["Atomen"].prompt_lines
    assert "vatten" in items["Grundämnen"].options


def test_ambiguous_multiple_choice_boundary_blocks_renderer_ready_output() -> None:
    result = DigiExamParser().parse(
        metadata=_metadata(),
        lines=(
            _line(1, "Materia"),
            _line(2, "Vilka av alternativen är exempel på materia?"),
            _line(3, "    sten"),
            _line(4, "orphan prompt fragment"),
            _line(5, "    syre"),
            _line(6, "    skugga"),
        ),
    )

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items[0].item_type == DigiExamItemType.MULTIPLE_CHOICE
    assert DigiExamWarningCode.UNSUPPORTED_STRUCTURE in {
        warning.code for warning in result.warnings
    }


def test_text_before_first_header_blocks_renderer_ready_output() -> None:
    result = DigiExamParser().parse(
        metadata=_metadata(),
        lines=(
            _line(1, "lös text före första frågan"),
            _line(2, "Fråga 1"),
            _line(3, "Max poäng: 1"),
            _line(4, "Varför behövs växter?"),
        ),
    )

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert DigiExamWarningCode.MISSING_REQUIRED_ANCHOR in {
        warning.code for warning in result.warnings
    }


def test_unknown_item_shape_blocks_renderer_ready_output() -> None:
    result = DigiExamParser().parse(
        metadata=_metadata(),
        lines=(
            _line(1, "Fråga 1"),
            _line(2, "Okänd itemform med åäö."),
        ),
    )

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items[0].item_type == DigiExamItemType.UNKNOWN
    assert DigiExamWarningCode.UNKNOWN_SOURCE_SHAPE in {warning.code for warning in result.warnings}


def test_lossy_swedish_text_extraction_blocks_renderer_ready_output() -> None:
    result = DigiExamParser().parse(
        metadata=_metadata(),
        lines=(
            _line(1, "Materia"),
            _line(2, "Which examples are matter?"),
            _line(3, "stone"),
            _line(4, "oxygen"),
            _line(5, "shadow"),
        ),
    )

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert DigiExamWarningCode.LOSSY_SWEDISH_TEXT_EXTRACTION in {
        warning.code for warning in result.warnings
    }


def test_incomplete_matching_structure_blocks_renderer_ready_output() -> None:
    result = DigiExamParser().parse(
        metadata=_metadata(),
        lines=(
            _line(1, "Para ihop"),
            _line(2, "Para ihop varje begrepp med rätt förklaring."),
            _line(3, "1. fotosyntes"),
            _line(4, "2. cellandning"),
        ),
    )

    assert result.status == DigiExamParseStatus.BLOCKED
    assert result.renderer_ready is False
    assert result.items[0].item_type == DigiExamItemType.UNKNOWN
    assert DigiExamWarningCode.UNKNOWN_SOURCE_SHAPE in {warning.code for warning in result.warnings}
