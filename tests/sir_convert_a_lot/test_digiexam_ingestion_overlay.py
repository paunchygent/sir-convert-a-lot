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
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    CHOICE_PROMPT_TEMPLATE_VERSION,
    DigiExamAnswerKeyCompletionValidationState,
    answer_key_candidate_payload_digest,
)
from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamAnswerKeyProvenance
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from scripts.sir_convert_a_lot.domain.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from scripts.sir_convert_a_lot.domain.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlayError,
    DigiExamOverlayReviewedCompletionOutcome,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DIGIEXAM_IR_SCHEMA_VERSION,
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
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


def test_teacher_overlay_applies_choice_item_patch_to_effective_exam_only() -> None:
    exam = _source_exam()
    item = exam.items[0]
    fingerprint = source_item_fingerprint(item)

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_choice_patch_overlay_bytes(fingerprint),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    effective_item = result.effective_exam_for_rendering.items[0]
    report_item = result.effective_exam_report.items[0]
    assert exam.items[0].title == "Single without key"
    assert exam.items[0].alternatives[0].title == "Alpha"
    assert exam.items[0].answer_key.provenance == "absent"
    assert effective_item.title == "Repaired single choice"
    assert effective_item.prompt_html == "<p>Choose the repaired Greek letter.</p>"
    assert effective_item.prompt_lines == ("Choose the repaired Greek letter.",)
    assert effective_item.alternatives[0].title == "Gamma"
    assert effective_item.options[0] == "Gamma"
    assert effective_item.answer_key.provenance == "absent"
    assert result.renderer_input_changed is True
    assert result.ingestion_overlay_report.accepted_entries[0].applied_fields == (
        "effective_item_patch",
    )
    assert result.ingestion_overlay_report.rejected_entries == ()
    assert report_item.source_item_fingerprint == fingerprint
    assert report_item.effective_item_patch is not None
    assert report_item.effective_item_patch.changed_fields == (
        "title",
        "prompt_html",
        "prompt_lines",
        "alternative_overrides",
    )
    assert report_item.effective_item_patch.patched_alternative_ids == (1,)


def test_teacher_overlay_patched_choice_content_feeds_pdf_and_qti_renderers() -> None:
    exam = _source_exam()
    item = exam.items[0]

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_choice_patch_with_manual_key_overlay_bytes(source_item_fingerprint(item)),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    document = build_digiexam_examnet_pdf_document(result.effective_exam_for_rendering)
    qti_result = build_examnet_qti_items_from_digiexam_ir(result.effective_exam_for_rendering)

    assert "Choose the repaired Greek letter." in document.html
    assert "Gamma" in document.html
    assert qti_result.manual_follow_ups == ()
    assert qti_result.items[0].prompt_lines == ("Choose the repaired Greek letter.",)
    assert qti_result.items[0].choices[0].text == "Gamma"
    assert qti_result.items[0].correct_choice_identifiers == ("choice_001",)


def test_teacher_overlay_applies_point_correction_to_effective_exam_only() -> None:
    exam = _source_exam()
    item = exam.items[0]
    fingerprint = source_item_fingerprint(item)

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_point_correction_overlay_bytes(fingerprint, max_score=5),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    effective_item = result.effective_exam_for_rendering.items[0]
    report_item = result.effective_exam_report.items[0]
    assert exam.items[0].max_score == 2
    assert effective_item.max_score == 5
    assert source_item_fingerprint(exam.items[0]) == fingerprint
    assert source_item_fingerprint(effective_item) != fingerprint
    assert result.renderer_input_changed is True
    assert result.ingestion_overlay_report.accepted_entries[0].applied_fields == (
        "point_correction",
    )
    assert result.ingestion_overlay_report.rejected_entries == ()
    assert report_item.source_item_fingerprint == fingerprint
    assert report_item.effective_point_correction is not None
    assert report_item.effective_point_correction.kind == "item_points"
    assert report_item.effective_point_correction.source_max_score == 2
    assert report_item.effective_point_correction.effective_max_score == 5
    assert report_item.effective_point_correction.source_item_fingerprint == fingerprint


