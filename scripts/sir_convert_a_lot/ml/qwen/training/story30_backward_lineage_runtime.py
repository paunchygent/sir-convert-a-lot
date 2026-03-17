"""Runtime helpers for the Story 30 backward-lineage proof surface.

Purpose:
    Build and execute the canonical local and remote commands for the T212
    backward-lineage Hemma proof lane.

Relationships:
    - Used by `story30_backward_lineage_proof.py`.
    - Reuses `qwen-scratch-policy` as the canonical host-side scratch audit.
"""

from __future__ import annotations

import subprocess

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import parse_json_object_from_mixed_stdout
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_artifacts import (
    Story30BackwardLineageProofConfig,
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
RUN_HEMMA_BACKWARD_LINEAGE_PREFIX = [
    "pdm",
    "run",
    "run-hemma",
    "--",
    "pdm",
    "run",
    "qwen-story30-backward-lineage",
]


def run_remote_json(command_args: list[str], *, label: str) -> dict[str, object]:
    """Run one remote backward-lineage proof command and parse its JSON payload."""
    command = [*RUN_HEMMA_BACKWARD_LINEAGE_PREFIX, *command_args]
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


def ensure_remote_scratch_headroom(config: Story30BackwardLineageProofConfig) -> dict[str, object]:
    """Require enough Hemma scratch headroom before a backward-lineage probe launches."""
    command = [
        *RUN_HEMMA_QWEN_SCRATCH_POLICY_PREFIX,
        "audit",
        "--required-free-bytes",
        str(config.required_scratch_free_bytes),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0 and result.stdout.strip() == "":
        raise SystemExit(
            "Task 212 scratch audit failed.\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    payload = parse_json_object_from_mixed_stdout(result.stdout)
    if payload.get("meets_required_headroom") is True:
        return payload
    raise SystemExit(
        "Task 212 launch blocked because Hemma scratch headroom is below the required threshold. "
        f"free_bytes={payload.get('scratch_free_bytes')} "
        f"required_free_bytes={config.required_scratch_free_bytes}."
    )


def remote_launch_proof_args(config: Story30BackwardLineageProofConfig) -> list[str]:
    """Return the remote proof-launch args for one prepared config."""
    command = [
        "remote-launch",
        "--proof-id",
        config.proof_id,
        "--remote-proof-output-root",
        config.remote_proof_output_root,
        "--source-bundle-root",
        config.source_bundle_root,
        "--manifest-family",
        config.manifest_family,
        "--source-lines",
        ",".join(str(value) for value in config.source_lines),
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--launch-id",
        config.launch_id,
    ]
    if config.skip_build:
        command.append("--skip-build")
    return command


def remote_status_proof_args(config: Story30BackwardLineageProofConfig) -> list[str]:
    """Return the remote proof-status args for one prepared config."""
    return [
        "remote-status",
        "--proof-id",
        config.proof_id,
        "--remote-proof-output-root",
        config.remote_proof_output_root,
        "--launch-id",
        config.launch_id,
    ]
