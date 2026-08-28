"""Tests for the keyed QTI Exam.net QTI package contract.

Purpose:
    Prove deterministic QTI 2.1 sample package generation, validation-report
    semantics, image packaging, matching proof-gating, and DigiExam IR adapter
    alignment.

Relationships:
    - Exercises QTI domain contracts, package planning, validation reports, and
      filesystem materialization without adding service routes or UI behavior.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import replace
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import pytest

from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiExamNetProofStatus,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualFollowUpReason,
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
    ExamNetQtiTargetSupportStatus,
    ExamNetQtiTextEntryGap,
    ExamNetQtiValidationStatus,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_package import (
    IMSCP_NAMESPACE,
    build_examnet_qti_package_plan,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_samples import (
    ExamNetQtiSamplePackage,
    examnet_qti_keyed_samples,
    examnet_qti_manual_unkeyed_samples,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_xml import (
    MAP_RESPONSE_TEMPLATE,
    QTI_NAMESPACE,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import (
    JobSpecV2,
    OutputFormatV2,
    SourceFormatV2,
)
from scripts.sir_convert_a_lot.infrastructure import digiexam_migration_target_artifacts
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_target_artifacts import (
    build_qti_artifacts,
)
from scripts.sir_convert_a_lot.infrastructure.examnet_qti_package_writer import (
    ExamNetQtiWrittenArtifacts,
    build_examnet_qti_zip_bytes,
    write_examnet_qti_artifacts,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


def test_sample_packages_are_deterministic(tmp_path: Path) -> None:
    for sample in examnet_qti_keyed_samples():
        first = _write_sample(sample, tmp_path / "first")
        second = _write_sample(sample, tmp_path / "second")

        first_report = _read_report(first / sample.report_filename)
        second_report = _read_report(second / sample.report_filename)

        assert _json_string(first_report, "package_status") == "passed"
        assert _json_string(first_report, "package_sha256") == _json_string(
            second_report,
            "package_sha256",
        )
        assert _validator_statuses(first_report) == [
            "passed",
            "external_validator_unavailable",
            "not_run",
        ]
        assert (first / sample.package_filename).read_bytes() == (
            second / sample.package_filename
        ).read_bytes()


def test_choice_packages_encode_single_and_multiple_cardinality(tmp_path: Path) -> None:
    single = _write_sample(_sample("single-choice-mcq"), tmp_path)
    multiple = _write_sample(_sample("multiple-response-mcq"), tmp_path)

    single_item = _item_root(single / "qti-package.zip")
    multiple_item = _item_root(multiple / "qti-package.zip")

    assert _response_declaration(single_item).attrib["cardinality"] == "single"
    assert _choice_interaction(single_item).attrib["maxChoices"] == "1"
    assert _correct_values(single_item) == ["choice_002"]
    assert _response_declaration(multiple_item).attrib["cardinality"] == "multiple"
    assert _choice_interaction(multiple_item).attrib["maxChoices"] == "3"
    assert _correct_values(multiple_item) == ["choice_001", "choice_002", "choice_004"]
    assert "shuffle" not in _choice_interaction(single_item).attrib
    assert "shuffle" not in _choice_interaction(multiple_item).attrib
    assert _mapping(single_item).attrib == {
        "defaultValue": "0",
        "lowerBound": "0",
        "upperBound": "4",
    }
    assert _map_entry_pairs(single_item) == [("choice_002", "4")]
    assert _mapping(multiple_item).attrib == {
        "defaultValue": "0",
        "lowerBound": "0",
        "upperBound": "4",
    }
    assert _map_entry_pairs(multiple_item) == [
        ("choice_001", "1.34"),
        ("choice_002", "1.33"),
        ("choice_004", "1.33"),
    ]
    assert _response_processing_template(single_item) == (
        "http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"
    )
    assert _response_processing_template(multiple_item) == MAP_RESPONSE_TEMPLATE
    assert next(iter(_choice_interaction(single_item))).tag == f"{{{QTI_NAMESPACE}}}prompt"
    assert (_interaction_prompt(single_item, "choiceInteraction").text or "").startswith(
        "Vilket svar kopplar"
    )
    assert (_interaction_prompt(multiple_item, "choiceInteraction").text or "").startswith(
        "Vilka drag stärker"
    )
    assert _item_body_paragraphs(single_item) == []
    assert _item_body_paragraphs(multiple_item) == []


def test_gap_fill_package_encodes_text_entries_and_accepted_values(tmp_path: Path) -> None:
    sample_dir = _write_sample(_sample("gap-fill-text-entry"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = _read_report(sample_dir / "qti-validation-report.json")
    xml = _item_xml(sample_dir / "qti-package.zip")

    response = _response_declaration(item)
    assert response.attrib["identifier"] == "RESPONSE_gap_001"
    assert response.attrib["baseType"] == "string"
    assert response.attrib["cardinality"] == "single"
    assert item.find(f".//{{{QTI_NAMESPACE}}}textEntryInteraction") is not None
    assert _correct_values(item) == ["ATP"]
    assert 'mapKey="ATP"' in xml
    assert 'mapKey="atp"' in xml
    assert _mapping(item).attrib == {
        "defaultValue": "0",
        "lowerBound": "0",
        "upperBound": "1",
    }
    assert [
        (entry.attrib["mapKey"], entry.attrib["mappedValue"], entry.attrib["caseSensitive"])
        for entry in _map_entries(item)
    ] == [("ATP", "1", "false"), ("atp", "1", "false")]
    assert item.find(f"{{{QTI_NAMESPACE}}}responseProcessing") is None
    assert _json_string(report, "target_support_status") == (
        ExamNetQtiTargetSupportStatus.PROOF_GATED
    )


def test_gap_fill_package_splits_max_score_equally_across_gaps() -> None:
    plan = build_examnet_qti_package_plan(
        package_name="gap-split",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Lucktext med två luckor",
                interaction_type=ExamNetQtiInteractionType.GAP_FILL,
                prompt_lines=("Fyll i _____ och _____.",),
                max_score=3,
                text_entry_gaps=(
                    ExamNetQtiTextEntryGap(
                        response_identifier="RESPONSE_gap_001",
                        label="Lucka 1",
                        accepted_values=("alfa", "Alfa"),
                    ),
                    ExamNetQtiTextEntryGap(
                        response_identifier="RESPONSE_gap_002",
                        label="Lucka 2",
                        accepted_values=("beta",),
                    ),
                ),
            ),
        ),
    )
    zip_bytes = build_examnet_qti_zip_bytes(plan)

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        item = ElementTree.fromstring(archive.read("items/item_001.xml"))

    mappings = item.findall(f".//{{{QTI_NAMESPACE}}}mapping")
    assert len(mappings) == 2
    for mapping in mappings:
        assert mapping.attrib == {
            "defaultValue": "0",
            "lowerBound": "0",
            "upperBound": "1.5",
        }
    assert [entry.attrib["mappedValue"] for entry in _map_entries(item)] == ["1.5", "1.5", "1.5"]


def test_post_missing_choice_key_blocks_qti_package(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample_dir = _write_sample(samples["unkeyed-multiple-response-preserved"], tmp_path)
    report = _read_report(sample_dir / "qti-validation-report.json")

    assert not (sample_dir / "qti-package.zip").exists()
    assert _json_string(report, "package_status") == "blocked"
    assert _json_string(report, "profile_id") == "examnet_qti_2_1_v1"
    follow_up = _first_manual_follow_up(report)
    assert _json_string(follow_up, "reason_code") == (
        ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
    )
    assert _report_contains_warning(report, "needs one or more correct choices")


def test_post_missing_gap_values_block_qti_package(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample_dir = _write_sample(samples["manual-gap-fill-preserved-as-free-text"], tmp_path)
    report = _read_report(sample_dir / "qti-validation-report.json")

    assert not (sample_dir / "qti-package.zip").exists()
    assert _json_string(report, "package_status") == "blocked"
    follow_up = _first_manual_follow_up(report)
    assert _json_string(follow_up, "reason_code") == (
        ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
    )
    assert _report_contains_warning(report, "accepted values for every gap")


def test_export_only_matching_sample_preserves_visible_content_as_manual_free_text(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample_dir = _write_sample(samples["manual-matching-preserved-as-free-text"], tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = _read_report(sample_dir / "qti-validation-report.json")

    assert item.find(f".//{{{QTI_NAMESPACE}}}extendedTextInteraction") is not None
    assert item.find(f".//{{{QTI_NAMESPACE}}}correctResponse") is None
    assert item.find(f".//{{{QTI_NAMESPACE}}}mapping") is None
    assert item.find(f"{{{QTI_NAMESPACE}}}responseProcessing") is None
    prompt = _interaction_prompt(item, "extendedTextInteraction")
    prompt_lines = [paragraph.text for paragraph in prompt.findall(f"{{{QTI_NAMESPACE}}}p")]
    assert prompt_lines[:2] == [
        "Para ihop varje begrepp med rätt förklaring.",
        "Vänster kolumn:",
    ]
    assert _item_body_paragraphs(item) == []
    assert "Vänster kolumn:" in _item_xml(sample_dir / "qti-package.zip")
    assert _json_string(report, "examnet_proof_status") == (
        ExamNetQtiExamNetProofStatus.VENDOR_REPORTED_UNPROVEN
    )


def test_free_text_package_uses_extended_text_without_answer_key(tmp_path: Path) -> None:
    sample_dir = _write_sample(_sample("free-text"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")

    assert item.find(f".//{{{QTI_NAMESPACE}}}extendedTextInteraction") is not None
    assert item.find(f".//{{{QTI_NAMESPACE}}}correctResponse") is None
    assert _mapping(item).attrib == {
        "defaultValue": "0",
        "lowerBound": "0",
        "upperBound": "9",
    }
    assert _map_entry_pairs(item) == [("CRITERION_FULL", "9")]
    assert _response_processing_template(item) == MAP_RESPONSE_TEMPLATE
    assert "Resonera kring" in (_interaction_prompt(item, "extendedTextInteraction").text or "")
    assert _item_body_paragraphs(item) == []


def test_image_packages_include_manifest_hrefs_and_resolved_item_images(tmp_path: Path) -> None:
    for sample_name in ("image-single-choice-mcq", "image-free-text"):
        sample_dir = _write_sample(_sample(sample_name), tmp_path / sample_name)
        with zipfile.ZipFile(sample_dir / "qti-package.zip") as archive:
            names = set(archive.namelist())
            assert "imsmanifest.xml" in names
            image_names = {name for name in names if name.startswith("resources/")}
            assert image_names == {"resources/item_001-image_001.png"}
            manifest = archive.read("imsmanifest.xml").decode("utf-8")
            item_xml = archive.read("items/item_001.xml").decode("utf-8")

        assert '<file href="resources/item_001-image_001.png"' in manifest
        assert 'src="../resources/item_001-image_001.png"' in item_xml
        assert 'src="resources/item_001-image_001.png"' not in item_xml
        item = ElementTree.fromstring(item_xml)
        prompt_images = item.findall(f".//{{{QTI_NAMESPACE}}}prompt/{{{QTI_NAMESPACE}}}img")
        assert [image.attrib["src"] for image in prompt_images] == [
            "../resources/item_001-image_001.png"
        ]
        assert _item_body_paragraphs(item) == []
        report = _read_report(sample_dir / "qti-validation-report.json")
        assert _json_string(report, "package_sha256") == _sha256(sample_dir / "qti-package.zip")


def test_matching_package_is_valid_but_examnet_proof_gated(tmp_path: Path) -> None:
    sample_dir = _write_sample(_sample("matching-proof-gated"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = _read_report(sample_dir / "qti-validation-report.json")

    match_interaction = item.find(f".//{{{QTI_NAMESPACE}}}matchInteraction")
    assert match_interaction is not None
    assert "shuffle" not in match_interaction.attrib
    assert _response_declaration(item).attrib["baseType"] == "directedPair"
    assert _correct_values(item) == [
        "left_001 right_001",
        "left_002 right_002",
        "left_003 right_003",
        "left_004 right_004",
    ]
    assert _mapping(item).attrib == {
        "defaultValue": "0",
        "lowerBound": "0",
        "upperBound": "4",
    }
    assert _map_entry_pairs(item) == [
        ("left_001 right_001", "1"),
        ("left_002 right_002", "1"),
        ("left_003 right_003", "1"),
        ("left_004 right_004", "1"),
    ]
    assert _response_processing_template(item) == MAP_RESPONSE_TEMPLATE
    assert next(iter(match_interaction)).tag == f"{{{QTI_NAMESPACE}}}prompt"
    assert (_interaction_prompt(item, "matchInteraction").text or "").startswith(
        "Para ihop varje cellstruktur"
    )
    assert _item_body_paragraphs(item) == []
    assert _json_string(report, "target_support_status") == (
        ExamNetQtiTargetSupportStatus.PROOF_GATED
    )
    assert _json_string(report, "examnet_proof_status") == (ExamNetQtiExamNetProofStatus.NOT_PROVEN)


def test_unsupported_resources_are_omitted_and_reported(tmp_path: Path) -> None:
    sample_dir = _write_sample(_sample("unsupported-resource-omission"), tmp_path)
    report = _read_report(sample_dir / "qti-validation-report.json")

    with zipfile.ZipFile(sample_dir / "qti-package.zip") as archive:
        names = archive.namelist()

    assert all(not name.endswith((".mp3", ".pdf", ".ggb")) for name in names)
    follow_up = _first_manual_follow_up(report)
    assert _json_string(follow_up, "reason_code") == (
        ExamNetQtiManualFollowUpReason.UNSUPPORTED_EXAMNET_QTI_RESOURCE
    )
    assert "teacher-audio.mp3" in _json_string(follow_up, "message")


def test_validation_reports_cover_blocked_and_failed_states() -> None:
    blocked_plan = build_examnet_qti_package_plan(
        package_name="blocked",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Missing key",
                interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
                prompt_lines=("Choose one.",),
                max_score=1,
                choices=(
                    ExamNetQtiChoice("choice_001", "Alpha"),
                    ExamNetQtiChoice("choice_002", "Beta"),
                ),
            ),
        ),
    )
    blocked_report = build_examnet_qti_validation_report(
        plan=blocked_plan,
        package_filename="qti-package.zip",
        package_bytes=None,
    )

    assert blocked_plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert blocked_report.package_status == ExamNetQtiPackageStatus.BLOCKED
    assert blocked_report.validator_results[0].status == ExamNetQtiValidationStatus.BLOCKED

    passed_plan = build_examnet_qti_package_plan(
        package_name="failed-validation",
        items=(_sample("free-text").items[0],),
    )
    failed_report = build_examnet_qti_validation_report(
        plan=passed_plan,
        package_filename="qti-package.zip",
        package_bytes=b"not a zip",
    )

    assert failed_report.package_status == ExamNetQtiPackageStatus.FAILED
    assert failed_report.validator_results[0].status == ExamNetQtiValidationStatus.FAILED
    assert "not a readable zip" in failed_report.errors[0]


def test_manual_unkeyed_choice_plan_passes_where_automatic_choice_blocks() -> None:
    item = ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Missing key",
        interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
        prompt_lines=("Choose one.",),
        max_score=1,
        choices=(
            ExamNetQtiChoice("choice_001", "Alpha"),
            ExamNetQtiChoice("choice_002", "Beta"),
        ),
    )
    automatic_plan = build_examnet_qti_package_plan(
        package_name="automatic-blocked",
        items=(item,),
    )
    manual_plan = build_examnet_qti_package_plan(
        package_name="manual-passed",
        items=(
            ExamNetQtiItem(
                item_id=item.item_id,
                sequence=item.sequence,
                title=item.title,
                interaction_type=item.interaction_type,
                prompt_lines=item.prompt_lines,
                max_score=item.max_score,
                evaluation_mode=ExamNetQtiEvaluationMode.MANUAL_UNKEYED,
                choices=item.choices,
            ),
        ),
    )

    assert automatic_plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert manual_plan.status == ExamNetQtiPackageStatus.PASSED


def test_gap_fill_plan_blocks_when_any_gap_lacks_accepted_values() -> None:
    plan = build_examnet_qti_package_plan(
        package_name="missing-gap-key",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Lucktext",
                interaction_type=ExamNetQtiInteractionType.GAP_FILL,
                prompt_lines=("Fyll i _____.",),
                max_score=1,
                text_entry_gaps=(
                    ExamNetQtiTextEntryGap(
                        response_identifier="RESPONSE_gap_001",
                        label="Lucka 1",
                        accepted_values=(),
                    ),
                ),
            ),
        ),
    )

    assert plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert plan.manual_follow_ups[0].reason_code == (
        ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
    )
    assert "accepted values for every gap" in plan.warnings[0]


def test_automatic_item_with_non_positive_score_blocks_plan() -> None:
    plan = build_examnet_qti_package_plan(
        package_name="zero-score",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Zero score",
                interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
                prompt_lines=("Choose one.",),
                max_score=0,
                choices=(
                    ExamNetQtiChoice("choice_001", "Alpha"),
                    ExamNetQtiChoice("choice_002", "Beta"),
                ),
                correct_choice_identifiers=("choice_001",),
            ),
        ),
    )

    assert plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert any("needs a positive point value" in warning for warning in plan.warnings)


def test_blocked_plan_removes_stale_package_file(tmp_path: Path) -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample = samples["unkeyed-multiple-response-preserved"]
    sample_dir = tmp_path / sample.name
    sample_dir.mkdir(parents=True)
    stale_package = sample_dir / sample.package_filename
    stale_package.write_bytes(b"stale package bytes")

    plan = build_examnet_qti_package_plan(package_name=sample.name, items=sample.items)
    written = write_examnet_qti_artifacts(
        plan=plan,
        output_dir=sample_dir,
        package_filename=sample.package_filename,
        report_filename=sample.report_filename,
    )

    assert plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert written.package_path is None
    assert not stale_package.exists()
    assert (sample_dir / sample.report_filename).exists()


def test_qti_package_entry_fails_when_validation_report_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exam = build_digiexam_intermediate_exam(
        DigiExamDxeParser().parse_payload(
            _digiexam_renderable_payload(),
            filename="qti-adapter.dxe",
        )
    )
    job = _stored_migration_job(tmp_path)

    def _write_with_failed_report(
        *,
        plan: ExamNetQtiPackagePlan,
        output_dir: Path,
        package_filename: str = "qti-package.zip",
        report_filename: str = "qti-validation-report.json",
        report_package_filename: str | None = None,
    ) -> ExamNetQtiWrittenArtifacts:
        written = write_examnet_qti_artifacts(
            plan=plan,
            output_dir=output_dir,
            package_filename=package_filename,
            report_filename=report_filename,
            report_package_filename=report_package_filename,
        )
        return ExamNetQtiWrittenArtifacts(
            package_path=written.package_path,
            report_path=written.report_path,
            report=replace(written.report, package_status=ExamNetQtiPackageStatus.FAILED),
        )

    monkeypatch.setattr(
        digiexam_migration_target_artifacts,
        "write_examnet_qti_artifacts",
        _write_with_failed_report,
    )
    entries, _follow_ups, _warnings = build_qti_artifacts(
        job=job,
        artifacts_dir=tmp_path / "artifacts",
        exam=exam,
    )

    package_entry = entries[DigiExamMigrationArtifactKey.QTI_PACKAGE]
    assert package_entry.availability == DigiExamMigrationArtifactAvailability.FAILED
    assert package_entry.unavailable_code == "qti_validation_failed"
    report_entry = entries[DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT]
    assert report_entry.availability == DigiExamMigrationArtifactAvailability.AVAILABLE


def test_all_sample_packages_wire_assessment_test_into_manifest() -> None:
    for sample in (*examnet_qti_keyed_samples(), *examnet_qti_manual_unkeyed_samples()):
        plan = build_examnet_qti_package_plan(package_name=sample.name, items=sample.items)
        if plan.status != ExamNetQtiPackageStatus.PASSED:
            continue
        zip_bytes = build_examnet_qti_zip_bytes(plan)

        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            names = set(archive.namelist())
            manifest = ElementTree.fromstring(archive.read("imsmanifest.xml"))
            assessment = ElementTree.fromstring(archive.read("assessment.xml"))

        assert "assessment.xml" in names
        resources = manifest.findall(f".//{{{IMSCP_NAMESPACE}}}resource")
        test_resources = [
            resource for resource in resources if resource.attrib["type"] == "imsqti_test_xmlv2p1"
        ]
        assert len(test_resources) == 1
        assert test_resources[0].attrib["identifier"] == "res_test"
        assert test_resources[0].attrib["href"] == "assessment.xml"
        file_hrefs = {
            file.attrib["href"] for file in test_resources[0].findall(f"{{{IMSCP_NAMESPACE}}}file")
        }
        assert file_hrefs == {"assessment.xml"}
        item_identifiers = {
            resource.attrib["identifier"]
            for resource in resources
            if resource.attrib["type"] == "imsqti_item_xmlv2p1"
        }
        dependency_refs = {
            dependency.attrib["identifierref"]
            for dependency in test_resources[0].findall(f"{{{IMSCP_NAMESPACE}}}dependency")
        }
        assert item_identifiers
        assert dependency_refs == item_identifiers
        assert assessment.tag == f"{{{QTI_NAMESPACE}}}assessmentTest"
        item_refs = assessment.findall(f".//{{{QTI_NAMESPACE}}}assessmentItemRef")
        assert item_refs
        assert all(item_ref.attrib["href"] in names for item_ref in item_refs)


def test_digiexam_ir_adapter_feeds_reusable_qti_package_plan() -> None:
    parse_result = DigiExamDxeParser().parse_payload(
        _digiexam_renderable_payload(),
        filename="qti-adapter.dxe",
    )
    exam = build_digiexam_intermediate_exam(parse_result)

    adapter_result = build_examnet_qti_items_from_digiexam_ir(exam)
    plan = build_examnet_qti_package_plan(
        package_name="digiexam-adapter",
        items=adapter_result.items,
    )
    zip_bytes = build_examnet_qti_zip_bytes(plan)

    assert [item.interaction_type for item in adapter_result.items] == [
        ExamNetQtiInteractionType.FREE_TEXT,
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    ]
    assert adapter_result.manual_follow_ups == ()
    assert plan.status == ExamNetQtiPackageStatus.PASSED
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        item_xml = archive.read("items/item_001.xml") + archive.read("items/item_002.xml")
    assert b"choice_002" in item_xml
    assert b"extendedTextInteraction" in item_xml


def _sample(name: str) -> ExamNetQtiSamplePackage:
    samples = {sample.name: sample for sample in examnet_qti_keyed_samples()}
    return samples[name]


def _write_sample(sample: ExamNetQtiSamplePackage, root: Path) -> Path:
    sample_dir = root / str(sample.name)
    plan = build_examnet_qti_package_plan(package_name=sample.name, items=sample.items)
    write_examnet_qti_artifacts(
        plan=plan,
        output_dir=sample_dir,
        package_filename=sample.package_filename,
        report_filename=sample.report_filename,
    )
    return sample_dir


def _read_report(path: Path) -> dict[str, object]:
    data: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return {str(key): value for key, value in data.items()}


def _json_string(data: dict[str, object], key: str) -> str:
    value = data[key]
    assert isinstance(value, str)
    return value


def _validator_statuses(report: dict[str, object]) -> list[str]:
    value = report["validator_results"]
    assert isinstance(value, list)
    statuses: list[str] = []
    for entry in value:
        assert isinstance(entry, dict)
        status = entry.get("status")
        assert isinstance(status, str)
        statuses.append(status)
    return statuses


def _first_manual_follow_up(report: dict[str, object]) -> dict[str, object]:
    value = report["manual_follow_ups"]
    assert isinstance(value, list)
    first = value[0]
    assert isinstance(first, dict)
    return {str(key): child for key, child in first.items()}


def _report_contains_warning(report: dict[str, object], expected_text: str) -> bool:
    value = report["warnings"]
    assert isinstance(value, list)
    return any(isinstance(warning, str) and expected_text in warning for warning in value)


def _item_root(package_path: Path) -> ElementTree.Element:
    return ElementTree.fromstring(_item_xml(package_path).encode("utf-8"))


def _item_xml(package_path: Path) -> str:
    with zipfile.ZipFile(package_path) as archive:
        item_names = sorted(name for name in archive.namelist() if name.startswith("items/"))
        return archive.read(item_names[0]).decode("utf-8")


def _response_declaration(item: ElementTree.Element) -> ElementTree.Element:
    declaration = item.find(f"{{{QTI_NAMESPACE}}}responseDeclaration")
    assert declaration is not None
    return declaration


def _choice_interaction(item: ElementTree.Element) -> ElementTree.Element:
    interaction = item.find(f".//{{{QTI_NAMESPACE}}}choiceInteraction")
    assert interaction is not None
    return interaction


def _interaction_prompt(item: ElementTree.Element, tag: str) -> ElementTree.Element:
    interaction = item.find(f".//{{{QTI_NAMESPACE}}}{tag}")
    assert interaction is not None
    prompt = interaction.find(f"{{{QTI_NAMESPACE}}}prompt")
    assert prompt is not None
    return prompt


def _item_body_paragraphs(item: ElementTree.Element) -> list[ElementTree.Element]:
    return item.findall(f"{{{QTI_NAMESPACE}}}itemBody/{{{QTI_NAMESPACE}}}p")


def _mapping(item: ElementTree.Element) -> ElementTree.Element:
    mapping = item.find(f".//{{{QTI_NAMESPACE}}}mapping")
    assert mapping is not None
    return mapping


def _map_entries(item: ElementTree.Element) -> list[ElementTree.Element]:
    return item.findall(f".//{{{QTI_NAMESPACE}}}mapEntry")


def _map_entry_pairs(item: ElementTree.Element) -> list[tuple[str, str]]:
    return [(entry.attrib["mapKey"], entry.attrib["mappedValue"]) for entry in _map_entries(item)]


def _response_processing_template(item: ElementTree.Element) -> str:
    processing = item.find(f"{{{QTI_NAMESPACE}}}responseProcessing")
    assert processing is not None
    return processing.attrib["template"]


def _correct_values(item: ElementTree.Element) -> list[str]:
    return [
        value.text or ""
        for value in item.findall(f".//{{{QTI_NAMESPACE}}}correctResponse/{{{QTI_NAMESPACE}}}value")
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stored_migration_job(tmp_path: Path) -> StoredJobV2:
    upload_path = tmp_path / "raw" / "qti-adapter.dxe"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"{}")
    now = datetime.now(UTC)
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {
                "kind": "upload",
                "filename": "qti-adapter.dxe",
                "format": "digiexam_dxe",
            },
            "conversion": {
                "output_format": "examnet_migration_bundle",
                "targets": ["qti_package"],
                "artifact_language": "sv",
            },
            "digiexam_migration_options": {
                "parity_pdf_filename": None,
                "ingestion_overlay_filename": None,
                "ingestion_overlay_policy": "none",
                "result_pdf_usage": "correct_machine_marked_answers_only",
                "manual_follow_up_policy": "emit_item_addressable_report",
                "completion_mode": "source_evidence_only",
                "remote_provider_policy": "forbidden",
            },
            "retention": {"pin": False},
        }
    )
    return StoredJobV2(
        job_id="job-qti-report-gate-test",
        spec=spec,
        source_filename="qti-adapter.dxe",
        source_format=SourceFormatV2.DIGIEXAM_DXE,
        output_format=OutputFormatV2.EXAMNET_MIGRATION_BUNDLE,
        upload_path=upload_path,
        resources_zip_path=None,
        reference_docx_path=None,
        artifact_path=tmp_path / "artifacts" / "bundle.zip",
        status=JobStatus.RUNNING,
        created_at=now,
        updated_at=now,
        expires_at=None,
        progress_stage="running",
    )


def _digiexam_renderable_payload() -> dict[str, object]:
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
                ]
            }
        ]
    }