def test_point_correction_can_coexist_with_manual_answer_key_overlay() -> None:
    exam = _source_exam()
    item = exam.items[0]

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_point_correction_with_manual_key_overlay_bytes(
            source_item_fingerprint(item)
        ),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    report_item = result.effective_exam_report.items[0]
    document = build_digiexam_examnet_pdf_document(result.effective_exam_for_rendering)
    qti_result = build_examnet_qti_items_from_digiexam_ir(result.effective_exam_for_rendering)

    assert result.effective_exam_for_rendering.items[0].max_score == 4
    assert result.effective_exam_for_rendering.items[0].answer_key.provenance == (
        "manual_teacher_key"
    )
    assert result.ingestion_overlay_report.accepted_entries[0].applied_fields == (
        "point_correction",
        "manual_answer_key",
    )
    assert report_item.effective_point_correction is not None
    assert report_item.effective_answer_key is not None
    assert report_item.effective_answer_key.provenance == "teacher_provided"
    assert "Poängvärde: 4" in document.html
    assert qti_result.manual_follow_ups == ()
    assert qti_result.items[0].max_score == 4


def test_point_correction_can_coexist_with_reviewed_completion_overlay() -> None:
    exam = _source_exam()
    item = exam.items[0]
    answer_payload = _choice_answer_payload(2)

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_point_correction_with_reviewed_completion_overlay_bytes(
            source_fingerprint=source_item_fingerprint(item),
            answer_payload=answer_payload,
            review_outcome=DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value,
            candidate_payload_digest=answer_key_candidate_payload_digest(answer_payload),
        ),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
        allow_reviewed_completion=True,
    )

    report_item = result.effective_exam_report.items[0]
    assert result.effective_exam_for_rendering.items[0].max_score == 7
    assert result.effective_exam_for_rendering.items[0].answer_key.provenance == (
        "manual_teacher_key"
    )
    assert result.ingestion_overlay_report.accepted_entries[0].applied_fields == (
        "point_correction",
        "reviewed_completion_answer_key",
    )
    assert report_item.effective_point_correction is not None
    assert report_item.effective_point_correction.source_max_score == 2
    assert report_item.effective_point_correction.effective_max_score == 7
    assert report_item.effective_answer_key is not None
    assert report_item.effective_answer_key.provenance == "reviewed"
    assert report_item.effective_answer_key.correct_alternative_ids == (2,)


@pytest.mark.parametrize("max_score", [0, -1, 1.5, "3", "three"])
def test_point_correction_rejects_non_positive_or_non_strict_integer_values(
    max_score: object,
) -> None:
    exam = _source_exam()

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_point_correction_overlay_bytes(
                source_item_fingerprint(exam.items[0]),
                max_score=max_score,
            ),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
        )

    assert error_info.value.code == "digiexam_ingestion_overlay_invalid"


def test_reviewed_completion_accepts_unchanged_candidate_into_effective_ir_only() -> None:
    exam = _source_exam()
    item = exam.items[0]
    answer_payload = _choice_answer_payload(2)

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_reviewed_completion_overlay_bytes(
            source_fingerprint=source_item_fingerprint(item),
            answer_payload=answer_payload,
            review_outcome=DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value,
            candidate_payload_digest=answer_key_candidate_payload_digest(answer_payload),
        ),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
        allow_reviewed_completion=True,
    )

    report_item = result.effective_exam_report.items[0]
    lineage = report_item.effective_answer_key.lineage if report_item.effective_answer_key else None
    assert exam.items[0].answer_key.provenance == "absent"
    assert result.effective_exam_for_rendering.items[0].answer_key.provenance == (
        "manual_teacher_key"
    )
    assert result.effective_exam_for_rendering.items[0].answer_key.correct_alternative_ids == (2,)
    assert result.effective_exam_report.answer_key_completion_report_sha256 == (
        "sha256:completion-report"
    )
    assert report_item.effective_answer_key is not None
    assert report_item.effective_answer_key.provenance == "reviewed"
    assert report_item.effective_answer_key.correct_alternative_ids == (2,)
    assert lineage is not None
    assert lineage.candidate_id == "candidate-item-001"
    assert lineage.schema_version == DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION
    assert lineage.prompt_template_version == CHOICE_PROMPT_TEMPLATE_VERSION
    assert lineage.review_outcome == (
        DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value
    )
    assert result.ingestion_overlay_report.accepted_entries[0].applied_fields == (
        "reviewed_completion_answer_key",
    )
    assert result.ingestion_overlay_report.rejected_entries == ()


