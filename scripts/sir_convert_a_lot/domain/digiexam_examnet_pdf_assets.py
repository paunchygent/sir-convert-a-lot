"""Exam.net PDF renderer embedded asset preparation.

Purpose:
    Validate DigiExam IR embedded asset payloads and build the local asset-file
    plan required by the Exam.net-oriented PDF artifact.

Relationships:
    - Consumes renderer-neutral IR assets from `domain.digiexam_ir_contracts`.
    - Produces contracts from `domain.digiexam_examnet_pdf_contracts`.
    - Used by the thin Exam.net PDF document coordinator before prompt and item
      rendering.
"""

from __future__ import annotations

import base64
import binascii
import hashlib

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamEmbeddedAsset
from scripts.sir_convert_a_lot.domain.digiexam_examnet_pdf_contracts import (
    AssetReferenceKey,
    DigiExamExamNetPdfAssetFile,
    DigiExamExamNetPdfAssetPreparation,
    DigiExamExamNetPdfWarning,
    DigiExamExamNetPdfWarningCode,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)

_SUPPORTED_ASSET_MEDIA_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


def prepare_examnet_pdf_assets(
    exam: DigiExamIntermediateExam,
) -> DigiExamExamNetPdfAssetPreparation:
    """Build a validated renderable asset plan for a DigiExam IR exam."""

    asset_files: list[DigiExamExamNetPdfAssetFile] = []
    asset_paths_by_reference: dict[AssetReferenceKey, str] = {}
    warnings: list[DigiExamExamNetPdfWarning] = []

    for item in exam.items:
        item_asset_files, item_paths, item_warnings = _prepare_item_assets(item)
        asset_files.extend(item_asset_files)
        asset_paths_by_reference.update(item_paths)
        warnings.extend(item_warnings)

    return DigiExamExamNetPdfAssetPreparation(
        asset_files=tuple(asset_files),
        asset_paths_by_reference=asset_paths_by_reference,
        warnings=tuple(warnings),
    )


def _prepare_item_assets(
    item: DigiExamIrItem,
) -> tuple[
    tuple[DigiExamExamNetPdfAssetFile, ...],
    dict[AssetReferenceKey, str],
    tuple[DigiExamExamNetPdfWarning, ...],
]:
    asset_files: list[DigiExamExamNetPdfAssetFile] = []
    paths: dict[AssetReferenceKey, str] = {}
    warnings: list[DigiExamExamNetPdfWarning] = []

    asset_by_id = {asset.asset_id: asset for asset in item.embedded_assets}
    path_by_asset_id: dict[str, str] = {}
    for asset in item.embedded_assets:
        asset_file = _asset_file(asset, item.item_id)
        if isinstance(asset_file, DigiExamExamNetPdfWarning):
            warnings.append(asset_file)
            continue
        asset_files.append(asset_file)
        path_by_asset_id[asset.asset_id] = asset_file.relative_path
        paths[(item.item_id, asset.source_image_index)] = asset_file.relative_path

    for reference in item.embedded_asset_references:
        referenced_asset = asset_by_id.get(reference.asset_id)
        if referenced_asset is None or reference.asset_id not in path_by_asset_id:
            warnings.append(_missing_reference_warning(item.item_id, reference.asset_id))
            continue
        if referenced_asset.source_image_index != reference.source_image_index:
            warnings.append(_missing_reference_warning(item.item_id, reference.asset_id))

    return tuple(asset_files), paths, tuple(warnings)


def _asset_file(
    asset: DigiExamEmbeddedAsset,
    item_id: str,
) -> DigiExamExamNetPdfAssetFile | DigiExamExamNetPdfWarning:
    if asset.content_base64 == "":
        return DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_MISSING,
            message=f"Embedded asset {asset.asset_id} has no renderable payload.",
            item_id=item_id,
        )

    try:
        payload = base64.b64decode(asset.content_base64, validate=True)
    except binascii.Error:
        return DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_INVALID,
            message=f"Embedded asset {asset.asset_id} payload is not valid base64.",
            item_id=item_id,
        )

    if len(payload) != asset.byte_length or hashlib.sha256(payload).hexdigest() != asset.sha256:
        return DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_INVALID,
            message=f"Embedded asset {asset.asset_id} payload does not match IR metadata.",
            item_id=item_id,
        )

    suffix = _SUPPORTED_ASSET_MEDIA_TYPES.get(asset.media_type)
    if suffix is None:
        return DigiExamExamNetPdfWarning(
            code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_PAYLOAD_INVALID,
            message=f"Embedded asset {asset.asset_id} uses unsupported media type.",
            item_id=item_id,
        )

    return DigiExamExamNetPdfAssetFile(
        asset_id=asset.asset_id,
        relative_path=f"assets/{asset.asset_id}{suffix}",
        media_type=asset.media_type,
        payload=payload,
    )


def _missing_reference_warning(item_id: str, asset_id: str) -> DigiExamExamNetPdfWarning:
    return DigiExamExamNetPdfWarning(
        code=DigiExamExamNetPdfWarningCode.EMBEDDED_ASSET_REFERENCE_MISSING,
        message=f"Embedded asset reference {asset_id} has no payload.",
        item_id=item_id,
    )
