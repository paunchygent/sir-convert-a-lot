"""Contracts for the Story 31 talker-core stability lab.

Purpose:
    Keep the lightweight exploration-lane settings and compact result-table
    payloads in one small shared module so the Story 31 runner and CLI stay
    focused on orchestration rather than bookkeeping.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for execution and artifact
      rendering.
    - Imported by tests that lock the compact matrix table and variant parsing
      behavior before any Hemma probe is launched.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Story31StabilityLabSettings:
    """Configuration for one attached Story 31 stability-lab matrix run."""

    output_root: Path
    dockerfile_path: Path
    image: str
    model_id: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    output_root_home_mount_base: Path
    source_bundle_root: Path
    manifest_family: str
    source_lines: tuple[int, int]
    text_embedding_mask_policy: str
    hook_profile: str
    stabilization_variants: tuple[str, ...]
    build_image: bool


@dataclass(frozen=True)
class StabilityLabMatrixRow:
    """Compact comparable result row for one variant/case combination."""

    stabilization_variant: str
    case_id: str
    loss_kind: str
    source_line_numbers: tuple[int, ...]
    batch_size: int
    interaction_mode: str
    case_has_non_finite: bool
    first_non_finite_hook_tensor: str | None
    first_non_finite_talker_core_hook_tensor: str | None
    gradient_rca_first_non_finite_surface: str | None
    parameter_first_non_finite_surface: str | None
    anomaly_operator: str | None


@dataclass(frozen=True)
class SubBoundaryComparisonRow:
    """Comparable pair-versus-single row outcome for one T229 sub-boundary case."""

    case_id: str
    source_line_numbers: tuple[int, ...]
    batch_size: int
    role: str
    case_has_non_finite: bool
    first_non_finite_talker_core_hook_tensor: str | None
    matched_sub_boundary: str | None


@dataclass(frozen=True)
class Story31SubBoundaryAssessment:
    """Focused T229 assessment for the shifted post-T219 handoff seam."""

    stabilization_variant: str
    target_loss_kind: str
    target_sub_boundaries: tuple[str, ...]
    comparison_rows: tuple[SubBoundaryComparisonRow, ...]
    earliest_sub_boundary: str | None
    evidence_is_ambiguous: bool
    ambiguity_reason: str | None
    next_micro_family_rule: str


@dataclass(frozen=True)
class InputLayernormInternalComparisonRow:
    """Comparable pair-versus-single row outcome for one T233 internal case."""

    case_id: str
    source_line_numbers: tuple[int, ...]
    batch_size: int
    role: str
    case_has_non_finite: bool
    first_non_finite_talker_core_hook_tensor: str | None
    matched_internal_surface: str | None


@dataclass(frozen=True)
class Story31InputLayernormInternalAssessment:
    """Focused T233 assessment for the internal layer-16 input-layernorm seam."""

    stabilization_variant: str
    target_loss_kind: str
    target_internal_surfaces: tuple[str, ...]
    comparison_rows: tuple[InputLayernormInternalComparisonRow, ...]
    earliest_internal_surface: str | None
    evidence_is_ambiguous: bool
    ambiguity_reason: str | None
    next_micro_family_rule: str


@dataclass(frozen=True)
class PostT234DisagreementComparisonRow:
    """Comparable pair-versus-single row outcome for one T235 disagreement case."""

    case_id: str
    source_line_numbers: tuple[int, ...]
    batch_size: int
    role: str
    case_has_non_finite: bool
    first_non_finite_talker_core_hook_tensor: str | None
    matched_corridor_surface: str | None


@dataclass(frozen=True)
class Story31PostT234DisagreementAssessment:
    """Focused T235 assessment for the mixed post-T234 sub-talker corridor."""

    stabilization_variant: str
    target_loss_kind: str
    target_corridor_surfaces: tuple[str, ...]
    comparison_rows: tuple[PostT234DisagreementComparisonRow, ...]
    earliest_corridor_surface: str | None
    evidence_is_ambiguous: bool
    ambiguity_reason: str | None
    next_micro_family_rule: str


@dataclass(frozen=True)
class PostT235RowLocalOutlierComparisonRow:
    """Comparable pair-versus-single row outcome for one T236 outlier case."""

    case_id: str
    source_line_numbers: tuple[int, ...]
    batch_size: int
    role: str
    case_has_non_finite: bool
    first_non_finite_talker_core_hook_tensor: str | None
    matched_outlier_surface: str | None


@dataclass(frozen=True)
class Story31PostT235RowLocalOutlierAssessment:
    """Focused T236 assessment for the repeatable post-T235 line-4 outlier."""

    stabilization_variant: str
    target_loss_kind: str
    target_outlier_surfaces: tuple[str, ...]
    comparison_rows: tuple[PostT235RowLocalOutlierComparisonRow, ...]
    outlier_classification: str | None
    dominant_surface: str | None
    evidence_is_ambiguous: bool
    ambiguity_reason: str | None
    next_micro_family_rule: str


@dataclass(frozen=True)
class Story31StabilityLabReport:
    """Machine-readable report for one Story 31 matrix run."""

    generated_at: str
    image: str
    image_id: str
    build_performed: bool
    model_id: str
    source_bundle_root: str
    manifest_family: str
    source_line_numbers: tuple[int, int]
    text_embedding_mask_policy: str
    hook_profile: str
    stabilization_variants: tuple[str, ...]
    mini_bundle: dict[str, object]
    hf_cache_dir: str
    effective_hf_cache_dir: str
    used_home_mount: bool
    effective_output_root: str
    used_output_root_home_mount: bool
    variant_report_paths: dict[str, str]
    probe_commands: dict[str, list[str]]
    matrix_rows: tuple[StabilityLabMatrixRow, ...]
    sub_boundary_assessment: Story31SubBoundaryAssessment | None
    input_layernorm_internal_assessment: Story31InputLayernormInternalAssessment | None
    post_t234_disagreement_assessment: Story31PostT234DisagreementAssessment | None = None
    post_t235_row_local_outlier_assessment: Story31PostT235RowLocalOutlierAssessment | None = None


@dataclass(frozen=True)
class PromotionGateCaseAssessment:
    """One exact-case comparison between baseline failure and candidate behavior."""

    case_id: str
    loss_kind: str
    expected_talker_core_hook: str
    baseline_case_has_non_finite: bool
    baseline_exact_family_match: bool
    candidate_case_has_non_finite: bool
    candidate_exact_surfaces_finite: bool
    passes: bool


@dataclass(frozen=True)
class Story31PromotionGateReport:
    """Compact promotion decision for one Story 31 candidate variant."""

    generated_at: str
    results_path: str
    required_hook_profile: str
    actual_hook_profile: str
    required_text_embedding_mask_policy: str
    actual_text_embedding_mask_policy: str
    baseline_variant: str
    candidate_variant: str
    required_case_ids: tuple[str, ...]
    exact_family_reproduced_by_baseline: bool
    candidate_exact_surfaces_finite: bool
    promotion_passed: bool
    case_assessments: tuple[PromotionGateCaseAssessment, ...]
