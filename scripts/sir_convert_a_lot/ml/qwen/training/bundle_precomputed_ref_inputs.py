"""Precomputed reference-input helpers for Qwen training bundles.

Purpose:
    Materialize deterministic bundle-owned ref-mel artifacts and expose their
    path and summary contracts for Qwen pilot training training.

Relationships:
    - Imported by `ml.qwen.training.bundles` during bundle preparation/finalization.
    - Reuses canonical ref-mel extraction from `sft_12hz_ref_inputs.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_inputs import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_SOURCE_FIELD,
    PRECOMPUTED_REF_INPUT_VERSION,
    extract_ref_mel_from_audio_path,
    save_persisted_ref_mel,
)
from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import iter_spool_rows, write_json
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_contracts import (
    BundlePrecomputedReferenceInputSummary,
)

_PRECOMPUTED_REF_ROOT = Path("precomputed") / PRECOMPUTED_REF_INPUT_KIND


def precomputed_ref_input_root(output_root: Path) -> Path:
    """Return the bundle-local root that holds precomputed reference inputs."""
    return output_root / _PRECOMPUTED_REF_ROOT


def precomputed_ref_input_relative_path(
    *,
    manifest_family: ManifestFamily,
    speaker_id: str,
) -> Path:
    """Return the canonical relative path for one family-speaker ref-mel artifact."""
    return _PRECOMPUTED_REF_ROOT / manifest_family / speaker_id / "ref_mel.pt"


def precomputed_ref_input_metadata_relative_path(
    *,
    manifest_family: ManifestFamily,
    speaker_id: str,
) -> Path:
    """Return the metadata path for one family-speaker ref-mel artifact."""
    return _PRECOMPUTED_REF_ROOT / manifest_family / speaker_id / "ref_mel.metadata.json"


def materialize_precomputed_reference_inputs(
    output_root: Path,
    *,
    manifest_families: tuple[ManifestFamily, ...],
) -> BundlePrecomputedReferenceInputSummary:
    """Persist bundle-owned ref-mel artifacts for each selected family-speaker anchor."""
    artifact_count = 0
    seen_speakers: set[tuple[ManifestFamily, str]] = set()
    for spool_row in iter_spool_rows(output_root):
        for manifest_family in spool_row.manifest_targets:
            if manifest_family not in manifest_families:
                continue
            speaker_key = (manifest_family, spool_row.speaker_id)
            if speaker_key in seen_speakers:
                continue
            seen_speakers.add(speaker_key)
            source_ref_audio_path = (
                output_root / spool_row.reference_audio_24k_paths[manifest_family]
            )
            artifact_relative_path = precomputed_ref_input_relative_path(
                manifest_family=manifest_family,
                speaker_id=spool_row.speaker_id,
            )
            artifact_path = output_root / artifact_relative_path
            metadata_relative_path = precomputed_ref_input_metadata_relative_path(
                manifest_family=manifest_family,
                speaker_id=spool_row.speaker_id,
            )
            metadata_path = output_root / metadata_relative_path
            if not artifact_path.exists():
                ref_mel = extract_ref_mel_from_audio_path(source_ref_audio_path)
                save_persisted_ref_mel(artifact_path, ref_mel)
            write_json(
                metadata_path,
                {
                    "kind": PRECOMPUTED_REF_INPUT_KIND,
                    "version": PRECOMPUTED_REF_INPUT_VERSION,
                    "source_field": PRECOMPUTED_REF_INPUT_SOURCE_FIELD,
                    "source_ref_audio": spool_row.reference_audio_24k_paths[manifest_family],
                    "artifact_path": artifact_relative_path.as_posix(),
                    "speaker_id": spool_row.speaker_id,
                    "manifest_family": manifest_family,
                },
            )
            artifact_count += 1
    return BundlePrecomputedReferenceInputSummary(
        kind=PRECOMPUTED_REF_INPUT_KIND,
        version=PRECOMPUTED_REF_INPUT_VERSION,
        source_field=PRECOMPUTED_REF_INPUT_SOURCE_FIELD,
        artifact_root=precomputed_ref_input_root(output_root).relative_to(output_root).as_posix(),
        artifact_count=artifact_count,
    )


def load_precomputed_reference_input_summary(
    output_root: Path,
) -> BundlePrecomputedReferenceInputSummary:
    """Load the canonical precomputed-reference summary by scanning persisted metadata."""
    metadata_paths = sorted(
        precomputed_ref_input_root(output_root).glob("*/*/ref_mel.metadata.json")
    )
    for metadata_path in metadata_paths:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(
                f"Precomputed reference metadata `{metadata_path.as_posix()}` was malformed."
            )
        return BundlePrecomputedReferenceInputSummary(
            kind=_required_str(payload, "kind", metadata_path),
            version=_required_str(payload, "version", metadata_path),
            source_field=_required_str(payload, "source_field", metadata_path),
            artifact_root=precomputed_ref_input_root(output_root)
            .relative_to(output_root)
            .as_posix(),
            artifact_count=len(metadata_paths),
        )
    raise FileNotFoundError(
        "Training bundle did not contain any precomputed reference-input metadata under "
        f"`{precomputed_ref_input_root(output_root).as_posix()}`."
    )


def _required_str(payload: dict[str, object], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(
            f"Precomputed reference metadata `{path.as_posix()}` lacked string `{key}`."
        )
    return value
