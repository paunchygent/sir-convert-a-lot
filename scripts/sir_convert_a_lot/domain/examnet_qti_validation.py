"""QTI validation-report assembly for Exam.net-oriented packages.

Purpose:
    Create machine-readable `qti_validation_report` artifacts from generated
    QTI package plans and deterministic zip bytes.

Relationships:
    - Consumes QTI package plans from `domain.examnet_qti_package`.
    - Performs local package/XML integrity preflight before infrastructure
      writes report JSON beside generated packages.
    - Records official 1EdTech validator availability separately from local
      validation so Exam.net readiness cannot be overstated.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import asdict
from enum import StrEnum
from xml.etree import ElementTree

from scripts.sir_convert_a_lot.domain.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_TEST_RESOURCE_TYPE,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    EXAMNET_QTI_GENERATOR_VERSION,
    EXAMNET_QTI_VALIDATION_REPORT_SCHEMA_VERSION,
    EXAMNET_QTI_VERSION,
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
    ExamNetQtiValidationReport,
    ExamNetQtiValidationStatus,
    ExamNetQtiValidatorResult,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_package import IMSCP_NAMESPACE
from scripts.sir_convert_a_lot.domain.examnet_qti_xml import QTI_NAMESPACE

_FORBIDDEN_PACKAGE_SUFFIXES = (".mp3", ".wav", ".m4a", ".pdf", ".ggb")
_ITEM_RESOURCE_TYPE = "imsqti_item_xmlv2p1"


def build_examnet_qti_validation_report(
    *,
    plan: ExamNetQtiPackagePlan,
    package_filename: str,
    package_bytes: bytes | None,
) -> ExamNetQtiValidationReport:
    """Build a validation report for a generated or blocked QTI package."""

    package_sha256 = hashlib.sha256(package_bytes).hexdigest() if package_bytes else None
    local_result = _local_validation_result(plan=plan, package_bytes=package_bytes)
    validator_results = (
        local_result,
        _official_validator_result(),
        _qtiworks_result(),
    )
    errors = _report_errors(plan, local_result)
    return ExamNetQtiValidationReport(
        schema_version=EXAMNET_QTI_VALIDATION_REPORT_SCHEMA_VERSION,
        generator_version=EXAMNET_QTI_GENERATOR_VERSION,
        qti_version=EXAMNET_QTI_VERSION,
        profile_id=plan.profile_id,
        package_filename=package_filename,
        package_sha256=package_sha256,
        package_status=_report_status(plan, local_result),
        target_support_status=plan.target_support_status,
        examnet_proof_status=plan.examnet_proof_status,
        validator_results=validator_results,
        manual_follow_ups=plan.manual_follow_ups,
        warnings=plan.warnings,
        errors=errors,
    )


def examnet_qti_validation_report_to_json_data(
    report: ExamNetQtiValidationReport,
) -> dict[str, object]:
    """Return the stable JSON shape for a QTI validation report."""

    data = _json_ready(asdict(report))
    if not isinstance(data, dict):
        raise TypeError("QTI validation report did not serialize to a JSON object.")
    return {str(key): value for key, value in data.items()}


def _local_validation_result(
    *,
    plan: ExamNetQtiPackagePlan,
    package_bytes: bytes | None,
) -> ExamNetQtiValidatorResult:
    if plan.status == ExamNetQtiPackageStatus.BLOCKED:
        return ExamNetQtiValidatorResult(
            name="sir-convert-local-qti-package-preflight",
            version=EXAMNET_QTI_GENERATOR_VERSION,
            layer="package_xml_preflight",
            status=ExamNetQtiValidationStatus.BLOCKED,
            message="QTI package generation was blocked before zip validation.",
        )
    if plan.status == ExamNetQtiPackageStatus.FAILED or package_bytes is None:
        return ExamNetQtiValidatorResult(
            name="sir-convert-local-qti-package-preflight",
            version=EXAMNET_QTI_GENERATOR_VERSION,
            layer="package_xml_preflight",
            status=ExamNetQtiValidationStatus.FAILED,
            message="QTI package bytes were not available for validation.",
        )
    errors = _validate_package_bytes(package_bytes)
    if errors:
        return ExamNetQtiValidatorResult(
            name="sir-convert-local-qti-package-preflight",
            version=EXAMNET_QTI_GENERATOR_VERSION,
            layer="package_xml_preflight",
            status=ExamNetQtiValidationStatus.FAILED,
            message="; ".join(errors),
        )
    return ExamNetQtiValidatorResult(
        name="sir-convert-local-qti-package-preflight",
        version=EXAMNET_QTI_GENERATOR_VERSION,
        layer="package_xml_preflight",
        status=ExamNetQtiValidationStatus.PASSED,
        message=(
            "Package files, XML documents, manifest hrefs, assessment-test wiring, "
            "contract rules, and image references passed."
        ),
    )


def _validate_package_bytes(package_bytes: bytes) -> tuple[str, ...]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(package_bytes), "r") as archive:
            names = tuple(archive.namelist())
            errors.extend(_validate_package_names(names))
            errors.extend(_validate_manifest(archive, names))
            errors.extend(_validate_assessment_test(archive, names))
            errors.extend(_validate_item_image_references(archive, names))
            errors.extend(_validate_contract_rules(archive, names))
    except zipfile.BadZipFile:
        errors.append("Package is not a readable zip archive.")
    return tuple(errors)


def _validate_package_names(names: tuple[str, ...]) -> tuple[str, ...]:
    errors: list[str] = []
    if "imsmanifest.xml" not in names:
        errors.append("Package is missing imsmanifest.xml.")
    for name in names:
        if name.startswith("/") or ".." in name.split("/"):
            errors.append(f"Package path {name} is not safe.")
        if name.lower().endswith(_FORBIDDEN_PACKAGE_SUFFIXES):
            errors.append(f"Package path {name} is forbidden for the Exam.net QTI profile.")
    return tuple(errors)


def _validate_manifest(archive: zipfile.ZipFile, names: tuple[str, ...]) -> tuple[str, ...]:
    if "imsmanifest.xml" not in names:
        return ()
    errors: list[str] = []
    manifest_root = _parse_xml(archive.read("imsmanifest.xml"), "imsmanifest.xml", errors)
    if manifest_root is None:
        return tuple(errors)
    if manifest_root.tag != f"{{{IMSCP_NAMESPACE}}}manifest":
        errors.append("imsmanifest.xml root is not an IMS content package manifest.")
    for file_element in manifest_root.findall(f".//{{{IMSCP_NAMESPACE}}}file"):
        href = file_element.attrib.get("href")
        if href is None:
            errors.append("Manifest file element is missing href.")
        elif href not in names:
            errors.append(f"Manifest href {href} does not resolve inside the package.")
    return tuple(errors)


def _validate_assessment_test(
    archive: zipfile.ZipFile,
    names: tuple[str, ...],
) -> tuple[str, ...]:
    if "imsmanifest.xml" not in names:
        return ()
    manifest_root = _parse_or_none(archive.read("imsmanifest.xml"))
    if manifest_root is None:
        return ()
    errors: list[str] = []
    resources = manifest_root.findall(f".//{{{IMSCP_NAMESPACE}}}resource")
    test_resources = tuple(
        resource
        for resource in resources
        if resource.attrib.get("type") == EXAMNET_QTI_TEST_RESOURCE_TYPE
    )
    if len(test_resources) != 1:
        return (f"Manifest must declare exactly one {EXAMNET_QTI_TEST_RESOURCE_TYPE} resource.",)
    test_resource = test_resources[0]
    item_identifiers = {
        resource.attrib.get("identifier", "")
        for resource in resources
        if resource.attrib.get("type") == _ITEM_RESOURCE_TYPE
    }
    dependency_refs = {
        dependency.attrib.get("identifierref", "")
        for dependency in test_resource.findall(f"{{{IMSCP_NAMESPACE}}}dependency")
    }
    missing_refs = sorted(item_identifiers - dependency_refs)
    if missing_refs:
        errors.append(
            "Assessment test resource is missing dependencies on item resources: "
            + ", ".join(missing_refs)
            + "."
        )
    href = test_resource.attrib.get("href")
    if href is None or href not in names:
        errors.append("Assessment test href does not resolve inside the package.")
        return tuple(errors)
    test_root = _parse_xml(archive.read(href), href, errors)
    if test_root is None:
        return tuple(errors)
    if test_root.tag != f"{{{QTI_NAMESPACE}}}assessmentTest":
        errors.append(f"{href} root is not a QTI assessmentTest.")
    for item_ref in test_root.findall(f".//{{{QTI_NAMESPACE}}}assessmentItemRef"):
        ref_href = item_ref.attrib.get("href")
        if ref_href is None or ref_href not in names:
            errors.append(f"assessmentItemRef href {ref_href} does not resolve inside the package.")
    return tuple(errors)


def _validate_contract_rules(
    archive: zipfile.ZipFile,
    names: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    for name in names:
        if not name.endswith(".xml"):
            continue
        root = _parse_or_none(archive.read(name))
        if root is None:
            continue
        errors.extend(_positive_mapping_errors(name, root))
        errors.extend(_scoring_shape_errors(name, root))
    return tuple(errors)


def _positive_mapping_errors(name: str, root: ElementTree.Element) -> tuple[str, ...]:
    errors: list[str] = []
    for entry in root.iter(f"{{{QTI_NAMESPACE}}}mapEntry"):
        raw_value = entry.attrib.get("mappedValue")
        if raw_value is None or not _is_positive_number(raw_value):
            errors.append(f"{name} mapEntry mappedValue {raw_value!r} must be a positive number.")
    return tuple(errors)


def _scoring_shape_errors(name: str, root: ElementTree.Element) -> tuple[str, ...]:
    errors: list[str] = []
    declarations = {
        declaration.attrib.get("identifier", ""): declaration
        for declaration in root.findall(f"{{{QTI_NAMESPACE}}}responseDeclaration")
    }
    for tag in ("choiceInteraction", "matchInteraction"):
        for interaction in root.iter(f"{{{QTI_NAMESPACE}}}{tag}"):
            if "shuffle" in interaction.attrib:
                errors.append(f"{name} {tag} must not carry a shuffle attribute.")
            declaration = declarations.get(interaction.attrib.get("responseIdentifier", ""))
            if declaration is None:
                continue
            has_mapping = declaration.find(f"{{{QTI_NAMESPACE}}}mapping") is not None
            has_correct = declaration.find(f"{{{QTI_NAMESPACE}}}correctResponse") is not None
            if has_mapping and not has_correct:
                errors.append(f"{name} {tag} has a mapping without correctResponse.")
    for interaction in root.iter(f"{{{QTI_NAMESPACE}}}matchInteraction"):
        errors.extend(_matching_left_coverage_errors(name, interaction, declarations))
    return tuple(errors)


def _matching_left_coverage_errors(
    name: str,
    interaction: ElementTree.Element,
    declarations: dict[str, ElementTree.Element],
) -> tuple[str, ...]:
    match_sets = interaction.findall(f"{{{QTI_NAMESPACE}}}simpleMatchSet")
    if not match_sets:
        return ()
    covered: set[str] = set()
    declaration = declarations.get(interaction.attrib.get("responseIdentifier", ""))
    if declaration is not None:
        for value in declaration.findall(
            f"{{{QTI_NAMESPACE}}}correctResponse/{{{QTI_NAMESPACE}}}value"
        ):
            pair = (value.text or "").split()
            if pair:
                covered.add(pair[0])
    return tuple(
        f"{name} matching left choice {choice.attrib.get('identifier', '')} "
        "has no correct association."
        for choice in match_sets[0].findall(f"{{{QTI_NAMESPACE}}}simpleAssociableChoice")
        if choice.attrib.get("identifier", "") not in covered
    )


def _is_positive_number(raw_value: str) -> bool:
    try:
        return float(raw_value) > 0
    except ValueError:
        return False


def _parse_or_none(payload: bytes) -> ElementTree.Element | None:
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return None


def _validate_item_image_references(
    archive: zipfile.ZipFile,
    names: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    for name in names:
        if not name.startswith("items/") or not name.endswith(".xml"):
            continue
        item_root = _parse_xml(archive.read(name), name, errors)
        if item_root is None:
            continue
        if item_root.tag != f"{{{QTI_NAMESPACE}}}assessmentItem":
            errors.append(f"{name} root is not a QTI assessmentItem.")
        for image in item_root.findall(f".//{{{QTI_NAMESPACE}}}img"):
            image_src = image.attrib.get("src")
            if image_src is None:
                errors.append(f"{name} contains an image without src.")
            elif image_src not in names:
                errors.append(f"{name} image src {image_src} does not resolve inside package.")
    return tuple(errors)


def _parse_xml(
    payload: bytes,
    name: str,
    errors: list[str],
) -> ElementTree.Element | None:
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        errors.append(f"{name} is not well-formed XML: {exc}.")
        return None


def _official_validator_result() -> ExamNetQtiValidatorResult:
    return ExamNetQtiValidatorResult(
        name="1EdTech QTI validator",
        version="external",
        layer="official_qti_validation",
        status=ExamNetQtiValidationStatus.EXTERNAL_VALIDATOR_UNAVAILABLE,
        message=(
            "Official 1EdTech validation is recorded as an external dependency "
            "for this local keyed QTI gate."
        ),
    )


def _qtiworks_result() -> ExamNetQtiValidatorResult:
    return ExamNetQtiValidatorResult(
        name="QTIWorks local semantic smoke",
        version="not_configured",
        layer="local_semantic_smoke",
        status=ExamNetQtiValidationStatus.NOT_RUN,
        message="QTIWorks was not installed as part of this bounded implementation slice.",
    )


def _report_errors(
    plan: ExamNetQtiPackagePlan,
    local_result: ExamNetQtiValidatorResult,
) -> tuple[str, ...]:
    errors: list[str] = []
    if plan.status == ExamNetQtiPackageStatus.FAILED:
        errors.extend(plan.warnings)
    if local_result.status == ExamNetQtiValidationStatus.FAILED:
        errors.append(local_result.message)
    return tuple(errors)


def _report_status(
    plan: ExamNetQtiPackagePlan,
    local_result: ExamNetQtiValidatorResult,
) -> ExamNetQtiPackageStatus:
    if plan.status != ExamNetQtiPackageStatus.PASSED:
        return plan.status
    if local_result.status == ExamNetQtiValidationStatus.FAILED:
        return ExamNetQtiPackageStatus.FAILED
    return plan.status


def _json_ready(value: object) -> object:
    if isinstance(value, StrEnum):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(child) for child in value]
    return value
