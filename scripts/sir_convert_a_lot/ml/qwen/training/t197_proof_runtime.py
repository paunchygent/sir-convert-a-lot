"""Remote-command helpers for the Story 29 proof surfaces.

Purpose:
    Build and execute the canonical remote `qwen-train` commands for Story 29
    while keeping remote execution logic separate from local proof-artifact
    management.

Relationships:
    - Used by the task-specific Story 29 proof entrypoints.
    - Consumes proof configuration and path helpers from `t197_proof_artifacts.py`.
"""

from __future__ import annotations

import json
import subprocess

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import parse_json_object_from_mixed_stdout
from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_artifacts import (
    Story29ProofConfig,
    remote_gate_launch_root,
    remote_window_launch_root,
)

RUN_HEMMA_QWEN_TRAIN_PREFIX = [
    "pdm",
    "run",
    "run-hemma",
    "--",
    "pdm",
    "run",
    "qwen-train",
]


def full_remote_command(qwen_train_args: list[str]) -> list[str]:
    """Wrap raw `qwen-train` args in the canonical `run-hemma` command prefix."""
    return [*RUN_HEMMA_QWEN_TRAIN_PREFIX, *qwen_train_args]


def run_remote_training_json(qwen_train_args: list[str], *, label: str) -> dict[str, object]:
    """Run one remote `qwen-train` command and parse its JSON payload."""
    command = full_remote_command(qwen_train_args)
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0 and result.stdout.strip() == "":
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    try:
        payload = parse_json_object_from_mixed_stdout(result.stdout)
    except SystemExit as exc:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        ) from exc
    return payload


def window_qwen_train_args(config: Story29ProofConfig) -> list[str]:
    """Return raw `qwen-train` args for the bounded replay phase."""
    command = [
        "diagnose-non-finite",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        config.source_launch_root,
        "--checkpoint-path",
        config.source_checkpoint_path,
        "--launch-id",
        config.window_launch_id,
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--gradient-accumulation-steps",
        str(config.gradient_accumulation_steps),
        "--start-optimizer-step",
        str(config.window_start_optimizer_step),
        "--end-optimizer-step",
        str(config.window_end_optimizer_step),
    ]
    if config.skip_build:
        command.append("--skip-build")
    return command


def window_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote bounded replay command."""
    return full_remote_command(window_qwen_train_args(config))


def status_window_qwen_train_args(config: Story29ProofConfig) -> list[str]:
    """Return raw `qwen-train` args for bounded replay status inspection."""
    return [
        "status",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        remote_window_launch_root(config).as_posix(),
    ]


def status_window_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote status command for the bounded replay phase."""
    return full_remote_command(status_window_qwen_train_args(config))


def gate_qwen_train_args(config: Story29ProofConfig) -> list[str]:
    """Return raw `qwen-train` args for the `1500` continuation phase."""
    command = [
        "resume",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        remote_window_launch_root(config).as_posix(),
        "--launch-id",
        config.gate_launch_id,
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--gradient-accumulation-steps",
        str(config.gradient_accumulation_steps),
        "--max-steps",
        str(config.gate_max_steps),
        "--checkpoint-interval-steps",
        str(config.gate_checkpoint_interval_steps),
        "--eval-interval-steps",
        str(config.gate_eval_interval_steps),
    ]
    if config.skip_build:
        command.append("--skip-build")
    return command


def gate_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote continuation command for the `1500` gate."""
    return full_remote_command(gate_qwen_train_args(config))


def status_gate_qwen_train_args(config: Story29ProofConfig) -> list[str]:
    """Return raw `qwen-train` args for `1500`-gate status inspection."""
    return [
        "status",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        remote_gate_launch_root(config).as_posix(),
    ]


def status_gate_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote status command for the `1500` gate phase."""
    return full_remote_command(status_gate_qwen_train_args(config))


def status_summary_markdown(phase_name: str, status_payload: dict[str, object]) -> str:
    """Render one concise markdown summary for a proof phase status payload."""
    pilot_status = status_payload.get("pilot_status")
    current_optimizer_step = (
        None if not isinstance(pilot_status, dict) else pilot_status.get("current_optimizer_step")
    )
    latest_eval_loss = (
        None if not isinstance(pilot_status, dict) else pilot_status.get("latest_eval_loss")
    )
    eval_runs_completed = (
        None if not isinstance(pilot_status, dict) else pilot_status.get("eval_runs_completed")
    )
    return "\n".join(
        [
            f"# Task 197 {phase_name} Status",
            "",
            f"- status: `{status_payload.get('status')}`",
            f"- running: `{status_payload.get('running')}`",
            f"- exit_code: `{status_payload.get('exit_code')}`",
            f"- current_optimizer_step: `{current_optimizer_step}`",
            f"- latest_eval_loss: `{latest_eval_loss}`",
            f"- eval_runs_completed: `{eval_runs_completed}`",
            "",
            "## Payload",
            "",
            "```json",
            json.dumps(status_payload, indent=2, ensure_ascii=False, sort_keys=True),
            "```",
        ]
    )


def ensure_window_passed(config: Story29ProofConfig) -> dict[str, object]:
    """Require a successful bounded replay before launching the `1500` gate."""
    status_payload = run_remote_training_json(
        status_window_qwen_train_args(config),
        label=f"{config.task_label.lower()} bounded replay status",
    )
    pilot_status = status_payload.get("pilot_status")
    current_optimizer_step = (
        None if not isinstance(pilot_status, dict) else pilot_status.get("current_optimizer_step")
    )
    if status_payload.get("running") is True:
        raise SystemExit(
            f"{config.task_label} bounded replay is still running; "
            "do not launch the `1500` gate yet."
        )
    if status_payload.get("exit_code") != 0:
        raise SystemExit(
            f"{config.task_label} bounded replay did not exit cleanly; "
            "do not launch the `1500` gate."
        )
    if (
        not isinstance(current_optimizer_step, int)
        or current_optimizer_step < config.window_end_optimizer_step
    ):
        raise SystemExit(
            f"{config.task_label} bounded replay did not reach the required "
            "optimizer-step gate before `1500` continuation."
        )
    return status_payload
