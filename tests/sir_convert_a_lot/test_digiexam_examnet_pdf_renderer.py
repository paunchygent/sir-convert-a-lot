"""Tests for the Task 277 DigiExam Exam.net-oriented PDF renderer.

Purpose:
    Prove that DigiExam IR can render to the promoted Exam.net PDF-converter
    shape with fail-closed warnings and live PDF generation for embedded
    images.

Relationships:
    - Exercises the SRP Exam.net PDF domain renderer modules.
    - Uses WeasyPrint through the infrastructure renderer for live artifact
      validation.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pymupdf

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamGapAnswer,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarningCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrAnswerKey,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_examnet_pdf_renderer import (
    render_digiexam_examnet_pdf,
)

_FIXTURE_DIR = Path("inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types")
_EMBEDDED_IMAGE_DXE = _FIXTURE_DIR / "sanitized-embedded-image.dxe"
_ITEM_013_DXE = (
    Path("inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe")
    / "1811577114-ekologiprov-v-49-25d-e.dxe"
)


def test_examnet_pdf_document_uses_promoted_converter_shape_without_option_labels() -> None:
    exam = _exam_from_payload(_renderable_payload(), filename="renderable.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert "Points:" not in document.html
    assert "Poängvärde: 2" in document.html
    assert "Typ: Fritext" in document.html
    assert "Skriv ditt svar i Exam.net." in document.html
    assert "Type: Multiple choice" in document.html
    assert "Choose one answer" in document.html
    assert "<p>Alpha</p>" in document.html
    assert "<p>Beta</p>" in document.html
    assert "Correct answer: Beta" in document.html
    assert "Type: Multiple response" in document.html
    assert "Choose all correct answers" in document.html
    assert "Correct answers: First; Third" in document.html
    assert document.html.count("Typ: Fritext") == 2
    assert "Type: Short answer" not in document.html
    assert "Correct answers: Stockholm; stockholm" in document.html
    assert "A. Alpha" not in document.html
    assert "<li>" not in document.html


def test_examnet_pdf_document_blocks_machine_marked_item_without_answer_key() -> None:
    payload = _renderable_payload()
    payload["exams"][0]["questions"][1]["alternatives"][1]["right"] = False
    exam = _exam_from_payload(payload, filename="missing-key.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_keeps_missing_key_choice_blocked_without_export_state() -> None:
    payload = _renderable_payload()
    payload["exams"][0]["questions"][1]["alternatives"][1]["right"] = False
    exam = _exam_from_payload(payload, filename="missing-key-accepted.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_keeps_item_013_multigap_blocked_without_key() -> None:
    exam = _item_013_exam()

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_keeps_reviewed_multigap_keys_in_free_text_shape() -> None:
    exam = _item_013_exam()
    item = exam.items[0]
    answers = tuple(
        DigiExamGapAnswer(guid=gap.guid, value=f"facit {index}")
        for index, gap in enumerate(item.gaps, start=1)
    )
    keyed_item = replace(
        item,
        answer_key=DigiExamIrAnswerKey(
            provenance=DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY,
            correct_alternative_ids=(),
            correct_gap_answers=answers,
        ),
    )
    keyed_exam = replace(exam, items=(keyed_item,))

    document = build_digiexam_examnet_pdf_document(keyed_exam)

    assert document.status == DigiExamExamNetPdfStatus.SUCCESS
    assert "Typ: Fritext" in document.html
    assert "Type: Short answer" not in document.html
    assert "Correct answers:" in document.html
    assert "Lucka 1: facit 1" in document.html
    assert "Lucka 5: facit 5" in document.html
    assert "Manuell bedömning" not in document.html
    assert DigiExamExamNetPdfWarningCode.UNSUPPORTED_ITEM_TYPE not in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_blocks_source_labelled_options() -> None:
    payload = _renderable_payload()
    payload["exams"][0]["questions"][1]["alternatives"][0]["title"] = "A. Alpha"
    exam = _exam_from_payload(payload, filename="labelled-options.dxe")

    document = build_digiexam_examnet_pdf_document(exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.OPTION_TEXT_LOOKS_LABELLED in {
        warning.code for warning in document.warnings
    }


def test_examnet_pdf_document_blocks_missing_embedded_asset_payload() -> None:
    exam = _embedded_image_open_ended_exam()
    item = exam.items[0]
    broken_asset = replace(item.embedded_assets[0], content_base64="")
    broken_item = replace(item, embedded_assets=(broken_asset,))
    broken_exam = replace(exam, items=(broken_item,))

    document = build_digiexam_examnet_pdf_document(broken_exam)

    assert document.status == DigiExamExamNetPdfStatus.BLOCKED
    assert DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_MISSING in {
        warning.code for warning in document.warnings
    }


def test_live_examnet_pdf_renderer_generates_pdf_with_embedded_image(tmp_path: Path) -> None:
    exam = _embedded_image_open_ended_exam()
    pdf_path = tmp_path / "embedded-image-examnet.pdf"

    artifacts = render_digiexam_examnet_pdf(exam=exam, output_pdf_path=pdf_path)

    assert artifacts.status == DigiExamExamNetPdfStatus.SUCCESS
    assert artifacts.pdf_path == pdf_path
    assert artifacts.html_path is not None
    assert artifacts.pdf_path.exists()
    assert artifacts.html_path.exists()
    assert len(artifacts.asset_paths) == 1
    assert artifacts.asset_paths[0].exists()
    assert "data-image-id" not in artifacts.html_path.read_text(encoding="utf-8")

    with pymupdf.open(pdf_path) as document:
        assert document.page_count == 1
        page = document[0]
        text = str(page.get_text("text", sort=True))
        assert "Fråga 1" in text
        assert "Poängvärde: 1" in text
        assert "Typ: Fritext" in text
        assert "Skriv ditt svar i Exam.net." in text
        assert "Look at the embedded prompt image." in text
        assert page.get_images(full=True)


def _exam_from_payload(payload: object, *, filename: str) -> DigiExamIntermediateExam:
    parse_result = DigiExamDxeParser().parse_payload(payload, filename=filename)
    return build_digiexam_intermediate_exam(parse_result)


def _embedded_image_open_ended_exam() -> DigiExamIntermediateExam:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    question = payload["exams"][0]["questions"][0]
    question["title"] = "Embedded image prompt"
    question["about"] = "Look at the embedded prompt image."
    question["bodyHTML"] = (
        "<p>Look at the embedded prompt image.</p>"
        '<p><img data-image-id="0" class="fr-fic fr-dib" /></p>'
    )
    question["type"] = 0
    question["blanks"] = []
    return _exam_from_payload(payload, filename="embedded-open-ended.dxe")


def _item_013_exam() -> DigiExamIntermediateExam:
    payload = json.loads(_ITEM_013_DXE.read_text(encoding="utf-8"))
    exam = payload["exams"][0]
    exam["questions"] = [exam["questions"][12]]
    return _exam_from_payload(payload, filename="item-013-multigap.dxe")


def _renderable_payload():
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Essay",
                        "about": "",
                        "bodyHTML": "<p>Explain the water cycle.</p>",
                        "images": [],
                        "maxScore": 3,
                        "type": 0,
                    },
                    {
                        "id": 2,
                        "title": "Single",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 3,
                        "title": "Multiple",
                        "about": "",
                        "bodyHTML": "<p>Choose the ordinal words.</p>",
                        "images": [],
                        "maxScore": 4,
                        "type": 2,
                        "alternatives": [
                            {"id": 1, "title": "First", "about": "", "right": True},
                            {"id": 2, "title": "Between", "about": "", "right": False},
                            {"id": 3, "title": "Third", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 4,
                        "title": "Short",
                        "about": "",
                        "bodyHTML": "<p>Name Sweden's capital.</p>",
                        "images": [],
                        "maxScore": 1,
                        "type": 3,
                        "blanks": [
                            {
                                "guid": "gap-1",
                                "validations": ["Stockholm", "stockholm"],
                            }
                        ],
                    },
                ]
            }
        ]
    }