def test_reviewed_completion_teacher_edit_becomes_teacher_provided_with_lineage() -> None:
    exam = _source_exam()
    item = exam.items[0]
    original_payload = _choice_answer_payload(1)
    edited_payload = _choice_answer_payload(2)

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_reviewed_completion_overlay_bytes(
            source_fingerprint=source_item_fingerprint(item),
            answer_payload=edited_payload,
            review_outcome=DigiExamOverlayReviewedCompletionOutcome.TEACHER_EDITED.value,
            candidate_payload_digest=answer_key_candidate_payload_digest(original_payload),
        ),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
        allow_reviewed_completion=True,
    )

    effective_answer_key = result.effective_exam_report.items[0].effective_answer_key
    assert effective_answer_key is not None
    assert effective_answer_key.provenance == "teacher_provided"
    assert effective_answer_key.correct_alternative_ids == (2,)
    assert effective_answer_key.lineage is not None
    assert effective_answer_key.lineage.candidate_payload_digest == (
        answer_key_candidate_payload_digest(original_payload)
    )
    assert effective_answer_key.lineage.review_outcome == (
        DigiExamOverlayReviewedCompletionOutcome.TEACHER_EDITED.value
    )


def test_reviewed_completion_without_apply_mode_fails_closed() -> None:
    exam = _source_exam()
    item = exam.items[0]
    answer_payload = _choice_answer_payload(2)

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_reviewed_completion_overlay_bytes(
                source_fingerprint=source_item_fingerprint(item),
                answer_payload=answer_payload,
                review_outcome=DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value,
                candidate_payload_digest=answer_key_candidate_payload_digest(answer_payload),
            ),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
        )

    assert error_info.value.code == "digiexam_reviewed_completion_not_requested"


def test_reviewed_completion_accepted_unchanged_requires_matching_candidate_digest() -> None:
    exam = _source_exam()
    item = exam.items[0]
    answer_payload = _choice_answer_payload(2)

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_reviewed_completion_overlay_bytes(
                source_fingerprint=source_item_fingerprint(item),
                answer_payload=answer_payload,
                review_outcome=DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value,
                candidate_payload_digest=answer_key_candidate_payload_digest(
                    _choice_answer_payload(1)
                ),
            ),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
            allow_reviewed_completion=True,
        )

    assert error_info.value.code == (
        "digiexam_ingestion_overlay_reviewed_completion_candidate_digest_mismatch"
    )


def test_reviewed_completion_cannot_overwrite_source_bound_answer_key() -> None:
    exam = _source_keyed_exam()
    item = exam.items[0]
    answer_payload = _choice_answer_payload(2)

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_reviewed_completion_overlay_bytes(
                source_fingerprint=source_item_fingerprint(item),
                answer_payload=answer_payload,
                review_outcome=DigiExamOverlayReviewedCompletionOutcome.ACCEPTED_UNCHANGED.value,
                candidate_payload_digest=answer_key_candidate_payload_digest(answer_payload),
            ),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
            allow_reviewed_completion=True,
        )

    assert error_info.value.code == "digiexam_ingestion_overlay_source_bound_answer_key_exists"
    assert exam.items[0].answer_key.provenance == DigiExamAnswerKeyProvenance.DXE_POPULATED_KEY


