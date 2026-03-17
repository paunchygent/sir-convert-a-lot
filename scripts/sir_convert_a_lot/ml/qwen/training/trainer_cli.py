"""CLI parsing for the in-container Qwen training entrypoint.

Purpose:
    Keep `trainer.py` focused on orchestration by owning the argparse surface
    for the in-container training runtime, including the shared text-embedding
    assembly and mask contract flags.

Relationships:
    - Imported by `trainer.py`.
    - Reuses domain choice sets from the training package.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_eval import DEFAULT_EVAL_INTERVAL_STEPS
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import add_boolean_argument
from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    GRADIENT_ACCUMULATION_STEP_CHOICES,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
    TEXT_EMBEDDING_ASSEMBLY_MODE_CHOICES,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    TEXT_EMBEDDING_MASK_POLICY_CHOICES,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
)


def parse_trainer_args() -> argparse.Namespace:
    """Parse CLI arguments for the in-container training entrypoint."""
    parser = argparse.ArgumentParser(description="Run the Qwen training trainer.")
    parser.add_argument("--launch-id", default=None)
    parser.add_argument("--launch-metadata-path", type=Path, default=None)
    parser.add_argument("--model-id", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--train-jsonl", type=Path, required=True)
    parser.add_argument("--eval-jsonl", type=Path, required=True)
    parser.add_argument("--pilot-bundle-root", type=Path, default=None)
    parser.add_argument("--train-manifest-family", default=None)
    parser.add_argument("--eval-manifest-family", default=None)
    parser.add_argument(
        "--text-embedding-assembly-mode",
        choices=TEXT_EMBEDDING_ASSEMBLY_MODE_CHOICES,
        default=DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
    )
    parser.add_argument(
        "--text-embedding-mask-policy",
        choices=TEXT_EMBEDDING_MASK_POLICY_CHOICES,
        default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tracker-project-name", default="qwen-training")
    parser.add_argument("--mlflow-experiment-name", default="qwen-training")
    parser.add_argument("--mlflow-tracking-uri", default=None)
    parser.add_argument("--mlflow-artifact-root", default=None)
    parser.add_argument("--tensorboard-logging-dir", default=None)
    parser.add_argument("--tracker-run-name", default=None)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--throughput-profile-label", default=DEFAULT_THROUGHPUT_PROFILE_LABEL)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--num-epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        choices=GRADIENT_ACCUMULATION_STEP_CHOICES,
        default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    )
    parser.add_argument("--checkpoint-interval-steps", type=int, default=500)
    parser.add_argument("--eval-interval-steps", type=int, default=DEFAULT_EVAL_INTERVAL_STEPS)
    parser.add_argument("--durable-checkpoint-retention", type=int, default=3)
    parser.add_argument("--durable-checkpoint-min-free-bytes", type=int, default=16 * 1024**3)
    parser.add_argument("--dataloader-num-workers", type=int, default=4)
    add_boolean_argument(parser, "--dataloader-pin-memory", default=True)
    add_boolean_argument(parser, "--dataloader-persistent-workers", default=True)
    parser.add_argument("--dataloader-prefetch-factor", type=int, default=4)
    add_boolean_argument(parser, "--non-blocking-transfer", default=True)
    add_boolean_argument(parser, "--data-path-proof-mode", default=False)
    parser.add_argument("--heartbeat-interval-optimizer-steps", type=int, default=20)
    parser.add_argument("--finite-loss-max-consecutive-steps", type=int, default=3)
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
    parser.add_argument("--resume-from-checkpoint", type=Path, default=None)
    parser.add_argument("--diagnostic-kind", default=None)
    parser.add_argument("--diagnostic-source-launch-root", type=Path, default=None)
    parser.add_argument("--diagnostic-source-checkpoint-path", type=Path, default=None)
    parser.add_argument("--diagnostic-target-optimizer-step", type=int, default=None)
    parser.add_argument("--diagnostic-capture-artifact-path", type=Path, default=None)
    parser.add_argument("--diagnostic-capture-launch-root-host-path", type=Path, default=None)
    parser.add_argument("--diagnostic-capture-checkpoint-path", type=Path, default=None)
    parser.add_argument("--diagnostic-start-optimizer-step", type=int, default=None)
    parser.add_argument("--diagnostic-end-optimizer-step", type=int, default=None)
    return parser.parse_args()
