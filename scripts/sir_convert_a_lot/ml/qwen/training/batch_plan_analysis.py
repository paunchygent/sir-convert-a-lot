"""Offline batch-plan analysis for Task 101 throughput experiments.

Purpose:
    Compute faithful Task 101 batch-occupancy comparisons for multiple
    throughput profiles without launching a live training run so bounded
    occupancy experiments can be promoted before Hemma GPU time is spent.

Relationships:
    - Runs inside the governed Qwen training image via the host-side
      `qwen-batch-plan` CLI.
    - Reuses the same prepared-manifest loader, throughput-profile contract,
      and bucketed sampler used by the live trainer.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import torch
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from scripts.devops.qwen_finetuning_patches.sft_12hz_batch_occupancy import (
    BatchOccupancySummary,
    summarize_batch_occupancy,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import (
    BucketedBatchSampler,
    TrainingRowBatchMetrics,
    bucket_signal_value,
)
from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    ThroughputBatchPolicy,
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)


class _ManifestRow(TypedDict):
    """Minimal prepared-manifest row surface needed for occupancy analysis."""

    text: str
    audio_codes: list[list[int]]


@dataclass(frozen=True)
class BatchPlanExperimentResult:
    """One profile-specific occupancy comparison result."""

    profile_label: str
    throughput_policy: dict[str, object]
    batch_occupancy: dict[str, object]
    singleton_batch_count: int
    singleton_batch_share: float
    two_row_batch_count: int
    two_row_batch_share: float
    quarantined_row_count: int
    maximum_row_codec_frames: int
    singleton_fit_audit: dict[str, object] | None = None

    def payload(self) -> dict[str, object]:
        """Return one JSON-safe payload for a profile-specific result."""
        return {
            "profile_label": self.profile_label,
            "throughput_policy": self.throughput_policy,
            "batch_occupancy": self.batch_occupancy,
            "singleton_batch_count": self.singleton_batch_count,
            "singleton_batch_share": self.singleton_batch_share,
            "two_row_batch_count": self.two_row_batch_count,
            "two_row_batch_share": self.two_row_batch_share,
            "quarantined_row_count": self.quarantined_row_count,
            "maximum_row_codec_frames": self.maximum_row_codec_frames,
            "singleton_fit_audit": self.singleton_fit_audit,
        }


@dataclass(frozen=True)
class SingletonFitOpportunityRecord:
    """One singleton-row audit record for fit-opportunity analysis."""

    row_index: int
    batch_index: int
    bucket_boundary: int
    text_token_count: int
    codec_frame_count: int
    later_same_bucket_fit_exists: bool
    adjacent_lower_bucket_fit_exists: bool

    def payload(self) -> dict[str, object]:
        """Return a JSON-safe payload for one singleton fit-opportunity record."""
        return {
            "row_index": self.row_index,
            "batch_index": self.batch_index,
            "bucket_boundary": self.bucket_boundary,
            "text_token_count": self.text_token_count,
            "codec_frame_count": self.codec_frame_count,
            "later_same_bucket_fit_exists": self.later_same_bucket_fit_exists,
            "adjacent_lower_bucket_fit_exists": self.adjacent_lower_bucket_fit_exists,
        }


@dataclass(frozen=True)
class SingletonFitAuditSummary:
    """Aggregate fit-opportunity evidence for singleton rows in one frame band."""

    codec_frame_band_min: int
    codec_frame_band_max: int
    audited_singleton_count: int
    same_bucket_fit_count: int
    adjacent_lower_bucket_fit_count: int
    same_bucket_only_count: int
    adjacent_lower_only_count: int
    both_fit_count: int
    neither_fit_count: int
    records: tuple[SingletonFitOpportunityRecord, ...]

    def payload(self) -> dict[str, object]:
        """Return a JSON-safe payload for one singleton fit audit summary."""
        return {
            "codec_frame_band_min": self.codec_frame_band_min,
            "codec_frame_band_max": self.codec_frame_band_max,
            "audited_singleton_count": self.audited_singleton_count,
            "same_bucket_fit_count": self.same_bucket_fit_count,
            "adjacent_lower_bucket_fit_count": self.adjacent_lower_bucket_fit_count,
            "same_bucket_only_count": self.same_bucket_only_count,
            "adjacent_lower_bucket_fit_count_only": self.adjacent_lower_only_count,
            "both_fit_count": self.both_fit_count,
            "neither_fit_count": self.neither_fit_count,
            "records": [record.payload() for record in self.records],
        }


def build_parser() -> argparse.ArgumentParser:
    """Build the committed parser for batch-plan analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze Task 101 batch occupancy for one or more throughput profiles."
    )
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--train-jsonl", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--fit-audit-codec-frame-band-min", type=int, default=None)
    parser.add_argument("--fit-audit-codec-frame-band-max", type=int, default=None)
    parser.add_argument(
        "--profile-label",
        action="append",
        dest="profile_labels",
        required=True,
        help="Repeat for each throughput profile that should be analyzed.",
    )
    return parser