def test_teacher_overlay_applies_gap_fill_prompt_patch_to_effective_exam() -> None:
    exam = _gap_source_exam()
    item = exam.items[0]

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=_gap_patch_overlay_bytes(source_item_fingerprint(item)),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    effective_item = result.effective_exam_for_rendering.items[0]
    report_item = result.effective_exam_report.items[0]
    assert exam.items[0].prompt_html == "<p>Stockholmsfråga: ___</p>"
    assert effective_item.prompt_html == "<p>Skriv huvudstaden i Sverige.</p>"
    assert effective_item.prompt_lines == ("Skriv huvudstaden i Sverige.",)
    assert effective_item.gaps == exam.items[0].gaps
    assert report_item.effective_item_patch is not None
    assert report_item.effective_item_patch.changed_fields == ("prompt_html", "prompt_lines")


def test_teacher_overlay_rejects_raw_asset_payload_in_item_patch() -> None:
    exam = _source_exam()

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_choice_patch_overlay_bytes(
                source_item_fingerprint(exam.items[0]),
                prompt_html='<img src="data:image/png;base64,AAAA" />',
            ),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
        )

    assert error_info.value.code == "digiexam_ingestion_overlay_invalid"


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


def test_teacher_overlay_rejects_legacy_review_decision_payload() -> None:
    exam = _source_exam()

    with pytest.raises(DigiExamIngestionOverlayError) as error_info:
        parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=_review_decision_overlay_bytes(
                source_item_fingerprint(exam.items[0])
            ),
            source_file_sha256="sha256:file",
            source_ir_sha256="sha256:ir",
            source_exam=exam,
        )

    assert error_info.value.code == "digiexam_ingestion_overlay_invalid"


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


def _source_keyed_exam() -> DigiExamIntermediateExam:
    parse_result = DigiExamDxeParser().parse_payload(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": "Single with key",
                            "about": "",
                            "bodyHTML": "<p>Choose the Greek letter.</p>",
                            "images": [],
                            "maxScore": 2,
                            "type": 1,
                            "alternatives": [
                                {"id": 1, "title": "Alpha", "about": "", "right": False},
                                {"id": 2, "title": "Beta", "about": "", "right": True},
                            ],
                        }
                    ]
                }
            ]
        },
        filename="exam.dxe",
    )
    return build_digiexam_intermediate_exam(parse_result)


def _gap_source_exam() -> DigiExamIntermediateExam:
    parse_result = DigiExamDxeParser().parse_payload(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": "Lucktext",
                            "about": "",
                            "bodyHTML": "<p>Stockholmsfråga: ___</p>",
                            "images": [],
                            "maxScore": 1,
                            "type": 3,
                            "blanks": [
                                {
                                    "guid": "gap-1",
                                    "validations": [],
                                }
                            ],
                        }
                    ]
                }
            ]
        },
        filename="gap.dxe",
    )
    return build_digiexam_intermediate_exam(parse_result)


