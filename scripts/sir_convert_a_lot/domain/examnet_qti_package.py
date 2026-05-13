"""QTI 2.1 package planning for Exam.net-oriented artifacts.

Purpose:
    Build deterministic, filesystem-free QTI package plans including item XML,
    IMS manifest XML, image resources, proof state, and manual follow-up.

Relationships:
    - Consumes `domain.examnet_qti_contracts` items.
    - Uses `domain.examnet_qti_xml` for assessment item serialization.
    - Feeds infrastructure zip writers and validation-report assembly.
"""

from __future__ import annotations

import hashlib
import re
from xml.etree import ElementTree

from scripts.sir_convert_a_lot.domain.examnet_qti_contracts import (
    EXAMNET_QTI_GENERATOR_VERSION,
    EXAMNET_QTI_PACKAGE_SCHEMA_VERSION,
    EXAMNET_QTI_VERSION,
    ExamNetQtiExamNetProofStatus,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualFollowUp,
    ExamNetQtiManualFollowUpReason,
    ExamNetQtiPackageFile,
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
    ExamNetQtiTargetSupportStatus,
    ExamNetQtiUnsupportedResource,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_xml import serialize_qti_assessment_item

IMSCP_NAMESPACE = "http://www.imsglobal.org/xsd/imscp_v1p1"
IMSCP_SCHEMA_LOCATION = (
    "http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p1.xsd"
)
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"

_SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_IMAGE_MEDIA_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def build_examnet_qti_package_plan(
    *,
    package_name: str,
    items: tuple[ExamNetQtiItem, ...],
) -> ExamNetQtiPackagePlan:
    """Build a deterministic QTI package plan for the supplied items."""

    manual_follow_ups = _manual_follow_ups(items)
    blocking_errors = _blocking_errors(items)
    if blocking_errors:
        return _blocked_plan(
            package_name=package_name,
            items=items,
            manual_follow_ups=manual_follow_ups,
            warnings=blocking_errors,
        )

    item_files: list[ExamNetQtiPackageFile] = []
    image_files_by_item_id: dict[str, tuple[ExamNetQtiPackageFile, ...]] = {}
    for item in sorted(items, key=lambda value: value.sequence):
        image_files = tuple(_image_file(item, image) for image in item.image_resources)
        image_paths = tuple(image.relative_path for image in image_files)
        item_xml = serialize_qti_assessment_item(item, image_paths=image_paths)
        item_files.append(
            _package_file(
                relative_path=_item_xml_path(item),
                content_type="application/xml",
                payload=item_xml,
            )
        )
        image_files_by_item_id[item.item_id] = image_files

    manifest = _manifest_file(
        item_files=tuple(item_files), image_files_by_item_id=image_files_by_item_id
    )
    files = tuple(
        sorted(
            (manifest, *item_files, *_all_image_files(image_files_by_item_id)), key=_file_sort_key
        )
    )
    return ExamNetQtiPackagePlan(
        schema_version=EXAMNET_QTI_PACKAGE_SCHEMA_VERSION,
        generator_version=EXAMNET_QTI_GENERATOR_VERSION,
        qti_version=EXAMNET_QTI_VERSION,
        package_name=package_name,
        status=ExamNetQtiPackageStatus.PASSED,
        target_support_status=_target_support_status(items),
        examnet_proof_status=_proof_status(items),
        items=items,
        files=files,
        manual_follow_ups=manual_follow_ups,
        warnings=(),
    )


def _manual_follow_ups(items: tuple[ExamNetQtiItem, ...]) -> tuple[ExamNetQtiManualFollowUp, ...]:
    follow_ups: list[ExamNetQtiManualFollowUp] = []
    for item in items:
        for resource in item.unsupported_resources:
            follow_ups.append(_unsupported_resource_follow_up(item, resource))
        if item.interaction_type == ExamNetQtiInteractionType.SINGLE_CHOICE:
            if len(item.correct_choice_identifiers) != 1:
                follow_ups.append(_manual_answer_key_follow_up(item))
        if item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
            if not item.correct_choice_identifiers:
                follow_ups.append(_manual_answer_key_follow_up(item))
    return tuple(follow_ups)


def _blocking_errors(items: tuple[ExamNetQtiItem, ...]) -> tuple[str, ...]:
    errors: list[str] = []
    if not items:
        errors.append("QTI package needs at least one item.")
    for item in items:
        errors.extend(_item_errors(item))
    return tuple(errors)


def _item_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    errors: list[str] = []
    if not _SAFE_IDENTIFIER_PATTERN.fullmatch(item.item_id):
        errors.append(f"Item {item.item_id} has an unsafe QTI identifier.")
    if not any(line.strip() for line in item.prompt_lines):
        errors.append(f"Item {item.item_id} has no prompt text.")
    if item.max_score is None:
        errors.append(f"Item {item.item_id} has no point value.")
    errors.extend(_choice_errors(item))
    errors.extend(_matching_errors(item))
    errors.extend(_image_errors(item))
    return tuple(errors)


def _choice_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    if item.interaction_type not in {
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    }:
        return ()
    errors: list[str] = []
    identifiers = tuple(choice.identifier for choice in item.choices)
    if len(identifiers) < 2:
        errors.append(f"Item {item.item_id} needs at least two choices.")
    if len(set(identifiers)) != len(identifiers):
        errors.append(f"Item {item.item_id} has duplicate choice identifiers.")
    missing = tuple(
        identifier
        for identifier in item.correct_choice_identifiers
        if identifier not in identifiers
    )
    if missing:
        errors.append(f"Item {item.item_id} has answer keys for missing choices.")
    if item.interaction_type == ExamNetQtiInteractionType.SINGLE_CHOICE:
        if len(item.correct_choice_identifiers) != 1:
            errors.append(f"Item {item.item_id} needs exactly one correct choice.")
    if item.interaction_type == ExamNetQtiInteractionType.MULTIPLE_RESPONSE:
        if not item.correct_choice_identifiers:
            errors.append(f"Item {item.item_id} needs one or more correct choices.")
    return tuple(errors)


def _matching_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    if item.interaction_type != ExamNetQtiInteractionType.MATCHING:
        return ()
    if not item.match_pairs:
        return (f"Item {item.item_id} needs exact matching pairs.",)
    identifiers = tuple(
        identifier
        for pair in item.match_pairs
        for identifier in (pair.left_identifier, pair.right_identifier)
    )
    if len(set(identifiers)) != len(identifiers):
        return (f"Item {item.item_id} has duplicate match identifiers.",)
    return ()


def _image_errors(item: ExamNetQtiItem) -> tuple[str, ...]:
    errors: list[str] = []
    for image in item.image_resources:
        if image.media_type not in _IMAGE_MEDIA_TYPES:
            errors.append(f"Item {item.item_id} has unsupported image type {image.media_type}.")
        if not image.payload:
            errors.append(f"Item {item.item_id} has an empty image payload.")
    return tuple(errors)


def _blocked_plan(
    *,
    package_name: str,
    items: tuple[ExamNetQtiItem, ...],
    manual_follow_ups: tuple[ExamNetQtiManualFollowUp, ...],
    warnings: tuple[str, ...],
) -> ExamNetQtiPackagePlan:
    return ExamNetQtiPackagePlan(
        schema_version=EXAMNET_QTI_PACKAGE_SCHEMA_VERSION,
        generator_version=EXAMNET_QTI_GENERATOR_VERSION,
        qti_version=EXAMNET_QTI_VERSION,
        package_name=package_name,
        status=ExamNetQtiPackageStatus.BLOCKED,
        target_support_status=_target_support_status(items),
        examnet_proof_status=_proof_status(items),
        items=items,
        files=(),
        manual_follow_ups=manual_follow_ups,
        warnings=warnings,
    )


def _unsupported_resource_follow_up(
    item: ExamNetQtiItem,
    resource: ExamNetQtiUnsupportedResource,
) -> ExamNetQtiManualFollowUp:
    return ExamNetQtiManualFollowUp(
        item_id=item.item_id,
        sequence=item.sequence,
        title=item.title,
        reason_code=ExamNetQtiManualFollowUpReason.UNSUPPORTED_EXAMNET_QTI_RESOURCE,
        message=(
            f"Resursen {resource.label} ({resource.resource_type}) måste läggas till "
            "manuellt efter import i Exam.net."
        ),
        affected_targets=("qti_package",),
    )


def _manual_answer_key_follow_up(item: ExamNetQtiItem) -> ExamNetQtiManualFollowUp:
    return ExamNetQtiManualFollowUp(
        item_id=item.item_id,
        sequence=item.sequence,
        title=item.title,
        reason_code=ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED,
        message="Lägg till eller kontrollera facit innan QTI-paketet används i Exam.net.",
        affected_targets=("qti_package",),
    )


def _item_xml_path(item: ExamNetQtiItem) -> str:
    return f"items/{item.item_id}.xml"


def _image_file(item: ExamNetQtiItem, image: ExamNetQtiImageResource) -> ExamNetQtiPackageFile:
    extension = _IMAGE_MEDIA_TYPES[image.media_type]
    filename = f"{item.item_id}-{_safe_path_stem(image.asset_id)}{extension}"
    return _package_file(
        relative_path=f"resources/{filename}",
        content_type=image.media_type,
        payload=image.payload,
    )


def _manifest_file(
    *,
    item_files: tuple[ExamNetQtiPackageFile, ...],
    image_files_by_item_id: dict[str, tuple[ExamNetQtiPackageFile, ...]],
) -> ExamNetQtiPackageFile:
    ElementTree.register_namespace("", IMSCP_NAMESPACE)
    ElementTree.register_namespace("xsi", XSI_NAMESPACE)
    manifest = ElementTree.Element(
        _cp("manifest"),
        {
            "identifier": "examnet_qti_package",
            _xsi("schemaLocation"): IMSCP_SCHEMA_LOCATION,
        },
    )
    metadata = ElementTree.SubElement(manifest, _cp("metadata"))
    schema = ElementTree.SubElement(metadata, _cp("schema"))
    schema.text = "QTIv2.1 Package"
    schema_version = ElementTree.SubElement(metadata, _cp("schemaversion"))
    schema_version.text = "1.0.0"
    ElementTree.SubElement(manifest, _cp("organizations"))
    resources = ElementTree.SubElement(manifest, _cp("resources"))
    for item_file in item_files:
        item_id = item_file.relative_path.removeprefix("items/").removesuffix(".xml")
        resource = ElementTree.SubElement(
            resources,
            _cp("resource"),
            {
                "identifier": f"res_{item_id}",
                "type": "imsqti_item_xmlv2p1",
                "href": item_file.relative_path,
            },
        )
        ElementTree.SubElement(resource, _cp("file"), {"href": item_file.relative_path})
        for image_file in image_files_by_item_id[item_id]:
            ElementTree.SubElement(resource, _cp("file"), {"href": image_file.relative_path})
    ElementTree.indent(manifest, space="  ")
    xml_text = ElementTree.tostring(
        manifest,
        encoding="unicode",
        xml_declaration=False,
        short_empty_elements=True,
    )
    return _package_file(
        relative_path="imsmanifest.xml",
        content_type="application/xml",
        payload=f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_text}\n'.encode("utf-8"),
    )