def _assistant_text(text: str) -> str:
    """Render the same assistant-wrapped training prompt used by the live dataset."""
    return f"<|im_start|>assistant\n{text}<|im_end|>\n<|im_start|>assistant\n"


def _tokenize_text(tokenizer: PreTrainedTokenizerBase, text: str) -> torch.Tensor:
    """Tokenize one assistant prompt into a stable tensor shape."""
    encoded = tokenizer(text, return_tensors="pt", padding=True)
    input_ids = encoded["input_ids"]
    if not isinstance(input_ids, torch.Tensor):
        raise ValueError("Tokenizer did not return tensor input ids for batch-plan analysis.")
    return input_ids.unsqueeze(0) if input_ids.dim() == 1 else input_ids


def _load_manifest_rows(train_jsonl: Path) -> list[_ManifestRow]:
    """Load only the manifest fields needed for occupancy analysis."""
    rows: list[_ManifestRow] = []
    with train_jsonl.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("Expected each prepared manifest row to be a JSON object.")
            text = payload.get("text")
            audio_codes = payload.get("audio_codes")
            if not isinstance(text, str):
                raise ValueError("Prepared manifest row lacked a valid `text` value.")
            if not isinstance(audio_codes, list):
                raise ValueError("Prepared manifest row lacked a valid `audio_codes` value.")
            rows.append(
                _ManifestRow(
                    text=text,
                    audio_codes=audio_codes,
                )
            )
    if len(rows) == 0:
        raise ValueError("Prepared manifest did not contain any rows for occupancy analysis.")
    return rows


def build_row_metrics(*, train_jsonl: Path, model_id: str) -> list[TrainingRowBatchMetrics]:
    """Build faithful row metrics from one prepared manifest and model tokenizer."""
    tokenizer: PreTrainedTokenizerBase = AutoTokenizer.from_pretrained(
        model_id,
        trust_remote_code=True,
    )
    rows = _load_manifest_rows(train_jsonl)
    row_metrics: list[TrainingRowBatchMetrics] = []
    for row in rows:
        text_ids = _tokenize_text(tokenizer, _assistant_text(row["text"]))
        row_metrics.append(
            TrainingRowBatchMetrics(
                text_token_count=int(text_ids[:, :-5].shape[1]),
                codec_frame_count=len(row["audio_codes"]),
            )
        )
    return row_metrics


