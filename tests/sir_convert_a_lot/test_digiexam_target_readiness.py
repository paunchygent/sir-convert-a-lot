"""Tests for DigiExam target-readiness item binding.

Purpose:
    Prove readiness rows keep source-owned item fingerprints even when
    effective renderer input changes item scoring.

Relationships:
    - Exercises `domain.digiexam_target_readiness`.
    - Guards Task 322 source-binding behavior for Skriptoteket consumers.
"""

from __future__ import annotations

from dataclasses import replace

from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactEntry,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.digiexam_source_fingerprints import (
    source_item_fingerprint,
)
from scripts.sir_convert_a_lot.domain.digiexam_target_readiness import (
    build_digiexam_target_readiness_report,
)


def test_readiness_item_rows_keep_source_fingerprint_after_point_correction() -> None:
    source_exam = _source_exam()
    source_item = source_exam.items[0]
    source_fingerprint = source_item_fingerprint(source_item)
    effective_item = replace(source_item, max_score=9)
    effective_exam = replace(source_exam, items=(effective_item,))

    report = build_digiexam_target_readiness_report(
        job_id="job-point-correction",
        exam=effective_exam,
        entries=_manual_key_required_entries(),
        source_ir_sha256="sha256:source-ir",
        effective_exam_sha256="sha256:effective-ir",
        source_item_fingerprints={source_item.item_id: source_fingerprint},
    )

    item_rows = tuple(row for row in report.targets if row.item_id == source_item.item_id)
    assert len(item_rows) == 2
    assert source_item_fingerprint(effective_item) != source_fingerprint
    assert {row.source_item_fingerprint for row in item_rows} == {source_fingerprint}


def _source_exam() -> DigiExamIntermediateExam:
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


def _manual_key_required_entries() -> tuple[DigiExamMigrationArtifactEntry, ...]:
    return (
        _unavailable_entry(DigiExamMigrationArtifactKey.EXAMNET_PDF),
        _unavailable_entry(DigiExamMigrationArtifactKey.QTI_PACKAGE),
    )


def _unavailable_entry(
    artifact_key: DigiExamMigrationArtifactKey,
) -> DigiExamMigrationArtifactEntry:
    return DigiExamMigrationArtifactEntry(
        artifact_key=artifact_key,
        filename=f"{artifact_key.value}.json",
        content_type="application/json",
        availability=DigiExamMigrationArtifactAvailability.UNAVAILABLE,
        size_bytes=None,
        sha256=None,
        download_path=None,
        unavailable_code="manual_answer_key_required",
    )