def _overlay_bytes(source_fingerprint: str) -> bytes:
    return json.dumps(
        {
            "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
            "source_binding": {
                "source_file_sha256": "sha256:file",
                "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
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


def _choice_patch_overlay_bytes(
    source_fingerprint: str,
    *,
    prompt_html: str = "<p>Choose the repaired Greek letter.</p>",
) -> bytes:
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "effective_item_patch": {
                    "kind": "choice",
                    "title": "Repaired single choice",
                    "prompt_html": prompt_html,
                    "prompt_lines": ["Choose the repaired Greek letter."],
                    "alternative_overrides": [
                        {"alternative_id": 1, "text": "Gamma"},
                    ],
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _choice_patch_with_manual_key_overlay_bytes(source_fingerprint: str) -> bytes:
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "effective_item_patch": {
                    "kind": "choice",
                    "title": "Repaired single choice",
                    "prompt_html": "<p>Choose the repaired Greek letter.</p>",
                    "prompt_lines": ["Choose the repaired Greek letter."],
                    "alternative_overrides": [
                        {"alternative_id": 1, "text": "Gamma"},
                    ],
                },
                "manual_answer_key": {
                    "kind": "choice",
                    "correct_alternative_ids": [1],
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _point_correction_overlay_bytes(source_fingerprint: str, *, max_score: object) -> bytes:
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "point_correction": {
                    "kind": "item_points",
                    "max_score": max_score,
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _point_correction_with_manual_key_overlay_bytes(source_fingerprint: str) -> bytes:
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "point_correction": {
                    "kind": "item_points",
                    "max_score": 4,
                },
                "manual_answer_key": {
                    "kind": "choice",
                    "correct_alternative_ids": [2],
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _point_correction_with_reviewed_completion_overlay_bytes(
    *,
    source_fingerprint: str,
    answer_payload: dict[str, JsonValue],
    review_outcome: str,
    candidate_payload_digest: str,
) -> bytes:
    kind = answer_payload.get("kind")
    if not isinstance(kind, str):
        raise RuntimeError("reviewed completion answer payload kind must be a string")
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "point_correction": {
                    "kind": "item_points",
                    "max_score": 7,
                },
                "reviewed_completion_answer_key": {
                    "kind": kind,
                    "review_decision_id": "review-decision-001",
                    "review_outcome": review_outcome,
                    "candidate_lineage": {
                        "completion_report_sha256": "sha256:completion-report",
                        "candidate_id": "candidate-item-001",
                        "candidate_payload_digest": candidate_payload_digest,
                        "provider_profile_id": "local-structured",
                        "schema_name": DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
                        "schema_version": DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
                        "prompt_template_version": CHOICE_PROMPT_TEMPLATE_VERSION,
                        "validation_state": DigiExamAnswerKeyCompletionValidationState.VALID.value,
                    },
                    "answer_payload": answer_payload,
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _gap_patch_overlay_bytes(source_fingerprint: str) -> bytes:
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "item_type": "gap_fill",
                "effective_item_patch": {
                    "kind": "gap_fill",
                    "prompt_html": "<p>Skriv huvudstaden i Sverige.</p>",
                    "prompt_lines": ["Skriv huvudstaden i Sverige."],
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _review_decision_overlay_bytes(source_fingerprint: str) -> bytes:
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "review_decision": {
                    "kind": "accept_current_state_for_export",
                    "decision_id": "review-decision-001",
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _reviewed_completion_overlay_bytes(
    *,
    source_fingerprint: str,
    answer_payload: dict[str, JsonValue],
    review_outcome: str,
    candidate_payload_digest: str,
) -> bytes:
    kind = answer_payload.get("kind")
    if not isinstance(kind, str):
        raise RuntimeError("reviewed completion answer payload kind must be a string")
    return json.dumps(
        _overlay_payload(
            source_fingerprint=source_fingerprint,
            item_fields={
                "reviewed_completion_answer_key": {
                    "kind": kind,
                    "review_decision_id": "review-decision-001",
                    "review_outcome": review_outcome,
                    "candidate_lineage": {
                        "completion_report_sha256": "sha256:completion-report",
                        "candidate_id": "candidate-item-001",
                        "candidate_payload_digest": candidate_payload_digest,
                        "provider_profile_id": "local-structured",
                        "schema_name": DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
                        "schema_version": DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
                        "prompt_template_version": CHOICE_PROMPT_TEMPLATE_VERSION,
                        "validation_state": DigiExamAnswerKeyCompletionValidationState.VALID.value,
                    },
                    "answer_payload": answer_payload,
                },
            },
        ),
        sort_keys=True,
    ).encode("utf-8")


def _choice_answer_payload(correct_id: int) -> dict[str, JsonValue]:
    return {"kind": "choice", "correct_alternative_ids": [correct_id]}


def _overlay_payload(
    *,
    source_fingerprint: str,
    item_fields: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
        "source_binding": {
            "source_file_sha256": "sha256:file",
            "source_ir_schema_version": DIGIEXAM_IR_SCHEMA_VERSION,
            "source_ir_sha256": "sha256:ir",
        },
        "items": [
            {
                "item_id": "item-001",
                "sequence": 1,
                "item_type": item_fields.get("item_type", "single_choice"),
                "source_item_fingerprint": source_fingerprint,
                **{key: value for key, value in item_fields.items() if key != "item_type"},
            }
        ],
    }