def build_experiment_result(
    *,
    row_metrics: list[TrainingRowBatchMetrics],
    policy: ThroughputBatchPolicy,
    fit_audit_codec_frame_band_min: int | None = None,
    fit_audit_codec_frame_band_max: int | None = None,
) -> BatchPlanExperimentResult:
    """Build one profile-specific occupancy result from resolved row metrics."""
    sampler = BucketedBatchSampler(row_metrics=row_metrics, policy=policy)
    summary = summarize_batch_occupancy(
        row_metrics=row_metrics,
        planned_batches=sampler.planned_batches(),
    )
    fit_audit = build_singleton_fit_audit(
        row_metrics=row_metrics,
        policy=policy,
        planned_batches=sampler.planned_batches(),
        codec_frame_band_min=fit_audit_codec_frame_band_min,
        codec_frame_band_max=fit_audit_codec_frame_band_max,
    )
    return BatchPlanExperimentResult(
        profile_label=policy.profile_label,
        throughput_policy=throughput_policy_payload(
            policy,
            batch_occupancy=summary.payload(),
        ),
        batch_occupancy=summary.payload(),
        singleton_batch_count=summary.batch_size_histogram.get(1, 0),
        singleton_batch_share=_batch_share(summary, row_count=1),
        two_row_batch_count=summary.batch_size_histogram.get(2, 0),
        two_row_batch_share=_batch_share(summary, row_count=2),
        quarantined_row_count=_quarantined_row_count(row_metrics=row_metrics, policy=policy),
        maximum_row_codec_frames=max(metric.codec_frame_count for metric in row_metrics),
        singleton_fit_audit=None if fit_audit is None else fit_audit.payload(),
    )


def _batch_share(summary: BatchOccupancySummary, *, row_count: int) -> float:
    """Return the share of planned batches at one row-count size."""
    batch_count = summary.batch_size_histogram.get(row_count, 0)
    return float(batch_count) / float(summary.total_batches)


def _quarantined_row_count(
    *,
    row_metrics: list[TrainingRowBatchMetrics],
    policy: ThroughputBatchPolicy,
) -> int:
    """Return the number of rows that would be forced singleton by the policy."""
    threshold = policy.long_row_singleton_codec_frame_threshold
    if threshold is None:
        return 0
    return sum(1 for metric in row_metrics if metric.codec_frame_count >= threshold)


def _bucket_boundary(
    *,
    metrics: TrainingRowBatchMetrics,
    policy: ThroughputBatchPolicy,
) -> int:
    """Return the policy bucket boundary for one row under the active signal."""
    bucket_value = bucket_signal_value(metrics=metrics, policy=policy)
    for boundary in policy.length_bucket_boundaries:
        if bucket_value <= boundary:
            return boundary
    return policy.length_bucket_boundaries[-1] + 1


def _ordered_bucket_indices(
    *,
    row_metrics: list[TrainingRowBatchMetrics],
    policy: ThroughputBatchPolicy,
) -> dict[int, list[int]]:
    """Return the stable ordered row indices for each non-quarantined bucket."""
    buckets: dict[int, list[int]] = {}
    quarantine_threshold = policy.long_row_singleton_codec_frame_threshold
    for row_index, metrics in enumerate(row_metrics):
        if quarantine_threshold is not None and metrics.codec_frame_count >= quarantine_threshold:
            continue
        boundary = _bucket_boundary(
            metrics=metrics,
            policy=policy,
        )
        buckets.setdefault(boundary, []).append(row_index)
    return {
        boundary: sorted(
            indices,
            key=lambda current_index: (
                row_metrics[current_index].codec_frame_count,
                row_metrics[current_index].text_token_count,
            ),
            reverse=True,
        )
        for boundary, indices in buckets.items()
    }


def _rows_fit_together(
    *,
    left_metrics: TrainingRowBatchMetrics,
    right_metrics: TrainingRowBatchMetrics,
    policy: ThroughputBatchPolicy,
) -> bool:
    """Return whether two rows fit together under the unchanged live caps."""
    if policy.max_batch_size < 2:
        return False
    if left_metrics.text_token_count + right_metrics.text_token_count > policy.max_tokens_per_batch:
        return False
    if (
        left_metrics.codec_frame_count + right_metrics.codec_frame_count
        > policy.max_codec_frames_per_batch
    ):
        return False
    return True


