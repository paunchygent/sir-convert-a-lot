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
    remote_fallback_eval_output_root,
    remote_fallback_launch_root,
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
RUN_HEMMA_QWEN_SCRATCH_POLICY_PREFIX = [
    "pdm",
    "run",
    "run-hemma",
    "--",
    "pdm",
    "run",
    "qwen-scratch-policy",
]
RUN_HEMMA_QWEN_STORY29_EVAL_DETACHED_PREFIX = [
    "pdm",
    "run",
    "run-hemma",
    "--",
    "pdm",
    "run",
    "qwen-story29-eval-detached",
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


def full_remote_eval_detached_command(eval_args: list[str]) -> list[str]:
    """Wrap raw detached-eval args in the canonical `run-hemma` command prefix."""
    return [*RUN_HEMMA_QWEN_STORY29_EVAL_DETACHED_PREFIX, *eval_args]


def run_remote_eval_detached_json(eval_args: list[str], *, label: str) -> dict[str, object]:
    """Run one remote detached Story 29 eval command and parse its JSON payload."""
    command = full_remote_eval_detached_command(eval_args)
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


def _run_remote_scratch_policy_json(
    policy_args: list[str],
    *,
    label: str,
) -> dict[str, object]:
    """Run one remote scratch-policy command and parse its JSON payload."""
    command = [*RUN_HEMMA_QWEN_SCRATCH_POLICY_PREFIX, *policy_args]
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


def ensure_remote_scratch_headroom(config: Story29ProofConfig) -> dict[str, object]:
    """Require enough Hemma scratch headroom before a detached proof launch starts."""
    payload = _run_remote_scratch_policy_json(
        [
            "audit",
            "--required-free-bytes",
            str(config.required_scratch_free_bytes),
        ],
        label=f"{config.task_label.lower()} scratch audit",
    )
    free_bytes = payload.get("scratch_free_bytes")
    meets_headroom = payload.get("meets_required_headroom")
    if meets_headroom is True:
        return payload
    raise SystemExit(
        f"{config.task_label} launch blocked because Hemma scratch headroom is below the "
        "required threshold. "
        f"free_bytes={free_bytes} required_free_bytes={config.required_scratch_free_bytes}. "
        "Run `pdm run run-hemma -- pdm run qwen-scratch-policy audit` and "
        "`pdm run run-hemma -- pdm run qwen-scratch-policy remediate ...` first."
    )


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


def fallback1470_qwen_train_args(config: Story29ProofConfig) -> list[str]:
    """Return raw `qwen-train` args for the fallback `1406 -> 1470` replay phase."""
    command = [
        "diagnose-non-finite",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        config.source_launch_root,
        "--checkpoint-path",
        config.source_checkpoint_path,
        "--launch-id",
        config.fallback_launch_id,
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--gradient-accumulation-steps",
        str(config.gradient_accumulation_steps),
        "--start-optimizer-step",
        str(config.window_start_optimizer_step),
        "--end-optimizer-step",
        str(config.fallback_max_steps),
    ]
    if config.skip_build:
        command.append("--skip-build")
    return command


def fallback1470_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote command for the fallback `1406 -> 1470` replay."""
    return full_remote_command(fallback1470_qwen_train_args(config))


def status_fallback1470_qwen_train_args(config: Story29ProofConfig) -> list[str]:
    """Return raw `qwen-train` args for fallback `1470` replay status inspection."""
    return [
        "status",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        remote_fallback_launch_root(config).as_posix(),
    ]


def status_fallback1470_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote status command for the fallback `1470` phase."""
    return full_remote_command(status_fallback1470_qwen_train_args(config))


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


def fallback_eval_detached_args(
    config: Story29ProofConfig,
    *,
    checkpoint_path: str | None = None,
) -> list[str]:
    """Return raw detached-eval args for the fallback standalone eval phase."""
    command = [
        "launch",
        "--output-root",
        remote_fallback_eval_output_root(config).as_posix(),
        "--",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        remote_fallback_launch_root(config).as_posix(),
        "--eval-id",
        config.fallback_eval_id,
        "--eval-output-dir",
        remote_fallback_eval_output_root(config).as_posix(),
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--gradient-accumulation-steps",
        str(config.gradient_accumulation_steps),
    ]
    if checkpoint_path is not None:
        command.extend(["--checkpoint-path", checkpoint_path])
    if config.skip_build:
        command.append("--skip-build")
    return command


def fallback_eval_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote detached-eval command for the fallback checkpoint."""
    return full_remote_eval_detached_command(fallback_eval_detached_args(config))


def status_fallback_eval_detached_args(config: Story29ProofConfig) -> list[str]:
    """Return raw detached-eval args for fallback standalone eval status inspection."""
    return [
        "status",
        "--output-root",
        remote_fallback_eval_output_root(config).as_posix(),
    ]


def status_fallback_eval_remote_command(config: Story29ProofConfig) -> list[str]:
    """Return the full remote status command for fallback standalone eval."""
    return full_remote_eval_detached_command(status_fallback_eval_detached_args(config))


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
            f"# Story 29 {phase_name} Status",
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


def ensure_fallback_passed(config: Story29ProofConfig) -> dict[str, object]:
    """Require a successful fallback replay before launching standalone eval."""
    status_payload = run_remote_training_json(
        status_fallback1470_qwen_train_args(config),
        label=f"{config.task_label.lower()} fallback `1470` status",
    )
    pilot_status = status_payload.get("pilot_status")
    current_optimizer_step = (
        None if not isinstance(pilot_status, dict) else pilot_status.get("current_optimizer_step")
    )
    if status_payload.get("running") is True:
        raise SystemExit(
            f"{config.task_label} fallback `1470` replay is still running; "
            "do not launch standalone eval yet."
        )
    if status_payload.get("exit_code") != 0:
        raise SystemExit(
            f"{config.task_label} fallback `1470` replay did not exit cleanly; "
            "do not launch standalone eval."
        )
    if (
        not isinstance(current_optimizer_step, int)
        or current_optimizer_step < config.fallback_max_steps
    ):
        raise SystemExit(
            f"{config.task_label} fallback replay did not reach optimizer step "
            f"`{config.fallback_max_steps}` before standalone eval."
        )
    checkpoint_path = latest_checkpoint_path(status_payload)
    if checkpoint_path is None:
        raise SystemExit(
            f"{config.task_label} fallback replay did not expose a durable checkpoint path for "
            "standalone eval."
        )
    return status_payload


def latest_checkpoint_path(status_payload: dict[str, object]) -> str | None:
    """Return the best available durable checkpoint path from one training status payload."""
    latest_checkpoint = status_payload.get("latest_checkpoint")
    if isinstance(latest_checkpoint, dict):
        checkpoint_path = latest_checkpoint.get("checkpoint_path")
        if isinstance(checkpoint_path, str):
            return checkpoint_path
    pilot_status = status_payload.get("pilot_status")
    if isinstance(pilot_status, dict):
        checkpoint_path = pilot_status.get("latest_durable_checkpoint_path")
        if isinstance(checkpoint_path, str):
            return checkpoint_path
    return None
