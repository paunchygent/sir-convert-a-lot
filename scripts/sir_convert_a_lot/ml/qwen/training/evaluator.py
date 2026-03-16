"""In-container standalone checkpoint eval entrypoint for Qwen fine-tuning.

Purpose:
    Restore one durable Qwen checkpoint inside the governed training image,
    execute a real held-out evaluation pass, and persist deterministic eval
    artifacts without entering the training loop.

Relationships:
    - Executed inside the shared Qwen runtime image by host-side eval and
      schedule orchestration.
    - Delegates core model/dataloader bootstrap to the patched `sft_12hz.py`
      standalone-eval helpers.
    - Reuses shared report-writing helpers from the
      `ml.qwen.training.reporting` package.
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import sft_12hz
import torch

from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    load_optional_training_bundle_summary,
)
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import add_boolean_argument
from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    GRADIENT_ACCUMULATION_STEP_CHOICES,
    resolve_gradient_accumulation_steps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import StandaloneEvalReport
from scripts.sir_convert_a_lot.ml.qwen.training.reporting import write_json
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    TEXT_EMBEDDING_MASK_POLICY_CHOICES,
    TextEmbeddingMaskPolicy,
    resolve_text_embedding_mask_policy,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _count_jsonl_rows(path: Path) -> int:
    """Return the number of non-empty rows in one JSONL file."""
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the standalone in-container eval entrypoint."""
    parser = argparse.ArgumentParser(description="Run standalone Qwen checkpoint eval.")
    parser.add_argument("--model-id", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--eval-jsonl", type=Path, required=True)
    parser.add_argument("--pilot-bundle-root", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-path", type=Path, required=True)
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        choices=GRADIENT_ACCUMULATION_STEP_CHOICES,
        default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    )
    parser.add_argument(
        "--text-embedding-mask-policy",
        choices=TEXT_EMBEDDING_MASK_POLICY_CHOICES,
        default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--throughput-profile-label",
        default=DEFAULT_THROUGHPUT_PROFILE_LABEL,
    )
    parser.add_argument("--dataloader-num-workers", type=int, default=4)
    add_boolean_argument(parser, "--dataloader-pin-memory", default=True)
    add_boolean_argument(parser, "--dataloader-persistent-workers", default=True)
    parser.add_argument("--dataloader-prefetch-factor", type=int, default=4)
    add_boolean_argument(parser, "--non-blocking-transfer", default=True)
    add_boolean_argument(parser, "--ref-mel-cache-enabled", default=True)
    parser.add_argument("--ref-mel-cache-max-items", type=int, default=2048)
    add_boolean_argument(parser, "--torch-profiler-enabled", default=False)
    parser.add_argument("--torch-profiler-wait-steps", type=int, default=1)
    parser.add_argument("--torch-profiler-warmup-steps", type=int, default=1)
    parser.add_argument("--torch-profiler-active-steps", type=int, default=4)
    parser.add_argument("--torch-profiler-repeat", type=int, default=1)
    add_boolean_argument(parser, "--torch-profiler-record-shapes", default=True)
    add_boolean_argument(parser, "--torch-profiler-profile-memory", default=True)
    add_boolean_argument(parser, "--torch-profiler-with-stack", default=False)
    parser.add_argument("--torch-profiler-trace-dir", default=None)
    return parser.parse_args()


def _running_status_payload(
    *,
    checkpoint_path: Path,
    eval_jsonl: Path,
    output_dir: Path,
    eval_row_count: int,
    gradient_accumulation_steps: int,
    text_embedding_mask_policy: TextEmbeddingMaskPolicy,
    bundle_precomputed_reference_input: dict[str, object] | None,
    throughput_profile: dict[str, object],
) -> dict[str, object]:
    """Build the running status payload for standalone eval."""
    return {
        "status": "running",
        "stage": "eval",
        "updated_at": _utc_now_iso(),
        "checkpoint_path": checkpoint_path.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "eval_row_count": eval_row_count,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "text_embedding_mask_policy": text_embedding_mask_policy,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "throughput_profile": throughput_profile,
    }


def _completed_status_payload(
    *,
    checkpoint_path: Path,
    eval_jsonl: Path,
    output_dir: Path,
    eval_row_count: int,
    gradient_accumulation_steps: int,
    text_embedding_mask_policy: TextEmbeddingMaskPolicy,
    bundle_precomputed_reference_input: dict[str, object] | None,
    throughput_profile: dict[str, object],
    eval_summary: dict[str, object],
) -> dict[str, object]:
    """Build the completed status payload for standalone eval."""
    return {
        "status": "completed",
        "stage": "eval",
        "updated_at": _utc_now_iso(),
        "checkpoint_path": checkpoint_path.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "eval_row_count": eval_row_count,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "text_embedding_mask_policy": text_embedding_mask_policy,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "throughput_profile": throughput_profile,
        "eval_summary": eval_summary,
    }


def _failed_status_payload(
    *,
    checkpoint_path: Path,
    eval_jsonl: Path,
    output_dir: Path,
    eval_row_count: int,
    gradient_accumulation_steps: int,
    text_embedding_mask_policy: TextEmbeddingMaskPolicy,
    bundle_precomputed_reference_input: dict[str, object] | None,
    throughput_profile: dict[str, object],
    exc: BaseException,
) -> dict[str, object]:
    """Build the failed status payload for standalone eval."""
    return {
        "status": "failed",
        "stage": "eval",
        "updated_at": _utc_now_iso(),
        "checkpoint_path": checkpoint_path.as_posix(),
        "eval_jsonl": eval_jsonl.as_posix(),
        "output_dir": output_dir.as_posix(),
        "eval_row_count": eval_row_count,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "text_embedding_mask_policy": text_embedding_mask_policy,
        "bundle_precomputed_reference_input": bundle_precomputed_reference_input,
        "throughput_profile": throughput_profile,
        "error": f"{type(exc).__name__}: {exc}",
    }


def main() -> int:
    """Run standalone checkpoint eval and persist deterministic artifacts."""
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "status.json"
    report_path = output_dir / "report.json"
    failure_path = output_dir / "failure.txt"
    summary_path = output_dir / "eval_summary.json"
    eval_row_count = _count_jsonl_rows(args.eval_jsonl)
    bundle_summary = (
        None
        if args.pilot_bundle_root is None
        else load_optional_training_bundle_summary(args.pilot_bundle_root)
    )
    bundle_precomputed_reference_input = (
        None
        if bundle_summary is None
        else {
            "kind": bundle_summary.precomputed_reference_input.kind,
            "version": bundle_summary.precomputed_reference_input.version,
            "source_field": bundle_summary.precomputed_reference_input.source_field,
            "artifact_root": bundle_summary.precomputed_reference_input.artifact_root,
            "artifact_count": bundle_summary.precomputed_reference_input.artifact_count,
        }
    )
    throughput_policy = resolve_throughput_batch_policy(
        profile_label=str(args.throughput_profile_label),
        max_batch_size=int(args.batch_size),
    )
    throughput_profile = throughput_policy_payload(throughput_policy)
    gradient_accumulation_steps = resolve_gradient_accumulation_steps(
        getattr(args, "gradient_accumulation_steps", None),
        default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    )
    text_embedding_mask_policy = resolve_text_embedding_mask_policy(
        getattr(args, "text_embedding_mask_policy", None),
        default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    )
    write_json(
        status_path,
        _running_status_payload(
            checkpoint_path=args.checkpoint_path,
            eval_jsonl=args.eval_jsonl,
            output_dir=output_dir,
            eval_row_count=eval_row_count,
            gradient_accumulation_steps=gradient_accumulation_steps,
            text_embedding_mask_policy=text_embedding_mask_policy,
            bundle_precomputed_reference_input=bundle_precomputed_reference_input,
            throughput_profile=throughput_profile,
        ),
    )
    try:
        if not torch.cuda.is_available():
            raise SystemExit("Evaluator expected GPU-visible torch inside the container.")
        if torch.version.hip is None:
            raise SystemExit("Evaluator expected ROCm-enabled torch inside the container.")
        eval_args = argparse.Namespace(
            init_model_path=str(args.model_id),
            eval_jsonl=args.eval_jsonl.as_posix(),
            output_model_path=(output_dir / "checkpoints").as_posix(),
            batch_size=int(args.batch_size),
            gradient_accumulation_steps=gradient_accumulation_steps,
            throughput_profile_label=str(args.throughput_profile_label),
            dataloader_num_workers=int(args.dataloader_num_workers),
            dataloader_pin_memory=bool(args.dataloader_pin_memory),
            dataloader_persistent_workers=bool(args.dataloader_persistent_workers),
            dataloader_prefetch_factor=int(args.dataloader_prefetch_factor),
            non_blocking_transfer=bool(args.non_blocking_transfer),
            ref_mel_cache_enabled=bool(args.ref_mel_cache_enabled),
            ref_mel_cache_max_items=int(args.ref_mel_cache_max_items),
            text_embedding_mask_policy=text_embedding_mask_policy,
            torch_profiler_enabled=bool(args.torch_profiler_enabled),
            torch_profiler_wait_steps=int(args.torch_profiler_wait_steps),
            torch_profiler_warmup_steps=int(args.torch_profiler_warmup_steps),
            torch_profiler_active_steps=int(args.torch_profiler_active_steps),
            torch_profiler_repeat=int(args.torch_profiler_repeat),
            torch_profiler_record_shapes=bool(args.torch_profiler_record_shapes),
            torch_profiler_profile_memory=bool(args.torch_profiler_profile_memory),
            torch_profiler_with_stack=bool(args.torch_profiler_with_stack),
            torch_profiler_trace_dir=args.torch_profiler_trace_dir,
            resume_from_checkpoint=args.checkpoint_path.as_posix(),
            pilot_bundle_root=(
                None if args.pilot_bundle_root is None else args.pilot_bundle_root.as_posix()
            ),
        )
        eval_summary = sft_12hz.evaluate_with_args(eval_args)
        write_json(summary_path, asdict(eval_summary))
        write_json(
            status_path,
            _completed_status_payload(
                checkpoint_path=args.checkpoint_path,
                eval_jsonl=args.eval_jsonl,
                output_dir=output_dir,
                eval_row_count=eval_row_count,
                gradient_accumulation_steps=gradient_accumulation_steps,
                text_embedding_mask_policy=text_embedding_mask_policy,
                bundle_precomputed_reference_input=bundle_precomputed_reference_input,
                throughput_profile=throughput_profile,
                eval_summary=asdict(eval_summary),
            ),
        )
        report = StandaloneEvalReport(
            generated_at=_utc_now_iso(),
            status="completed",
            model_id=str(args.model_id),
            checkpoint_path=args.checkpoint_path.as_posix(),
            eval_jsonl=args.eval_jsonl.as_posix(),
            output_dir=output_dir.as_posix(),
            eval_row_count=eval_row_count,
            gradient_accumulation_steps=gradient_accumulation_steps,
            text_embedding_mask_policy=text_embedding_mask_policy,
            bundle_precomputed_reference_input=bundle_precomputed_reference_input,
            throughput_profile=throughput_profile,
            eval_summary=asdict(eval_summary),
            failure=None,
        )
        write_json(report_path, asdict(report))
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except BaseException as exc:
        failure_path.write_text(traceback.format_exc(), encoding="utf-8")
        write_json(
            status_path,
            _failed_status_payload(
                checkpoint_path=args.checkpoint_path,
                eval_jsonl=args.eval_jsonl,
                output_dir=output_dir,
                eval_row_count=eval_row_count,
                gradient_accumulation_steps=gradient_accumulation_steps,
                text_embedding_mask_policy=text_embedding_mask_policy,
                bundle_precomputed_reference_input=bundle_precomputed_reference_input,
                throughput_profile=throughput_profile,
                exc=exc,
            ),
        )
        report = StandaloneEvalReport(
            generated_at=_utc_now_iso(),
            status="failed",
            model_id=str(args.model_id),
            checkpoint_path=args.checkpoint_path.as_posix(),
            eval_jsonl=args.eval_jsonl.as_posix(),
            output_dir=output_dir.as_posix(),
            eval_row_count=eval_row_count,
            gradient_accumulation_steps=gradient_accumulation_steps,
            text_embedding_mask_policy=text_embedding_mask_policy,
            bundle_precomputed_reference_input=bundle_precomputed_reference_input,
            throughput_profile=throughput_profile,
            eval_summary=None,
            failure={"error": f"{type(exc).__name__}: {exc}"},
        )
        write_json(report_path, asdict(report))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
