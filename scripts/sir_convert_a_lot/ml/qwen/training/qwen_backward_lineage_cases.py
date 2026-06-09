"""Case sequencing and report assembly for Qwen backward-lineage and fresh-start proof lane lineage
probes.

Purpose:
    Own the deterministic row/loss probe order, branch interaction summaries,
    and report-building logic for Qwen backward-lineage and fresh-start proof lane lineage work so
    execution modules do
    not duplicate task-specific bookkeeping.

Relationships:
    - Imported by `backward_lineage_probe.py` for in-container execution.
    - Imported by focused unit tests to lock the requested probe order and
      interaction classification before any Hemma run.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_contracts import (
    BackwardLineageProbeReport,
    BranchInteractionSummary,
    ProbeCaseResult,
    ProbeCaseSpec,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso


def parse_source_lines(raw_value: str) -> tuple[int, int]:
    """Parse the canonical two-line source tuple from one CLI string."""
    pieces = [piece.strip() for piece in raw_value.split(",") if piece.strip() != ""]
    if len(pieces) != 2:
        raise SystemExit("Backward-lineage probe requires exactly two source lines.")
    return int(pieces[0]), int(pieces[1])


def load_source_line_numbers(train_jsonl: Path, *, source_line_field: str) -> tuple[int, ...]:
    """Load preserved source-line numbers from one prepared mini-bundle manifest."""
    source_lines: list[int] = []
    with train_jsonl.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise SystemExit("Backward-lineage manifest row was not a JSON object.")
            source_line = payload.get(source_line_field)
            if not isinstance(source_line, int):
                raise SystemExit(
                    f"Backward-lineage manifest row was missing `{source_line_field}`."
                )
            source_lines.append(source_line)
    return tuple(source_lines)


def build_case_specs(source_line_numbers: tuple[int, int]) -> tuple[ProbeCaseSpec, ...]:
    """Return the fixed branch-ordered case sequence requested for Qwen backward-lineage and
    fresh-start proof lane.
    """
    first_line, second_line = source_line_numbers
    return (
        ProbeCaseSpec(
            case_id="pair-main-loss",
            loss_kind="main_loss",
            dataset_indices=(0, 1),
            source_line_numbers=(first_line, second_line),
        ),
        ProbeCaseSpec(
            case_id="pair-sub-talker-loss",
            loss_kind="sub_talker_loss",
            dataset_indices=(0, 1),
            source_line_numbers=(first_line, second_line),
        ),
        ProbeCaseSpec(
            case_id="pair-combined-loss",
            loss_kind="combined_loss",
            dataset_indices=(0, 1),
            source_line_numbers=(first_line, second_line),
        ),
        ProbeCaseSpec(
            case_id=f"line-{first_line}-main-loss",
            loss_kind="main_loss",
            dataset_indices=(0,),
            source_line_numbers=(first_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{second_line}-main-loss",
            loss_kind="main_loss",
            dataset_indices=(1,),
            source_line_numbers=(second_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{first_line}-sub-talker-loss",
            loss_kind="sub_talker_loss",
            dataset_indices=(0,),
            source_line_numbers=(first_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{second_line}-sub-talker-loss",
            loss_kind="sub_talker_loss",
            dataset_indices=(1,),
            source_line_numbers=(second_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{first_line}-combined-loss",
            loss_kind="combined_loss",
            dataset_indices=(0,),
            source_line_numbers=(first_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{second_line}-combined-loss",
            loss_kind="combined_loss",
            dataset_indices=(1,),
            source_line_numbers=(second_line,),
        ),
    )


def build_branch_summaries(
    cases: Sequence[ProbeCaseResult],
    source_line_numbers: tuple[int, int],
) -> tuple[BranchInteractionSummary, ...]:
    """Summarize pair-vs-single-row non-finite outcomes for each loss branch."""
    first_line, second_line = source_line_numbers
    summaries: list[BranchInteractionSummary] = []
    for loss_kind in ("main_loss", "sub_talker_loss", "combined_loss"):
        pair_case = _required_case(cases, f"pair-{loss_kind.replace('_', '-')}")
        first_case = _required_case(cases, f"line-{first_line}-{loss_kind.replace('_', '-')}")
        second_case = _required_case(cases, f"line-{second_line}-{loss_kind.replace('_', '-')}")
        pair_has_non_finite = _case_has_non_finite(pair_case)
        first_row_has_non_finite = _case_has_non_finite(first_case)
        second_row_has_non_finite = _case_has_non_finite(second_case)
        summaries.append(
            BranchInteractionSummary(
                loss_kind=loss_kind,
                pair_has_non_finite=pair_has_non_finite,
                first_row_has_non_finite=first_row_has_non_finite,
                second_row_has_non_finite=second_row_has_non_finite,
                interaction_mode=_interaction_mode(
                    pair_has_non_finite=pair_has_non_finite,
                    first_row_has_non_finite=first_row_has_non_finite,
                    second_row_has_non_finite=second_row_has_non_finite,
                ),
            )
        )
    return tuple(summaries)


def build_report(
    *,
    model_id: str,
    train_jsonl: Path,
    text_embedding_mask_policy: str,
    hook_profile: str,
    cases: Sequence[ProbeCaseResult],
    source_line_numbers: tuple[int, int],
) -> BackwardLineageProbeReport:
    """Build the machine-readable backward-lineage report."""
    return BackwardLineageProbeReport(
        generated_at=utc_now_iso(),
        model_id=model_id,
        train_jsonl=train_jsonl.as_posix(),
        text_embedding_mask_policy=text_embedding_mask_policy,
        hook_profile=hook_profile,
        source_line_numbers=source_line_numbers,
        cases=tuple(cases),
        branch_summaries=build_branch_summaries(cases, source_line_numbers),
    )


def _required_case(cases: Sequence[ProbeCaseResult], case_id: str) -> ProbeCaseResult:
    for case in cases:
        if case.case_id == case_id:
            return case
    raise SystemExit(f"Backward-lineage case result `{case_id}` was missing.")


def _case_has_non_finite(case: ProbeCaseResult) -> bool:
    if case.first_non_finite_hook_tensor is not None:
        return True
    gradient_rca_surface = case.gradient_rca.get("first_non_finite_surface")
    if isinstance(gradient_rca_surface, str):
        return True
    probe_surface = case.parameter_gradient_probes.get("first_non_finite_surface")
    return isinstance(probe_surface, str)


def _interaction_mode(
    *,
    pair_has_non_finite: bool,
    first_row_has_non_finite: bool,
    second_row_has_non_finite: bool,
) -> str:
    if not pair_has_non_finite and not first_row_has_non_finite and not second_row_has_non_finite:
        return "none"
    if pair_has_non_finite and not first_row_has_non_finite and not second_row_has_non_finite:
        return "pair_only"
    if first_row_has_non_finite and second_row_has_non_finite:
        return "both_rows"
    if first_row_has_non_finite:
        return "first_row_only"
    if second_row_has_non_finite:
        return "second_row_only"
    return "mixed"
