"""Tests for DigiExam ingestion overlay application.

Purpose:
    Prove that source-bound teacher overlays validate against parser-owned IR
    and apply only to effective renderer input.

Relationships:
    - Exercises `domain.digiexam_ingestion_overlay` for Task 295.
    - Complements the v2 API bundle tests with focused stale-binding coverage.
"""

from __future__ import annotations

import json

import pytest

from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlayError,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.digiexam_source_fingerprints import (
    source_item_fingerprint,
)


def test_teacher_overlay_applies_manual_key_to_effective_exam_only() -> None:
    exam = _source_exam()
    item = exam.items[0]

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_overlay_bytes(source_item_fingerprint(item)),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    assert exam.items[0].answer_key.provenance == "absent"
    assert result.effective_exam_for_rendering.items[0].answer_key.provenance == (
        "manual_teacher_key"
    )
    assert result.renderer_input_changed is True
    assert result.ingestion_overlay_report.rejected_entries == ()


def test_teacher_overlay_rejects_stale_item_fingerprint_before_application() -> None:
    exam = _source_exam()

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_overlay_bytes("sha256:stale"),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
        )

    assert error_info.value.code == "digiexam_ingestion_overlay_stale_source_item_fingerprint"


def _source_exam():
    parse_result = DigiExamDxeParser().parse_payload(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": "Single without key",
                            "about": "",
                            "bodyHTML": "<p>Choose the Greek letter.</p>",
                            "images": [],
                            "maxScore": 2,
                            "type": 1,
                            "alternatives": [
                                {"id": 1, "title": "Alpha", "about": "", "right": False},
                                {"id": 2, "title": "Beta", "about": "", "right": False},
                            ],
                        }
                    ]
                }
            ]
        },
        filename="exam.dxe",
    )
    return build_digiexam_intermediate_exam(parse_result)


def _overlay_bytes(source_fingerprint: str) -> bytes:
    return json.dumps(
        {
            "schema_version": "digiexam_ingestion_overlay_v1",
            "source_binding": {
                "source_file_sha256": "sha256:file",
                "source_ir_schema_version": "digiexam_intermediate_exam_v2",
                "source_ir_sha256": "sha256:ir",
            },
            "items": [
                {
                    "item_id": "item-001",
                    "sequence": 1,
                    "item_type": "single_choice",
                    "source_item_fingerprint": source_fingerprint,
                    "manual_answer_key": {
                        "kind": "choice",
                        "correct_alternative_ids": [2],
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode("utf-8")
