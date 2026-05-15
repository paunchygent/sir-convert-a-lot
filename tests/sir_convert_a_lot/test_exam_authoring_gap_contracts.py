"""Tests for source-neutral ExamAuthoringIR gap/open-cloze contracts.

Purpose:
    Prove Task 305 gap ID binding, accepted-value validation, normalization,
    DigiExam adapter mapping, and target-readiness degradation semantics.

Relationships:
    - Exercises `domain.exam_authoring_gap_contracts` as the neutral authoring
      boundary.
    - Exercises `domain.digiexam_exam_authoring_adapter` against available
      DigiExam `.dxe` evidence without promoting DigiExam DTOs to universal IR.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_exam_authoring_adapter import (
    build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    ARTIFACT_DEFINITIONS,
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactEntry,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
    DigiExamResultPdfAnswerExtractor,
)
from scripts.sir_convert_a_lot.domain.digiexam_target_readiness import (
    GAP_OPEN_CLOZE_TARGET_CHOICE_TEACHER_ACTION,
    GAP_OPEN_CLOZE_UNSUPPORTED_TARGET_MESSAGE_KEY,
    TARGET_READINESS_REPORT_SCHEMA_VERSION,
    DigiExamTargetReadiness,
    build_digiexam_target_readiness_report,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_gap_contracts import (
    ExamAuthoringGap,
    ExamAuthoringGapAcceptedValue,
    ExamAuthoringGapAnswerKey,
    ExamAuthoringGapNormalizationProfile,
    ExamAuthoringGapOpenClozeInteraction,
    ExamAuthoringGapPromptBinding,
    ExamAuthoringGapPromptBindingKind,
    ExamAuthoringGapValidationIssueCode,
    build_exam_authoring_gap_open_cloze_interaction,
    normalize_exam_authoring_gap_value,
    validate_exam_authoring_gap_open_cloze_interaction,
    validate_examnet_pdf_gap_open_cloze_profile,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_ir_contracts import (
    ExamAuthoringAnswerKeyProvenance,
    ExamAuthoringSourceEvidence,
)
from scripts.sir_convert_a_lot.domain.exam_authoring_schema_versions import (
    EXAM_AUTHORING_IR_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_pdf_text import (
    DigiExamPdfTextExtractor,
)

_FIXTURE_DIR = Path("inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types")
_DXE = _FIXTURE_DIR / "1772718003-test-samma-prov-i-digiexam.dxe"
_RESULT_PDF = _FIXTURE_DIR / "graded-student-result-sanitized.pdf"


def _result_pdf_evidence() -> DigiExamResultPdfAnswerEvidence:
    _, lines = DigiExamPdfTextExtractor().extract(_RESULT_PDF)
    return DigiExamResultPdfAnswerExtractor(student_block_delimiter="Example Student").extract(
        lines
    )


def test_gap_open_cloze_contract_accepts_id_bound_values_and_profiles_target_limits() -> None:
    interaction = _gap_interaction(
        accepted_values=(
            _accepted_value("gap-001", "Photosynthesis"),
            _accepted_value("gap-002", "Chlorophyll"),
        )
    )

    result = validate_exam_authoring_gap_open_cloze_interaction(interaction)
    target_result = validate_examnet_pdf_gap_open_cloze_profile(interaction)

    assert interaction.schema_version == EXAM_AUTHORING_IR_SCHEMA_VERSION
    assert result.valid is True
    assert result.automatic_evaluation_ready is True
    assert target_result.target_export_ready is False
    assert ExamAuthoringGapValidationIssueCode.EXAMNET_PDF_MULTI_GAP_NOT_SUPPORTED in {
        issue.reason_code for issue in target_result.issues
    }
    assert ExamAuthoringGapValidationIssueCode.EXAMNET_PDF_NATIVE_GAP_SUPPORT_UNPROVEN in {
        issue.reason_code for issue in target_result.issues
    }


def test_gap_open_cloze_contract_keeps_missing_values_valid_but_not_auto_evaluable() -> None:
    interaction = _gap_interaction(accepted_values=())

    result = validate_exam_authoring_gap_open_cloze_interaction(interaction)

    assert result.valid is True
    assert result.automatic_evaluation_ready is False
    assert {
        issue.reason_code
        for issue in result.issues
        if issue.blocks_auto_evaluation and not issue.blocks_contract
    } == {ExamAuthoringGapValidationIssueCode.MISSING_REQUIRED_ACCEPTED_VALUE}


def test_gap_open_cloze_contract_rejects_unknown_blank_and_duplicate_normalized_values() -> None:
    interaction = _gap_interaction(
        normalization_profile=(
            ExamAuthoringGapNormalizationProfile.TRIM_CASE_PUNCTUATION_INSENSITIVE
        ),
        accepted_values=(
            _accepted_value("gap-001", "Stockholm!"),
            _accepted_value("gap-001", "stockholm"),
            _accepted_value("gap-404", "orphan"),
            _accepted_value("gap-002", "   "),
        ),
    )

    result = validate_exam_authoring_gap_open_cloze_interaction(interaction)

    assert result.valid is False
    assert result.automatic_evaluation_ready is False
    assert {
        ExamAuthoringGapValidationIssueCode.DUPLICATE_NORMALIZED_ACCEPTED_VALUE,
        ExamAuthoringGapValidationIssueCode.UNKNOWN_GAP_ID,
        ExamAuthoringGapValidationIssueCode.BLANK_ACCEPTED_VALUE,
    }.issubset({issue.reason_code for issue in result.issues})


def test_gap_open_cloze_contract_preserves_mixed_value_provenance() -> None:
    interaction = _gap_interaction(
        accepted_values=(
            _accepted_value(
                "gap-001",
                "Photosynthesis",
                provenance=ExamAuthoringAnswerKeyProvenance.SOURCE_PROVIDED,
                evidence=(
                    ExamAuthoringSourceEvidence(
                        source_family="digiexam_result_pdf_correct_labels",
                        source_id="gap-item-001",
                        locator="answer_key.correct_gap_answers[0]",
                    ),
                ),
            ),
            _accepted_value(
                "gap-002",
                "Chlorophyll",
                provenance=ExamAuthoringAnswerKeyProvenance.TEACHER_PROVIDED,
                evidence=(
                    ExamAuthoringSourceEvidence(
                        source_family="teacher_overlay",
                        source_id="gap-item-001",
                        locator="manual_answer_key.gap_answers[0]",
                    ),
                ),
            ),
        )
    )

    result = validate_exam_authoring_gap_open_cloze_interaction(interaction)

    assert result.valid is True
    assert result.automatic_evaluation_ready is True
    assert interaction.answer_key.provenance == ExamAuthoringAnswerKeyProvenance.MIXED
    assert [value.provenance for value in interaction.answer_key.accepted_values] == [
        ExamAuthoringAnswerKeyProvenance.SOURCE_PROVIDED,
        ExamAuthoringAnswerKeyProvenance.TEACHER_PROVIDED,
    ]


def test_gap_open_cloze_contract_rejects_absent_or_inconsistent_value_provenance() -> None:
    interaction = _gap_interaction(
        accepted_values=(
            _accepted_value(
                "gap-001",
                "Photosynthesis",
                provenance=ExamAuthoringAnswerKeyProvenance.ABSENT,
            ),
            _accepted_value(
                "gap-002",
                "Chlorophyll",
                provenance=ExamAuthoringAnswerKeyProvenance.SOURCE_PROVIDED,
                evidence=(
                    ExamAuthoringSourceEvidence(
                        source_family="teacher_overlay",
                        source_id="gap-item-001",
                        locator="manual_answer_key.gap_answers[0]",
                    ),
                ),
            ),
        )
    )

    result = validate_exam_authoring_gap_open_cloze_interaction(interaction)

    assert result.valid is False
    assert {
        ExamAuthoringGapValidationIssueCode.ACCEPTED_VALUE_WITHOUT_PROVENANCE,
        ExamAuthoringGapValidationIssueCode.ACCEPTED_VALUE_PROVENANCE_EVIDENCE_MISMATCH,
    }.issubset({issue.reason_code for issue in result.issues})


def test_gap_normalization_keeps_spelling_variants_explicit() -> None:
    assert (
        normalize_exam_authoring_gap_value(
            "  Stockholm!  ",
            ExamAuthoringGapNormalizationProfile.TRIM_CASE_PUNCTUATION_INSENSITIVE,
        )
        == "stockholm"
    )
    assert (
        normalize_exam_authoring_gap_value(
            "Stockholm",
            ExamAuthoringGapNormalizationProfile.EXACT_TRIM_CASE_SENSITIVE,
        )
        == "Stockholm"
    )
    assert (
        normalize_exam_authoring_gap_value(
            "Stockholmm",
            ExamAuthoringGapNormalizationProfile.TRIM_CASE_PUNCTUATION_INSENSITIVE,
        )
        == "stockholmm"
    )


def test_digiexam_gap_item_maps_to_source_neutral_authoring_ir_without_answer_synthesis() -> None:
    parse_result = DigiExamDxeParser().parse_file(_DXE)
    exam = build_digiexam_intermediate_exam(parse_result)

    interactions = build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir(exam)
    interaction = interactions[0]
    result = validate_exam_authoring_gap_open_cloze_interaction(interaction)

    assert len(interactions) == 1
    assert interaction.schema_version == EXAM_AUTHORING_IR_SCHEMA_VERSION
    assert [gap.gap_id for gap in interaction.gaps] == [
        "84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1",
        "21d786a3-2f14-49f1-8ffc-388f06d9a20c",
        "b011fc52-c9b2-4d74-aa78-e94035e0599b",
    ]
    assert {gap.prompt_binding.kind for gap in interaction.gaps} == {
        ExamAuthoringGapPromptBindingKind.HTML_ATTRIBUTE
    }
    assert interaction.answer_key.provenance == ExamAuthoringAnswerKeyProvenance.ABSENT
    assert interaction.answer_key.accepted_values == ()
    assert result.valid is True
    assert result.automatic_evaluation_ready is False


def test_digiexam_result_pdf_gap_answers_map_to_source_provided_authoring_values() -> None:
    parse_result = DigiExamDxeParser().parse_file(_DXE, answer_evidence=_result_pdf_evidence())
    exam = build_digiexam_intermediate_exam(parse_result)

    interaction = build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir(exam)[0]
    result = validate_exam_authoring_gap_open_cloze_interaction(interaction)

    assert interaction.answer_key.provenance == ExamAuthoringAnswerKeyProvenance.SOURCE_PROVIDED
    assert [(value.gap_id, value.value) for value in interaction.answer_key.accepted_values] == [
        ("84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1", "lucktext"),
        ("21d786a3-2f14-49f1-8ffc-388f06d9a20c", "texten"),
        ("b011fc52-c9b2-4d74-aa78-e94035e0599b", "lång"),
    ]
    assert {value.provenance for value in interaction.answer_key.accepted_values} == {
        ExamAuthoringAnswerKeyProvenance.SOURCE_PROVIDED
    }
    assert {
        evidence.source_family
        for value in interaction.answer_key.accepted_values
        for evidence in value.evidence
    } == {"digiexam_result_pdf_correct_labels"}
    assert result.valid is True
    assert result.automatic_evaluation_ready is True


def test_available_dxe_gap_pool_matches_task305_gap_assumptions() -> None:
    paths = sorted(Path("inputs").rglob("*.dxe"))
    interactions: list[ExamAuthoringGapOpenClozeInteraction] = []
    parser = DigiExamDxeParser()
    for path in paths:
        exam = build_digiexam_intermediate_exam(parser.parse_file(path))
        interactions.extend(build_exam_authoring_gap_open_cloze_interactions_from_digiexam_ir(exam))

    assert interactions
    assert all(interaction.answer_key.accepted_values == () for interaction in interactions)
    assert all(
        gap.prompt_binding.kind == ExamAuthoringGapPromptBindingKind.HTML_ATTRIBUTE
        for interaction in interactions
        for gap in interaction.gaps
    )
    assert all(
        validate_exam_authoring_gap_open_cloze_interaction(interaction).valid
        for interaction in interactions
    )


def test_available_dxe_gap_pool_raw_blank_shape_is_metadata_only_guid_and_validations() -> None:
    blank_keys: set[str] = set()
    validation_counts: list[int] = []
    for path in sorted(Path("inputs").rglob("*.dxe")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        exams = payload.get("exams")
        if not isinstance(exams, list) or not exams or not isinstance(exams[0], dict):
            continue
        questions = exams[0].get("questions")
        if not isinstance(questions, list):
            continue
        for question in questions:
            if not isinstance(question, dict) or question.get("type") != 3:
                continue
            blanks = question.get("blanks")
            if not isinstance(blanks, list):
                continue
            for blank in blanks:
                if not isinstance(blank, dict):
                    continue
                blank_keys.update(blank.keys())
                validations = blank.get("validations")
                assert isinstance(validations, list)
                validation_counts.append(
                    len(
                        tuple(
                            value
                            for value in validations
                            if isinstance(value, str) and value.strip()
                        )
                    )
                )

    assert blank_keys == {"guid", "validations"}
    assert validation_counts
    assert set(validation_counts) == {0}


def test_gap_open_cloze_target_readiness_reports_teacher_target_choices() -> None:
    parse_result = DigiExamDxeParser().parse_file(_DXE, answer_evidence=_result_pdf_evidence())
    exam = build_digiexam_intermediate_exam(parse_result)
    report = build_digiexam_target_readiness_report(
        job_id="job-gap-target",
        exam=exam,
        entries=(
            _entry(
                DigiExamMigrationArtifactKey.EXAMNET_PDF,
                DigiExamMigrationArtifactAvailability.UNAVAILABLE,
                unavailable_code="unsupported_target_shape",
            ),
            _entry(
                DigiExamMigrationArtifactKey.QTI_PACKAGE,
                DigiExamMigrationArtifactAvailability.NOT_REQUESTED,
            ),
        ),
        source_ir_sha256="sha256:source",
        effective_exam_sha256="sha256:effective",
    )

    row = next(row for row in report.targets if row.target == "examnet_pdf")

    assert report.schema_version == TARGET_READINESS_REPORT_SCHEMA_VERSION
    assert row.readiness == DigiExamTargetReadiness.UNSUPPORTED_TARGET_SHAPE
    assert row.export_enabled is False
    assert row.reason_code == DigiExamTargetReadiness.UNSUPPORTED_TARGET_SHAPE.value
    assert row.teacher_action == GAP_OPEN_CLOZE_TARGET_CHOICE_TEACHER_ACTION
    assert row.message_key == GAP_OPEN_CLOZE_UNSUPPORTED_TARGET_MESSAGE_KEY
    assert row.item_id == "item-007"
    assert row.source_item_fingerprint is not None
    assert row.source_item_fingerprint.startswith("sha256:")


def _gap_interaction(
    *,
    normalization_profile: ExamAuthoringGapNormalizationProfile = (
        ExamAuthoringGapNormalizationProfile.EXACT_TRIM_CASE_SENSITIVE
    ),
    accepted_values: tuple[ExamAuthoringGapAcceptedValue, ...],
) -> ExamAuthoringGapOpenClozeInteraction:
    return build_exam_authoring_gap_open_cloze_interaction(
        interaction_id="gap-item-001",
        gaps=(
            ExamAuthoringGap(
                gap_id="gap-001",
                display_order=1,
                prompt_binding=ExamAuthoringGapPromptBinding(
                    kind=ExamAuthoringGapPromptBindingKind.HTML_ATTRIBUTE,
                    locator='bodyHTML:span[dx-wg-id="gap-001"]',
                ),
                required_for_auto_evaluation=True,
            ),
            ExamAuthoringGap(
                gap_id="gap-002",
                display_order=2,
                prompt_binding=ExamAuthoringGapPromptBinding(
                    kind=ExamAuthoringGapPromptBindingKind.HTML_ATTRIBUTE,
                    locator='bodyHTML:span[dx-wg-id="gap-002"]',
                ),
                required_for_auto_evaluation=True,
            ),
        ),
        normalization_profile=normalization_profile,
        answer_key=ExamAuthoringGapAnswerKey(accepted_values=accepted_values),
    )


def _accepted_value(
    gap_id: str,
    value: str,
    *,
    provenance: ExamAuthoringAnswerKeyProvenance = (
        ExamAuthoringAnswerKeyProvenance.TEACHER_PROVIDED
    ),
    evidence: tuple[ExamAuthoringSourceEvidence, ...] = (),
) -> ExamAuthoringGapAcceptedValue:
    return ExamAuthoringGapAcceptedValue(
        gap_id=gap_id,
        value=value,
        provenance=provenance,
        evidence=evidence,
    )


def _entry(
    key: DigiExamMigrationArtifactKey,
    availability: DigiExamMigrationArtifactAvailability,
    *,
    unavailable_code: str | None = None,
) -> DigiExamMigrationArtifactEntry:
    definition = ARTIFACT_DEFINITIONS[key]
    return DigiExamMigrationArtifactEntry(
        artifact_key=key,
        filename=definition.filename,
        content_type=definition.content_type,
        availability=availability,
        size_bytes=None,
        sha256=None,
        download_path=None,
        unavailable_code=unavailable_code,
    )
