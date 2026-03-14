"""Data contracts for Qwen training-bundle materialization.

Purpose:
    Define the stable typed bundle-plan, bundle-summary, and precomputed
    reference-input contracts used during deterministic training-bundle
    materialization.

Relationships:
    - Imported by `ml.qwen.training.bundles` for the canonical public bundle API.
    - Imported by bundle state/precompute helpers for parsing and persistence.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import RowKey


@dataclass(frozen=True)
class BundleBatch:
    """Describe one bounded finalization unit for one manifest family."""

    manifest_family: ManifestFamily
    batch_index: int
    row_count: int
    first_row_key: RowKey
    last_row_key: RowKey


@dataclass(frozen=True)
class BundleBatchPlan:
    """Deterministic plan for one batched bundle finalization."""

    source_root: str
    output_root: str
    train_manifest_family: ManifestFamily
    eval_manifest_family: ManifestFamily
    tokenizer_model: str
    finalization_batch_row_count: int
    retained_row_count: int
    conflict_row_count: int
    owned_row_keys_path: str
    conflict_row_keys_path: str
    repo_head: str
    generated_at: str
    family_row_counts: dict[ManifestFamily, int]
    batches: list[BundleBatch]


@dataclass(frozen=True)
class BundlePrecomputedReferenceInputSummary:
    """Bundle-level summary of persisted precomputed reference inputs."""

    kind: str
    version: str
    source_field: str
    artifact_root: str
    artifact_count: int


@dataclass(frozen=True)
class BundleSummary:
    """Machine-readable summary for one deterministic training bundle."""

    source_root: str
    output_root: str
    train_manifest_family: ManifestFamily
    eval_manifest_family: ManifestFamily
    tokenizer_model: str
    retained_row_count: int
    conflict_row_count: int
    manifest_row_counts: dict[ManifestFamily, int]
    speaker_counts: dict[ManifestFamily, int]
    owned_row_keys_path: str
    conflict_row_keys_path: str
    repo_head: str
    generated_at: str
    finalization_batch_row_count: int
    total_batch_count: int
    batch_plan_path: str
    events_path: str
    status_path: str
    precomputed_reference_input: BundlePrecomputedReferenceInputSummary
