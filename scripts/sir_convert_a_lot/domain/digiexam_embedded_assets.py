"""DigiExam embedded image asset extraction.

Purpose:
    Decode renderer-neutral embedded image assets from DigiExam `.dxe`
    `question.images[]` payloads and bind them to ordered `bodyHTML`
    `data-image-id` references.

Relationships:
    - Used by `domain.digiexam_dxe_parser` while constructing parser items.
    - Emits `domain.digiexam_contracts` asset value objects and typed warnings.
    - Feeds `domain.digiexam_ir_contracts` without coupling extraction to PDF,
      QTI, Exam.net, or any later renderer/import target.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.digiexam_contracts import (
    DigiExamEmbeddedAsset,
    DigiExamEmbeddedAssetReference,
    DigiExamSourceSpan,
    DigiExamWarning,
    DigiExamWarningCode,
)


@dataclass(frozen=True)
class DigiExamEmbeddedAssetParse:
    """Embedded asset parse result for one DigiExam item."""

    assets: tuple[DigiExamEmbeddedAsset, ...]
    references: tuple[DigiExamEmbeddedAssetReference, ...]
    warnings: tuple[DigiExamWarning, ...]


@dataclass(frozen=True)
class _ImageMetadata:
    media_type: str
    width_px: int
    height_px: int


_IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_DATA_IMAGE_ID_PATTERN = re.compile(
    r"\bdata-image-id\s*=\s*(['\"])(?P<image_id>[^'\"]+)\1",
    re.IGNORECASE,
)


def extract_digiexam_embedded_assets(
    *,
    image_values: object,
    prompt_html: str | None,
    item_sequence: int,
    source_span: DigiExamSourceSpan,
) -> DigiExamEmbeddedAssetParse:
    """Extract and bind `.dxe` embedded images for one item."""

    image_payloads = _image_payloads(image_values)
    if image_payloads is None:
        return DigiExamEmbeddedAssetParse(
            assets=(),
            references=(),
            warnings=(
                _warning(
                    DigiExamWarningCode.INVALID_EMBEDDED_ASSET_BASE64,
                    "DigiExam question.images must be an array of base64 image payloads.",
                    source_span,
                ),
            ),
        )
    references_by_index, reference_warnings = _body_html_references(
        prompt_html=prompt_html,
        image_count=len(image_payloads),
        source_span=source_span,
    )
    if not image_payloads:
        return DigiExamEmbeddedAssetParse(
            assets=(),
            references=(),
            warnings=reference_warnings,
        )

    warnings: list[DigiExamWarning] = []
    assets_by_index: dict[int, DigiExamEmbeddedAsset] = {}
    for image_index, payload in enumerate(image_payloads):
        decoded = _decode_base64(payload)
        if decoded is None:
            warnings.append(
                _warning(
                    DigiExamWarningCode.INVALID_EMBEDDED_ASSET_BASE64,
                    f"Embedded image {image_index} is not valid base64.",
                    source_span,
                )
            )
            continue
        metadata = _image_metadata(decoded)
        if metadata is None:
            warnings.append(
                _warning(
                    DigiExamWarningCode.UNSUPPORTED_EMBEDDED_ASSET_MEDIA,
                    f"Embedded image {image_index} is not a supported PNG or JPEG payload.",
                    source_span,
                )
            )
            continue
        digest = hashlib.sha256(decoded).hexdigest()
        assets_by_index[image_index] = DigiExamEmbeddedAsset(
            asset_id=f"item-{item_sequence:03d}-asset-{image_index + 1:03d}-{digest[:12]}",
            item_sequence=item_sequence,
            source_image_index=image_index,
            sha256=digest,
            media_type=metadata.media_type,
            content_base64=base64.b64encode(decoded).decode("ascii"),
            byte_length=len(decoded),
            width_px=metadata.width_px,
            height_px=metadata.height_px,
        )

    warnings.extend(reference_warnings)

    references: list[DigiExamEmbeddedAssetReference] = []
    for reference_order, image_index in enumerate(references_by_index, start=1):
        asset = assets_by_index.get(image_index)
        if asset is None:
            continue
        references.append(
            DigiExamEmbeddedAssetReference(
                asset_id=asset.asset_id,
                source_image_index=image_index,
                reference_order=reference_order,
            )
        )

    referenced_indexes = frozenset(references_by_index)
    for image_index in range(len(image_payloads)):
        if image_index not in referenced_indexes:
            warnings.append(
                _warning(
                    DigiExamWarningCode.UNUSED_EMBEDDED_ASSET_PAYLOAD,
                    f"Embedded image {image_index} is not referenced by bodyHTML.",
                    source_span,
                )
            )

    return DigiExamEmbeddedAssetParse(
        assets=tuple(assets_by_index[index] for index in sorted(assets_by_index)),
        references=tuple(references),
        warnings=tuple(warnings),
    )


def _image_payloads(value: object) -> tuple[str, ...] | None:
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, Sequence):
        return None
    payloads: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        payloads.append(item)
    return tuple(payloads)


def _decode_base64(payload: str) -> bytes | None:
    try:
        decoded = base64.b64decode(payload, validate=True)
    except binascii.Error:
        return None
    if not decoded:
        return None
    return decoded


def _image_metadata(payload: bytes) -> _ImageMetadata | None:
    if payload.startswith(b"\x89PNG\r\n\x1a\n") and len(payload) >= 24:
        width = int.from_bytes(payload[16:20], byteorder="big")
        height = int.from_bytes(payload[20:24], byteorder="big")
        if width > 0 and height > 0:
            return _ImageMetadata(media_type="image/png", width_px=width, height_px=height)
    if payload.startswith(b"\xff\xd8"):
        jpeg_size = _jpeg_size(payload)
        if jpeg_size is not None:
            width, height = jpeg_size
            return _ImageMetadata(media_type="image/jpeg", width_px=width, height_px=height)
    return None


def _jpeg_size(payload: bytes) -> tuple[int, int] | None:
    offset = 2
    while offset + 9 <= len(payload):
        if payload[offset] != 0xFF:
            return None
        marker = payload[offset + 1]
        offset += 2
        while marker == 0xFF and offset < len(payload):
            marker = payload[offset]
            offset += 1
        if marker in {0x01, *range(0xD0, 0xD9)}:
            continue
        if offset + 2 > len(payload):
            return None
        segment_length = int.from_bytes(payload[offset : offset + 2], byteorder="big")
        if segment_length < 2 or offset + segment_length > len(payload):
            return None
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            if segment_length < 7:
                return None
            height = int.from_bytes(payload[offset + 3 : offset + 5], byteorder="big")
            width = int.from_bytes(payload[offset + 5 : offset + 7], byteorder="big")
            if width > 0 and height > 0:
                return width, height
            return None
        offset += segment_length
    return None


def _body_html_references(
    *,
    prompt_html: str | None,
    image_count: int,
    source_span: DigiExamSourceSpan,
) -> tuple[tuple[int, ...], tuple[DigiExamWarning, ...]]:
    references: list[int] = []
    warnings: list[DigiExamWarning] = []
    if prompt_html is None:
        return (), ()

    for tag in _IMG_TAG_PATTERN.findall(prompt_html):
        matches = _DATA_IMAGE_ID_PATTERN.findall(tag)
        if len(matches) > 1:
            warnings.append(
                _warning(
                    DigiExamWarningCode.AMBIGUOUS_EMBEDDED_ASSET_BINDING,
                    "An embedded image tag contains multiple data-image-id bindings.",
                    source_span,
                )
            )
            continue
        if not matches:
            continue
        image_id = matches[0][1]
        if not image_id.isdecimal():
            warnings.append(
                _warning(
                    DigiExamWarningCode.AMBIGUOUS_EMBEDDED_ASSET_BINDING,
                    f"Embedded image reference '{image_id}' is not a non-negative integer.",
                    source_span,
                )
            )
            continue
        image_index = int(image_id)
        if image_index >= image_count:
            warnings.append(
                _warning(
                    DigiExamWarningCode.MISSING_EMBEDDED_ASSET_REFERENCE,
                    f"Embedded image reference {image_index} has no matching images[] payload.",
                    source_span,
                )
            )
            continue
        references.append(image_index)

    return tuple(references), tuple(warnings)


def _warning(
    code: DigiExamWarningCode,
    message: str,
    source_span: DigiExamSourceSpan,
) -> DigiExamWarning:
    return DigiExamWarning(
        code=code,
        message=message,
        blocking=True,
        source_span=source_span,
    )
