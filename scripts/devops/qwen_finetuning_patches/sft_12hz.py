# coding=utf-8
# Copyright 2026 The Alibaba Qwen team.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Patched Qwen `sft_12hz.py` entrypoint for Swedish multi-speaker training.

This module remains the canonical trainer entrypoint, but the heavy logic now
lives in focused helper modules so the public surface stays SRP-aligned and
below the repository's hard LoC ceiling.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_cli import parse_args
from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop import execute_training_loop
from scripts.devops.qwen_finetuning_patches.sft_12hz_progress import TrainingProgressHeartbeat
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import prepare_training_run
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import TrainingTrackerSummary


def train_with_args(
    args: object,
    *,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None = None,
    tracker_ready_callback: Callable[[TrainingTrackerSummary], None] | None = None,
) -> TrainingSummary:
    """Run one bounded Qwen fine-tuning job and return machine-readable metrics."""
    if not hasattr(args, "__dict__"):
        raise TypeError("Expected an argparse-style namespace for training arguments.")
    prepared = prepare_training_run(args)
    return execute_training_loop(
        prepared,
        progress_callback=progress_callback,
        tracker_ready_callback=tracker_ready_callback,
    )


def train() -> None:
    """Run the canonical CLI entrypoint for the patched Qwen trainer."""
    args = parse_args()
    summary = train_with_args(args)
    if args.metrics_output_json is not None:
        metrics_output_path = Path(args.metrics_output_json)
        metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
        with metrics_output_path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(summary), handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    train()
