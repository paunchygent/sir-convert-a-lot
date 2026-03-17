"""Runtime helpers for the Story 30 fresh-start proof surface.

Purpose:
    Build and execute the canonical local and remote commands for the short
    fresh-start Candidate 1 Hemma proof lane.

Relationships:
    - Used by `story30_freshstart_proof.py` for prepare/launch/status flows.
    - Reuses `qwen-scratch-policy` and `qwen-train` as the canonical host and
      detached-runtime surfaces.
"""

from __future__ import annotations

import subprocess

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import parse_json_object_from_mixed_stdout
from scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_artifacts import (
    Story30FreshstartProofConfig,
    remote_bundle_root,
    remote_launch_root,
)

RUN_HEMMA_QWEN_SCRATCH_POLICY_PREFIX = [
    "pdm",
    "run",
    "run-hemma",
    "--",
    "pdm",
    "run",
    "qwen-scratch-policy",
]
RUN_HEMMA_FRESHSTART_PREFIX = [
    "pdm",
    "run",
    "run-hemma",
    "--",
    "pdm",
    "run",
    "qwen-story30-freshstart-proof",
]
LOCAL_QWEN_TRAIN_PREFIX = ["pdm", "run", "qwen-train"]


def run_remote_json(command_args: list[str], *, label: str) -> dict[str, object]:
    """Run one remote fresh-start proof command and parse its JSON payload."""
    command = [*RUN_HEMMA_FRESHSTART_PREFIX, *command_args]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0 and result.stdout.strip() == "":
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    try:
        return parse_json_object_from_mixed_stdout(result.stdout)
    except SystemExit as exc:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        ) from exc


def run_local_qwen_train_json(qwen_train_args: list[str], *, label: str) -> dict[str, object]:
    """Run one local `qwen-train` command and parse its JSON payload."""
    command = [*LOCAL_QWEN_TRAIN_PREFIX, *qwen_train_args]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0 and result.stdout.strip() == "":
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    try:
        return parse_json_object_from_mixed_stdout(result.stdout)
    except SystemExit as exc:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        ) from exc


def ensure_remote_scratch_headroom(config: Story30FreshstartProofConfig) -> dict[str, object]:
    """Require enough Hemma scratch headroom before a fresh-start probe launches."""
    command = [
        *RUN_HEMMA_QWEN_SCRATCH_POLICY_PREFIX,
        "audit",
        "--required-free-bytes",
        str(config.required_scratch_free_bytes),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0 and result.stdout.strip() == "":
        raise SystemExit(
            "Task 211 scratch audit failed.\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    payload = parse_json_object_from_mixed_stdout(result.stdout)
    if payload.get("meets_required_headroom") is True:
        return payload
    raise SystemExit(
        "Task 211 launch blocked because Hemma scratch headroom is below the required threshold. "
        f"free_bytes={payload.get('scratch_free_bytes')} "
        f"required_free_bytes={config.required_scratch_free_bytes}."
    )


def remote_launch_proof_args(config: Story30FreshstartProofConfig) -> list[str]:
    """Return the remote proof-launch args for one prepared config."""
    command = [
        "remote-launch",
        "--proof-id",
        config.proof_id,
        "--remote-proof-output-root",
        config.remote_proof_output_root,
        "--remote-training-output-root",
        config.remote_training_output_root,
        "--train-source-bundle-root",
        config.train_source_bundle_root,
        "--eval-source-bundle-root",
        config.eval_source_bundle_root,
        "--train-manifest-family",
        config.train_manifest_family,
        "--eval-manifest-family",
        config.eval_manifest_family,
        "--eval-source-manifest-family",
        config.eval_source_manifest_family,
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--throughput-profile-label",
        config.throughput_profile_label,
        "--train-line-start",
        str(config.train_line_start),
        "--train-line-end",
        str(config.train_line_end),
        "--eval-line-start",
        str(config.eval_line_start),
        "--eval-line-end",
        str(config.eval_line_end),
        "--batch-size",
        str(config.batch_size),
        "--max-steps",
        str(config.max_steps),
        "--checkpoint-interval-steps",
        str(config.checkpoint_interval_steps),
        "--eval-interval-steps",
        str(config.eval_interval_steps),
        "--gradient-accumulation-steps",
        str(config.gradient_accumulation_steps),
        "--launch-id",
        config.launch_id,
    ]
    if config.skip_build:
        command.append("--skip-build")
    return command


def remote_status_proof_args(config: Story30FreshstartProofConfig) -> list[str]:
    """Return the remote proof-status args for one prepared config."""
    return [
        "remote-status",
        "--proof-id",
        config.proof_id,
        "--remote-proof-output-root",
        config.remote_proof_output_root,
        "--remote-training-output-root",
        config.remote_training_output_root,
        "--launch-id",
        config.launch_id,
    ]


def qwen_train_launch_args(config: Story30FreshstartProofConfig) -> list[str]:
    """Return the canonical detached fresh-start training launch args."""
    command = [
        "launch",
        "--output-root",
        config.remote_training_output_root,
        "--pilot-bundle-root",
        remote_bundle_root(config).as_posix(),
        "--train-manifest-family",
        config.train_manifest_family,
        "--eval-manifest-family",
        config.eval_manifest_family,
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--throughput-profile-label",
        config.throughput_profile_label,
        "--batch-size",
        str(config.batch_size),
        "--max-steps",
        str(config.max_steps),
        "--checkpoint-interval-steps",
        str(config.checkpoint_interval_steps),
        "--eval-interval-steps",
        str(config.eval_interval_steps),
        "--gradient-accumulation-steps",
        str(config.gradient_accumulation_steps),
        "--launch-id",
        config.launch_id,
    ]
    if config.skip_build:
        command.append("--skip-build")
    return command


def qwen_train_status_args(config: Story30FreshstartProofConfig) -> list[str]:
    """Return the canonical detached fresh-start training status args."""
    return [
        "status",
        "--output-root",
        config.remote_training_output_root,
        "--launch-root",
        remote_launch_root(config).as_posix(),
    ]