def build_singleton_fit_audit(
    *,
    row_metrics: list[TrainingRowBatchMetrics],
    policy: ThroughputBatchPolicy,
    planned_batches: list[list[int]],
    codec_frame_band_min: int | None,
    codec_frame_band_max: int | None,
) -> SingletonFitAuditSummary | None:
    """Audit fit opportunities for singleton rows in one codec-frame band."""
    if codec_frame_band_min is None and codec_frame_band_max is None:
        return None
    if codec_frame_band_min is None or codec_frame_band_max is None:
        raise ValueError("Singleton fit audit requires both codec-frame band bounds when enabled.")
    if codec_frame_band_min > codec_frame_band_max:
        raise ValueError("Singleton fit audit requires band min <= band max.")

    batch_index_by_row: dict[int, int] = {}
    for batch_index, batch in enumerate(planned_batches):
        for row_index in batch:
            batch_index_by_row[row_index] = batch_index

    ordered_bucket_indices = _ordered_bucket_indices(
        row_metrics=row_metrics,
        policy=policy,
    )
    boundary_order = sorted(ordered_bucket_indices)
    lower_boundary_by_boundary = {
        boundary_order[current_index]: (
            None if current_index == 0 else boundary_order[current_index - 1]
        )
        for current_index in range(len(boundary_order))
    }
    position_in_bucket: dict[int, tuple[int, int]] = {}
    for boundary, ordered_indices in ordered_bucket_indices.items():
        for current_index, row_index in enumerate(ordered_indices):
            position_in_bucket[row_index] = (boundary, current_index)

    records: list[SingletonFitOpportunityRecord] = []
    for batch in planned_batches:
        if len(batch) != 1:
            continue
        row_index = batch[0]
        metrics = row_metrics[row_index]
        if metrics.codec_frame_count < codec_frame_band_min:
            continue
        if metrics.codec_frame_count > codec_frame_band_max:
            continue
        bucket_position = position_in_bucket.get(row_index)
        if bucket_position is None:
            continue
        boundary, current_position = bucket_position
        same_bucket_candidates = ordered_bucket_indices[boundary][current_position + 1 :]
        lower_boundary = lower_boundary_by_boundary[boundary]
        lower_bucket_candidates = (
            [] if lower_boundary is None else ordered_bucket_indices.get(lower_boundary, [])
        )
        later_same_bucket_fit_exists = any(
            _rows_fit_together(
                left_metrics=metrics,
                right_metrics=row_metrics[candidate_index],
                policy=policy,
            )
            for candidate_index in same_bucket_candidates
        )
        adjacent_lower_bucket_fit_exists = any(
            _rows_fit_together(
                left_metrics=metrics,
                right_metrics=row_metrics[candidate_index],
                policy=policy,
            )
            for candidate_index in lower_bucket_candidates
        )
        records.append(
            SingletonFitOpportunityRecord(
                row_index=row_index,
                batch_index=batch_index_by_row[row_index],
                bucket_boundary=boundary,
                text_token_count=metrics.text_token_count,
                codec_frame_count=metrics.codec_frame_count,
                later_same_bucket_fit_exists=later_same_bucket_fit_exists,
                adjacent_lower_bucket_fit_exists=adjacent_lower_bucket_fit_exists,
            )
        )

    same_bucket_fit_count = sum(1 for record in records if record.later_same_bucket_fit_exists)
    adjacent_lower_bucket_fit_count = sum(
        1 for record in records if record.adjacent_lower_bucket_fit_exists
    )
    same_bucket_only_count = sum(
        1
        for record in records
        if record.later_same_bucket_fit_exists and not record.adjacent_lower_bucket_fit_exists
    )
    adjacent_lower_only_count = sum(
        1
        for record in records
        if record.adjacent_lower_bucket_fit_exists and not record.later_same_bucket_fit_exists
    )
    both_fit_count = sum(
        1
        for record in records
        if record.later_same_bucket_fit_exists and record.adjacent_lower_bucket_fit_exists
    )
    neither_fit_count = sum(
        1
        for record in records
        if not record.later_same_bucket_fit_exists and not record.adjacent_lower_bucket_fit_exists
    )
    return SingletonFitAuditSummary(
        codec_frame_band_min=codec_frame_band_min,
        codec_frame_band_max=codec_frame_band_max,
        audited_singleton_count=len(records),
        same_bucket_fit_count=same_bucket_fit_count,
        adjacent_lower_bucket_fit_count=adjacent_lower_bucket_fit_count,
        same_bucket_only_count=same_bucket_only_count,
        adjacent_lower_only_count=adjacent_lower_only_count,
        both_fit_count=both_fit_count,
        neither_fit_count=neither_fit_count,
        records=tuple(records),
    )


