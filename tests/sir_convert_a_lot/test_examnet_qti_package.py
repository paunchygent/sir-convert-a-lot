"""Tests for the Task 280 Exam.net QTI package contract.

Purpose:
    Prove deterministic QTI 2.1 sample package generation, validation-report
    semantics, image packaging, matching proof-gating, and DigiExam IR adapter
    compatibility.

Relationships:
    - Exercises QTI domain contracts, package planning, validation reports, and
      filesystem materialization without adding service routes or UI behavior.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiExamNetProofStatus,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualFollowUpReason,
    ExamNetQtiPackageStatus,
    ExamNetQtiTargetSupportStatus,
    ExamNetQtiTextEntryGap,
    ExamNetQtiValidationStatus,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_samples import (
    ExamNetQtiSamplePackage,
    examnet_qti_task_280_samples,
    examnet_qti_task_303_samples,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_xml import QTI_NAMESPACE
from scripts.sir_convert_a_lot.infrastructure.examnet_qti_package_writer import (
    build_examnet_qti_zip_bytes,
    write_examnet_qti_artifacts,
)


def test_task_280_sample_packages_are_deterministic(tmp_path: Path) -> None:
    for sample in examnet_qti_task_280_samples():
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
    assert _json_string(report, "target_support_status") == (
        ExamNetQtiTargetSupportStatus.PROOF_GATED
    )


def test_post_task_337_missing_choice_key_blocks_qti_package(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_task_303_samples()}
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


def test_post_task_337_missing_gap_values_block_qti_package(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_task_303_samples()}
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
    samples = {sample.name: sample for sample in examnet_qti_task_303_samples()}
    sample_dir = _write_sample(samples["manual-matching-preserved-as-free-text"], tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = _read_report(sample_dir / "qti-validation-report.json")

    assert item.find(f".//{{{QTI_NAMESPACE}}}extendedTextInteraction") is not None
    assert item.find(f".//{{{QTI_NAMESPACE}}}correctResponse") is None
    assert item.find(f"{{{QTI_NAMESPACE}}}responseProcessing") is None
    assert "Vänster kolumn:" in _item_xml(sample_dir / "qti-package.zip")
    assert _json_string(report, "examnet_proof_status") == (
        ExamNetQtiExamNetProofStatus.VENDOR_REPORTED_UNPROVEN
    )


def test_free_text_package_uses_extended_text_without_answer_key(tmp_path: Path) -> None:
    sample_dir = _write_sample(_sample("free-text"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")

    assert item.find(f".//{{{QTI_NAMESPACE}}}extendedTextInteraction") is not None
    assert item.find(f".//{{{QTI_NAMESPACE}}}correctResponse") is None
    assert "Resonera kring" in _item_xml(sample_dir / "qti-package.zip")


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
        assert 'src="resources/item_001-image_001.png"' in item_xml
        report = _read_report(sample_dir / "qti-validation-report.json")
        assert _json_string(report, "package_sha256") == _sha256(sample_dir / "qti-package.zip")


def test_matching_package_is_valid_but_examnet_proof_gated(tmp_path: Path) -> None:
    sample_dir = _write_sample(_sample("matching-proof-gated"), tmp_path)
    item = _item_root(sample_dir / "qti-package.zip")
    report = _read_report(sample_dir / "qti-validation-report.json")

    assert item.find(f".//{{{QTI_NAMESPACE}}}matchInteraction") is not None
    assert _response_declaration(item).attrib["baseType"] == "directedPair"
    assert _correct_values(item) == [
        "left_001 right_001",
        "left_002 right_002",
        "left_003 right_003",
        "left_004 right_004",
    ]
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
    samples = {sample.name: sample for sample in examnet_qti_task_280_samples()}
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


def _correct_values(item: ElementTree.Element) -> list[str]:
    return [
        value.text or ""
        for value in item.findall(f".//{{{QTI_NAMESPACE}}}correctResponse/{{{QTI_NAMESPACE}}}value")
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
