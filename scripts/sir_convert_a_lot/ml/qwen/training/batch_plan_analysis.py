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
from transformers import AutoTokenizer

from scripts.devops.qwen_finetuning_patches.sft_12hz_batch_occupancy import (
    BatchOccupancySummary,
    summarize_batch_occupancy,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import (
    BucketedBatchSampler,
    TrainingRowBatchMetrics,
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


def _tokenize_text(tokenizer: AutoTokenizer, text: str) -> torch.Tensor:
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
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
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
) -> BatchPlanExperimentResult:
    """Build one profile-specific occupancy result from resolved row metrics."""
    sampler = BucketedBatchSampler(row_metrics=row_metrics, policy=policy)
    summary = summarize_batch_occupancy(
        row_metrics=row_metrics,
        planned_batches=sampler.planned_batches(),
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