def _package_file(relative_path: str, content_type: str, payload: bytes) -> ExamNetQtiPackageFile:
    return ExamNetQtiPackageFile(
        relative_path=relative_path,
        content_type=content_type,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def _all_image_files(
    image_files_by_item_id: dict[str, tuple[ExamNetQtiPackageFile, ...]],
) -> tuple[ExamNetQtiPackageFile, ...]:
    return tuple(file for files in image_files_by_item_id.values() for file in files)


def _file_sort_key(file: ExamNetQtiPackageFile) -> str:
    if file.relative_path == "imsmanifest.xml":
        return ""
    return file.relative_path


def _target_support_status(
    items: tuple[ExamNetQtiItem, ...],
) -> ExamNetQtiTargetSupportStatus:
    if any(item.interaction_type == ExamNetQtiInteractionType.MATCHING for item in items):
        return ExamNetQtiTargetSupportStatus.PROOF_GATED
    return ExamNetQtiTargetSupportStatus.VENDOR_REPORTED_MINIMUM


def _proof_status(items: tuple[ExamNetQtiItem, ...]) -> ExamNetQtiExamNetProofStatus:
    if any(item.interaction_type == ExamNetQtiInteractionType.MATCHING for item in items):
        return ExamNetQtiExamNetProofStatus.NOT_PROVEN
    return ExamNetQtiExamNetProofStatus.VENDOR_REPORTED_UNPROVEN


def _safe_path_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return safe or "asset"


def _cp(local_name: str) -> str:
    return f"{{{IMSCP_NAMESPACE}}}{local_name}"


def _xsi(local_name: str) -> str:
    return f"{{{XSI_NAMESPACE}}}{local_name}"
