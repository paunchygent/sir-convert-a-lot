"""DigiExam source fingerprint helpers.

Purpose:
    Produce answer-key independent digests for DigiExam source IR items so
    teacher overlays and readiness reports can bind edits to parser-owned
    structure without trusting mutable downstream state.

Relationships:
    - Used by `domain.digiexam_ir_contracts` when building IR manifests.
    - Used by `domain.digiexam_ingestion_overlay` when validating overlays.
    - Used by `domain.digiexam_target_readiness` for item-addressable rows.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from enum import StrEnum

from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIrItem


def source_item_fingerprint(item: DigiExamIrItem) -> str:
    """Return a source-bound item fingerprint that excludes answer-key data."""

    payload = {
        "schema_version": "digiexam_source_item_fingerprint_v1",
        "item_id": item.item_id,
        "sequence": item.sequence,
        "title": item.title,
        "item_type": item.item_type.value,
        "source_span": _json_ready(asdict(item.source_span)),
        "prompt_html": item.prompt_html,
        "prompt_lines": _json_ready(item.prompt_lines),
        "max_score": item.max_score,
        "digiexam_type_code": item.digiexam_type_code,
        "options": _json_ready(item.options),
        "alternatives": _json_ready(
            tuple(asdict(alternative) for alternative in item.alternatives)
        ),
        "matching": _json_ready(asdict(item.matching)) if item.matching is not None else None,
        "gaps": _json_ready(tuple(asdict(gap) for gap in item.gaps)),
        "grading_policy": (
            _json_ready(asdict(item.grading_policy)) if item.grading_policy is not None else None
        ),
        "embedded_asset_references": _json_ready(
            tuple(asdict(reference) for reference in item.embedded_asset_references)
        ),
        "embedded_assets": _json_ready(
            tuple(
                {
                    "asset_id": asset.asset_id,
                    "source_image_index": asset.source_image_index,
                    "sha256": asset.sha256,
                    "media_type": asset.media_type,
                    "byte_length": asset.byte_length,
                    "width_px": asset.width_px,
                    "height_px": asset.height_px,
                }
                for asset in item.embedded_assets
            )
        ),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(child) for child in value]
    if isinstance(value, StrEnum):
        return value.value
    return value