def _report_payload(
    *,
    train_jsonl: Path,
    model_id: str,
    batch_size: int,
    results: list[BatchPlanExperimentResult],
) -> dict[str, object]:
    """Build the JSON payload for one batch-plan analysis report."""
    return {
        "train_jsonl": train_jsonl.as_posix(),
        "model_id": model_id,
        "batch_size": batch_size,
        "profiles": [result.payload() for result in results],
    }


def _report_markdown(
    *,
    train_jsonl: Path,
    model_id: str,
    batch_size: int,
    results: list[BatchPlanExperimentResult],
) -> str:
    """Render one concise Markdown summary for the batch-plan analysis."""
    lines = [
        "# Task 172 Batch Plan Analysis",
        "",
        f"- train_jsonl: `{train_jsonl.as_posix()}`",
        f"- model_id: `{model_id}`",
        f"- batch_size: `{batch_size}`",
        "",
        (
            "| Profile | Mean batch size | Singleton share | Two-row share | "
            "Peak batch frames | Quarantined rows |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        occupancy = result.batch_occupancy
        lines.append(
            "| "
            f"`{result.profile_label}` | "
            f"{occupancy['mean_batch_size']:.3f} | "
            f"{result.singleton_batch_share:.3f} | "
            f"{result.two_row_batch_share:.3f} | "
            f"{occupancy['peak_codec_frames_per_batch']} | "
            f"{result.quarantined_row_count} |"
        )
        fit_audit = result.singleton_fit_audit
        if isinstance(fit_audit, dict):
            lines.extend(
                [
                    "",
                    (
                        f"- `{result.profile_label}` singleton fit audit "
                        f"[{fit_audit['codec_frame_band_min']}, "
                        f"{fit_audit['codec_frame_band_max']}]"
                    ),
                    f"  - audited_singleton_count: `{fit_audit['audited_singleton_count']}`",
                    f"  - same_bucket_fit_count: `{fit_audit['same_bucket_fit_count']}`",
                    (
                        "  - adjacent_lower_bucket_fit_count: "
                        f"`{fit_audit['adjacent_lower_bucket_fit_count']}`"
                    ),
                    f"  - same_bucket_only_count: `{fit_audit['same_bucket_only_count']}`",
                    (
                        "  - adjacent_lower_only_count: "
                        f"`{fit_audit['adjacent_lower_bucket_fit_count_only']}`"
                    ),
                    f"  - both_fit_count: `{fit_audit['both_fit_count']}`",
                    f"  - neither_fit_count: `{fit_audit['neither_fit_count']}`",
                ]
            )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON report with deterministic formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one Markdown report deterministically."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Analyze one prepared manifest against multiple throughput profiles."""
    parser = build_parser()
    args = parser.parse_args(argv)
    row_metrics = build_row_metrics(
        train_jsonl=Path(args.train_jsonl),
        model_id=str(args.model_id),
    )
    results = [
        build_experiment_result(
            row_metrics=row_metrics,
            policy=resolve_throughput_batch_policy(
                profile_label=profile_label,
                max_batch_size=int(args.batch_size),
            ),
            fit_audit_codec_frame_band_min=args.fit_audit_codec_frame_band_min,
            fit_audit_codec_frame_band_max=args.fit_audit_codec_frame_band_max,
        )
        for profile_label in list(args.profile_labels)
    ]
    report_payload = _report_payload(
        train_jsonl=Path(args.train_jsonl),
        model_id=str(args.model_id),
        batch_size=int(args.batch_size),
        results=results,
    )
    report_markdown = _report_markdown(
        train_jsonl=Path(args.train_jsonl),
        model_id=str(args.model_id),
        batch_size=int(args.batch_size),
        results=results,
    )
    _write_json(Path(args.output_json), report_payload)
    _write_markdown(Path(args.output_md), report_markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
