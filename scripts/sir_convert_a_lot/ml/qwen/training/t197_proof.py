"""Shared command surface for the Story 29 detached proof lanes.

Purpose:
    Expose one reusable prepare/launch/status CLI for bounded Story 29 proof
    lanes while delegating proof configuration and remote execution to bounded
    helper modules.

Relationships:
    - Used by the task-specific `T197` and `T198` proof entrypoints.
    - Uses `t197_proof_artifacts.py` for deterministic local proof artifacts.
    - Uses `t197_proof_runtime.py` for detached Hemma launch/status commands.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    GRADIENT_ACCUMULATION_STEP_CHOICES,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story29_proof_rendering import (
    render_checklist_markdown,
    render_plan_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_artifacts import (
    DEFAULT_GATE_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_GATE_EVAL_INTERVAL_STEPS,
    DEFAULT_GATE_MAX_STEPS,
    DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT,
    DEFAULT_SOURCE_CHECKPOINT_PATH,
    DEFAULT_SOURCE_LAUNCH_ROOT,
    DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
    DEFAULT_WINDOW_END_OPTIMIZER_STEP,
    DEFAULT_WINDOW_START_OPTIMIZER_STEP,
    T197_PROOF_PROFILE,
    Story29ProofProfile,
    build_prepare_config,
    checklist_path,
    config_path,
    gate_launch_path,
    gate_status_markdown_path,
    gate_status_path,
    latest_pointer_path,
    load_config,
    plan_path,
    resolve_proof_root,
    window_launch_path,
    window_status_markdown_path,
    window_status_path,
    write_json,
    write_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_runtime import (
    ensure_window_passed,
    gate_qwen_train_args,
    gate_remote_command,
    run_remote_training_json,
    status_gate_qwen_train_args,
    status_gate_remote_command,
    status_summary_markdown,
    status_window_qwen_train_args,
    status_window_remote_command,
    window_qwen_train_args,
    window_remote_command,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    TEXT_EMBEDDING_MASK_POLICY_CHOICES,
)


def build_parser(profile: Story29ProofProfile) -> argparse.ArgumentParser:
    """Build the CLI parser for one Story 29 proof surface."""
    parser = argparse.ArgumentParser(
        description=(f"Prepare and operate the detached Hemma {profile.task_label} proof surface.")
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare one deterministic proof package.")
    prepare.add_argument("--output-root", type=Path, default=profile.local_proof_root)
    prepare.add_argument("--proof-id", default=None)
    prepare.add_argument(
        "--remote-training-output-root",
        type=Path,
        default=DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT,
    )
    prepare.add_argument("--source-launch-root", type=Path, default=DEFAULT_SOURCE_LAUNCH_ROOT)
    prepare.add_argument(
        "--source-checkpoint-path",
        type=Path,
        default=DEFAULT_SOURCE_CHECKPOINT_PATH,
    )
    prepare.add_argument(
        "--text-embedding-mask-policy",
        choices=TEXT_EMBEDDING_MASK_POLICY_CHOICES,
        default=DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
    )
    prepare.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        choices=GRADIENT_ACCUMULATION_STEP_CHOICES,
        default=profile.default_gradient_accumulation_steps,
    )
    prepare.add_argument(
        "--window-start-optimizer-step",
        type=int,
        default=DEFAULT_WINDOW_START_OPTIMIZER_STEP,
    )
    prepare.add_argument(
        "--window-end-optimizer-step",
        type=int,
        default=DEFAULT_WINDOW_END_OPTIMIZER_STEP,
    )
    prepare.add_argument("--gate-max-steps", type=int, default=DEFAULT_GATE_MAX_STEPS)
    prepare.add_argument(
        "--gate-checkpoint-interval-steps",
        type=int,
        default=DEFAULT_GATE_CHECKPOINT_INTERVAL_STEPS,
    )
    prepare.add_argument(
        "--gate-eval-interval-steps",
        type=int,
        default=DEFAULT_GATE_EVAL_INTERVAL_STEPS,
    )
    prepare.add_argument("--skip-build", action="store_true")

    for command_name, help_text in (
        ("launch-window", "Launch the bounded `1406 -> 1418` replay phase."),
        ("status-window", "Inspect the bounded `1406 -> 1418` replay phase."),
        ("launch-gate1500", "Launch the follow-on `1500` continuation phase."),
        ("status-gate1500", "Inspect the follow-on `1500` continuation phase."),
    ):
        subparser = subparsers.add_parser(command_name, help=help_text)
        subparser.add_argument("--output-root", type=Path, default=profile.local_proof_root)
        subparser.add_argument("--proof-id", default=None)
        subparser.add_argument("--proof-root", type=Path, default=None)
    return parser


def run_main(profile: Story29ProofProfile, argv: list[str] | None = None) -> int:
    """Prepare or operate one task-specific Story 29 detached proof surface."""
    parser = build_parser(profile)
    args = parser.parse_args(argv)

    if args.command == "prepare":
        config = build_prepare_config(profile, args)
        local_root = Path(config.local_proof_root)
        local_root.mkdir(parents=True, exist_ok=False)
        write_json(config_path(local_root), asdict(config))
        write_markdown(
            plan_path(local_root),
            render_plan_markdown(
                config,
                window_command=window_remote_command(config),
                status_window_command=status_window_remote_command(config),
                gate_command=gate_remote_command(config),
                status_gate_command=status_gate_remote_command(config),
            ),
        )
        write_markdown(checklist_path(local_root), render_checklist_markdown(config))
        write_json(
            latest_pointer_path(Path(args.output_root)),
            {"proof_root": local_root.as_posix(), "proof_id": config.proof_id},
        )
        print(json.dumps(asdict(config), indent=2, ensure_ascii=False))
        return 0

    local_root = resolve_proof_root(
        base_output_root=Path(args.output_root),
        proof_root_arg=args.proof_root,
        proof_id_arg=args.proof_id,
    )
    config = load_config(local_root)

    if args.command == "launch-window":
        launch_payload = run_remote_training_json(
            window_qwen_train_args(config),
            label=f"{config.task_label.lower()} bounded replay launch",
        )
        write_json(window_launch_path(local_root), launch_payload)
        print(json.dumps(launch_payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "status-window":
        status_payload = run_remote_training_json(
            status_window_qwen_train_args(config),
            label=f"{config.task_label.lower()} bounded replay status",
        )
        write_json(window_status_path(local_root), status_payload)
        write_markdown(
            window_status_markdown_path(local_root),
            status_summary_markdown("Window", status_payload),
        )
        print(json.dumps(status_payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "launch-gate1500":
        status_payload = ensure_window_passed(config)
        write_json(window_status_path(local_root), status_payload)
        write_markdown(
            window_status_markdown_path(local_root),
            status_summary_markdown("Window", status_payload),
        )
        launch_payload = run_remote_training_json(
            gate_qwen_train_args(config),
            label=f"{config.task_label.lower()} `1500` gate launch",
        )
        write_json(gate_launch_path(local_root), launch_payload)
        print(json.dumps(launch_payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "status-gate1500":
        status_payload = run_remote_training_json(
            status_gate_qwen_train_args(config),
            label=f"{config.task_label.lower()} `1500` gate status",
        )
        write_json(gate_status_path(local_root), status_payload)
        write_markdown(
            gate_status_markdown_path(local_root),
            status_summary_markdown("Gate1500", status_payload),
        )
        print(json.dumps(status_payload, indent=2, ensure_ascii=False))
        return 0

    raise SystemExit(f"Unsupported {profile.task_label} proof command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    """Prepare or operate the detached Hemma Task 197 proof surface."""
    return run_main(T197_PROOF_PROFILE, argv)


if __name__ == "__main__":
    raise SystemExit(main())
