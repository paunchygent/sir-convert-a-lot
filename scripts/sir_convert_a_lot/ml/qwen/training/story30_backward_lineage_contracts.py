"""Contracts for Story 30 backward-lineage and talker-core probes.

Purpose:
    Keep the probe result shapes, case specifications, and machine-readable
    report payloads in one small shared module so the orchestration code stays
    focused on execution rather than payload bookkeeping.

Relationships:
    - Imported by `backward_lineage_probe.py` for in-container execution.
    - Imported by `story30_backward_lineage_cases.py` for branch summaries and
      report assembly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeCaseSpec:
    """One deterministic loss and row-selection case for the lineage probe."""

    case_id: str
    loss_kind: str
    dataset_indices: tuple[int, ...]
    source_line_numbers: tuple[int, ...]


@dataclass(frozen=True)
class TensorGradientObservation:
    """One gradient-hook observation for an instrumented tensor."""

    tensor_name: str
    hook_order: int
    is_finite: bool
    nan_count: int
    inf_count: int
    max_abs: float | None


@dataclass(frozen=True)
class FirstNonFiniteHookObservation:
    """Earliest matching non-finite gradient hook for one backward pass."""

    tensor_name: str | None
    hook_order: int | None


@dataclass(frozen=True)
class ProbeCaseResult:
    """Result payload for one deterministic probe case."""

    case_id: str
    loss_kind: str
    source_line_numbers: tuple[int, ...]
    batch_size: int
    loss_value: float
    main_loss_value: float
    sub_talker_loss_value: float
    first_non_finite_hook_tensor: str | None
    first_non_finite_hook_order: int | None
    first_non_finite_talker_core_hook_tensor: str | None
    first_non_finite_talker_core_hook_order: int | None
    hooked_tensor_gradients: tuple[TensorGradientObservation, ...]
    gradient_rca: dict[str, object]
    parameter_gradient_probes: dict[str, object]
    anomaly_trace: str | None
    batch_provenance: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class BranchInteractionSummary:
    """Pair-versus-row interaction summary for one loss branch."""

    loss_kind: str
    pair_has_non_finite: bool
    first_row_has_non_finite: bool
    second_row_has_non_finite: bool
    interaction_mode: str


@dataclass(frozen=True)
class BackwardLineageProbeReport:
    """Machine-readable report for one backward-lineage probe run."""

    generated_at: str
    model_id: str
    train_jsonl: str
    text_embedding_mask_policy: str
    hook_profile: str
    source_line_numbers: tuple[int, int]
    cases: tuple[ProbeCaseResult, ...]
    branch_summaries: tuple[BranchInteractionSummary, ...]
