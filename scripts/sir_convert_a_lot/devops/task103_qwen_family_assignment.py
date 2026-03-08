"""Manifest-family assignment helpers for the Task 103 Qwen corpus pipeline.

Purpose:
    Centralize the mapping from dataset-native source rows to canonical Qwen
    manifest families so adapters do not hardcode repo manifest ownership.

Relationships:
    - Consumed by `task103_qwen_preprocessing_core.py` during curation.
    - Uses `SourceRecord` from `task103_qwen_source_models.py`.
"""

from __future__ import annotations

from typing import Literal

from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import SourceRecord

ManifestFamily = Literal[
    "swedish_smoke_train",
    "swedish_pilot_train",
    "swedish_scaleup_train",
    "swedish_checkpoint_dev",
    "swedish_final_test",
    "swedish_waxholm_control",
]


def manifest_target_for_source(source_record: SourceRecord) -> ManifestFamily | None:
    """Map one source record to the canonical manifest family, when available."""
    if source_record.dataset == "repo_fixture_sv":
        return "swedish_smoke_train"
    if source_record.dataset == "fleurs_sv_se":
        fleurs_mapping: dict[str, ManifestFamily] = {
            "dev": "swedish_checkpoint_dev",
            "test": "swedish_final_test",
        }
        return fleurs_mapping.get(source_record.source_split)
    if source_record.dataset == "waxholm":
        return "swedish_waxholm_control"
    if source_record.dataset == "rixvox":
        rixvox_mapping: dict[str, ManifestFamily] = {
            "dev": "swedish_checkpoint_dev",
            "validation": "swedish_checkpoint_dev",
            "test": "swedish_final_test",
        }
        return rixvox_mapping.get(source_record.source_split)
    return None


def manifest_targets_for_curated_source(
    source_record: SourceRecord,
    *,
    quality_tier: str,
    speaker_quality_gate: str,
) -> tuple[ManifestFamily, ...]:
    """Map one curated source row into one or more canonical manifest families."""
    direct_target = manifest_target_for_source(source_record)
    if direct_target is not None:
        return (direct_target,)
    if source_record.dataset != "rixvox" or source_record.source_split != "train":
        return ()
    if speaker_quality_gate != "speaker_from_id":
        return ()
    if quality_tier == "high_trust":
        return (
            "swedish_smoke_train",
            "swedish_pilot_train",
            "swedish_scaleup_train",
        )
    if quality_tier == "medium_trust":
        return ("swedish_scaleup_train",)
    return ()
