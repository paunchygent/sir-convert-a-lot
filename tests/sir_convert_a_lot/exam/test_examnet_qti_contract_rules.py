"""Validator tests for the empirically confirmed Exam.net QTI contract rules.

Purpose:
    Prove that the local package preflight rejects refuted constructions:
    non-positive map entries, orphaned scoring, uncovered matching left rows,
    missing assessmentTest wiring, and shuffle delivery attributes.

Relationships:
    - Mutates deterministic sample package plans from the domain planner and
      asserts `domain.examnet_qti_validation` preflight failures.
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Callable
from io import BytesIO

from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
    ExamNetQtiValidationReport,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_samples import (
    examnet_qti_keyed_samples,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from scripts.sir_convert_a_lot.infrastructure.examnet_qti_package_writer import (
    build_examnet_qti_zip_bytes,
)


def test_unmutated_sample_package_passes_contract_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    report = _preflight(plan, build_examnet_qti_zip_bytes(plan))

    assert report.package_status == ExamNetQtiPackageStatus.PASSED
    assert report.errors == ()


def test_non_positive_map_entry_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _replaced(xml, 'mappedValue="4"', 'mappedValue="0"'),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "must be a positive number" in report.errors[0]


def test_mapping_without_correct_response_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _regex_removed(xml, r"<correctResponse>.*?</correctResponse>"),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "mapping without correctResponse" in report.errors[0]


def test_shuffle_attribute_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _replaced(
            xml,
            'responseIdentifier="RESPONSE" maxChoices="1"',
            'responseIdentifier="RESPONSE" shuffle="false" maxChoices="1"',
        ),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "must not carry a shuffle attribute" in report.errors[0]


def test_matching_left_choice_without_association_fails_preflight() -> None:
    plan = _sample_plan("matching-proof-gated")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _regex_removed(xml, r"\s*<value>left_004 right_004</value>"),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "matching left choice left_004 has no correct association" in report.errors[0]


def test_missing_assessment_test_resource_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "imsmanifest.xml",
        lambda xml: _replaced(xml, 'type="imsqti_test_xmlv2p1"', 'type="imsqti_item_xmlv2p1"'),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "exactly one imsqti_test_xmlv2p1 resource" in report.errors[0]


def test_missing_item_dependency_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "imsmanifest.xml",
        lambda xml: _regex_removed(xml, r'\s*<dependency identifierref="res_item_001" ?/>'),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "missing dependencies on item resources: res_item_001" in report.errors[0]


def test_unresolved_assessment_item_ref_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "assessment.xml",
        lambda xml: _replaced(xml, 'href="items/item_001.xml"', 'href="items/missing.xml"'),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "assessmentItemRef href items/missing.xml does not resolve" in report.errors[0]


def test_package_root_image_src_fails_preflight() -> None:
    plan = _sample_plan("image-single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _replaced(
            xml,
            'src="../resources/item_001-image_001.png"',
            'src="resources/item_001-image_001.png"',
        ),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "refuted package-root style" in report.errors[0]


def test_match_correct_template_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _replaced(xml, "rptemplates/map_response", "rptemplates/match_correct"),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "match_correct responseProcessing template" in report.errors[0]


def test_unreferenced_item_resource_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "assessment.xml",
        lambda xml: _regex_removed(xml, r"\s*<assessmentItemRef [^>]*/>"),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "not referenced by an assessmentItemRef" in report.errors[0]


def test_missing_interaction_prompt_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _regex_removed(xml, r"\s*<prompt>.*?</prompt>"),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "choiceInteraction must carry a non-empty prompt" in report.errors[0]


def test_sibling_body_content_before_interaction_fails_preflight() -> None:
    plan = _sample_plan("single-choice-mcq")
    package_bytes = _mutated_zip_bytes(
        plan,
        "items/item_001.xml",
        lambda xml: _replaced(
            xml,
            "<itemBody>",
            "<itemBody><p>[STRAY] sibling stem before the interaction</p>",
        ),
    )

    report = _preflight(plan, package_bytes)

    assert report.package_status == ExamNetQtiPackageStatus.FAILED
    assert "sibling body content (p) before the interaction" in report.errors[0]


def _sample_plan(sample_name: str) -> ExamNetQtiPackagePlan:
    samples = {sample.name: sample for sample in examnet_qti_keyed_samples()}
    sample = samples[sample_name]
    plan = build_examnet_qti_package_plan(package_name=sample.name, items=sample.items)
    assert plan.status == ExamNetQtiPackageStatus.PASSED
    return plan


def _preflight(
    plan: ExamNetQtiPackagePlan,
    package_bytes: bytes,
) -> ExamNetQtiValidationReport:
    return build_examnet_qti_validation_report(
        plan=plan,
        package_filename="qti-package.zip",
        package_bytes=package_bytes,
    )


def _mutated_zip_bytes(
    plan: ExamNetQtiPackagePlan,
    relative_path: str,
    transform: Callable[[str], str],
) -> bytes:
    buffer = BytesIO()
    transformed = False
    with zipfile.ZipFile(buffer, "w") as archive:
        for file in plan.files:
            payload = file.payload
            if file.relative_path == relative_path:
                payload = transform(payload.decode("utf-8")).encode("utf-8")
                transformed = True
            archive.writestr(file.relative_path, payload)
    assert transformed
    return buffer.getvalue()


def _replaced(xml: str, old: str, new: str) -> str:
    assert old in xml
    return xml.replace(old, new)


def _regex_removed(xml: str, pattern: str) -> str:
    assert re.search(pattern, xml, flags=re.DOTALL) is not None
    return re.sub(pattern, "", xml, flags=re.DOTALL)
