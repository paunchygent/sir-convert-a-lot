"""CLI implementation for the Story 30 fresh-start discriminant proof.

Purpose:
    Expose one deterministic prepare/launch/status surface for the short
    fresh-start Candidate 1 Hemma proof lane while delegating mini-bundle
    materialization and detached training to bounded helpers.

Relationships:
    - Uses `story30_freshstart_artifacts.py` for proof-package state.
    - Uses `story30_freshstart_bundle.py` for remote mini-bundle creation.
    - Uses `story30_freshstart_runtime.py` for local/remote command execution.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_artifacts import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_COMMAND_NAME,
    DEFAULT_EVAL_INTERVAL_STEPS,
    DEFAULT_EVAL_LINE_END,
    DEFAULT_EVAL_LINE_START,
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    DEFAULT_LOCAL_PROOF_ROOT,
    DEFAULT_MAX_STEPS,
    DEFAULT_REMOTE_PROOF_OUTPUT_ROOT,
    DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT,
    DEFAULT_REQUIRED_SCRATCH_FREE_BYTES,
    DEFAULT_SOURCE_BUNDLE_ROOT,
    DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    DEFAULT_TRAIN_LINE_END,
    DEFAULT_TRAIN_LINE_START,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    Story30FreshstartProofConfig,
    build_prepare_config,
    checklist_path,
    config_path,
    latest_pointer_path,
    launch_path,
    load_config,
    plan_path,
    remote_bundle_root,
    remote_launch_root,
    remote_proof_root,
    resolve_proof_root,
    status_markdown_path,
    status_path,
    write_json,
    write_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_bundle import (
    materialize_mini_bundle,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_runtime import (
    ensure_remote_scratch_headroom,
    qwen_train_launch_args,
    qwen_train_status_args,
    remote_launch_proof_args,
    remote_status_proof_args,
    run_local_qwen_train_json,
    run_remote_json,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for the fresh-start proof surface."""
    parser = argparse.ArgumentParser(
        description="Prepare and operate the Story 30 fresh-start Candidate 1 proof surface."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare one deterministic proof package.")
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_LOCAL_PROOF_ROOT)
    prepare.add_argument("--proof-id", default=None)
    prepare.add_argument(
        "--remote-proof-output-root",
        type=Path,
        default=DEFAULT_REMOTE_PROOF_OUTPUT_ROOT,
    )
    prepare.add_argument(
        "--remote-training-output-root",
        type=Path,
        default=DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT,
    )
    prepare.add_argument("--source-bundle-root", type=Path, default=DEFAULT_SOURCE_BUNDLE_ROOT)
    prepare.add_argument("--train-manifest-family", default=DEFAULT_TRAIN_MANIFEST_FAMILY)
    prepare.add_argument("--eval-manifest-family", default=DEFAULT_EVAL_MANIFEST_FAMILY)
    prepare.add_argument("--text-embedding-mask-policy", default=DEFAULT_TEXT_EMBEDDING_MASK_POLICY)
    prepare.add_argument("--throughput-profile-label", default=DEFAULT_THROUGHPUT_PROFILE_LABEL)
    prepare.add_argument("--train-line-start", type=int, default=DEFAULT_TRAIN_LINE_START)
    prepare.add_argument("--train-line-end", type=int, default=DEFAULT_TRAIN_LINE_END)
    prepare.add_argument("--eval-line-start", type=int, default=DEFAULT_EVAL_LINE_START)
    prepare.add_argument("--eval-line-end", type=int, default=DEFAULT_EVAL_LINE_END)
    prepare.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    prepare.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    prepare.add_argument(
        "--checkpoint-interval-steps", type=int, default=DEFAULT_CHECKPOINT_INTERVAL_STEPS
    )
    prepare.add_argument("--eval-interval-steps", type=int, default=DEFAULT_EVAL_INTERVAL_STEPS)
    prepare.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    )
    prepare.add_argument(
        "--required-scratch-free-bytes",
        type=int,
        default=DEFAULT_REQUIRED_SCRATCH_FREE_BYTES,
    )
    prepare.add_argument("--skip-build", action="store_true")

    for command_name, help_text in (
        ("launch", "Launch the detached fresh-start Hemma probe."),
        ("status", "Inspect the detached fresh-start Hemma probe."),
    ):
        command_parser = subparsers.add_parser(command_name, help=help_text)
        command_parser.add_argument("--output-root", type=Path, default=DEFAULT_LOCAL_PROOF_ROOT)
        command_parser.add_argument("--proof-id", default=None)
        command_parser.add_argument("--proof-root", type=Path, default=None)

    remote_launch = subparsers.add_parser(
        "remote-launch",
        help=argparse.SUPPRESS,
    )
    _add_remote_launch_args(remote_launch)

    remote_status = subparsers.add_parser(
        "remote-status",
        help=argparse.SUPPRESS,
    )
    remote_status.add_argument("--proof-id", required=True)
    remote_status.add_argument("--remote-proof-output-root", type=Path, required=True)
    remote_status.add_argument("--remote-training-output-root", type=Path, required=True)
    remote_status.add_argument("--launch-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Prepare or operate the Story 30 fresh-start proof surface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "prepare":
        config = build_prepare_config(args)
        local_root = Path(config.local_proof_root)
        local_root.mkdir(parents=True, exist_ok=False)
        write_json(config_path(local_root), asdict(config))
        write_markdown(plan_path(local_root), _render_plan_markdown(config))
        write_markdown(checklist_path(local_root), _render_checklist_markdown(config))
        write_json(
            latest_pointer_path(Path(args.output_root)),
            {"proof_root": local_root.as_posix(), "proof_id": config.proof_id},
        )
        print(json.dumps(asdict(config), indent=2, ensure_ascii=False))
        return 0

    if args.command in {"launch", "status"}:
        local_root = resolve_proof_root(
            base_output_root=Path(args.output_root),
            proof_root_arg=args.proof_root,
            proof_id_arg=args.proof_id,
        )
        config = load_config(local_root)
        if args.command == "launch":
            ensure_remote_scratch_headroom(config)
            payload = run_remote_json(
                remote_launch_proof_args(config),
                label=f"{config.task_label.lower()} fresh-start launch",
            )
            write_json(launch_path(local_root), payload)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        payload = run_remote_json(
            remote_status_proof_args(config),
            label=f"{config.task_label.lower()} fresh-start status",
        )
        write_json(status_path(local_root), payload)
        write_markdown(status_markdown_path(local_root), _render_status_markdown(payload))
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "remote-launch":
        config = _config_from_remote_launch_args(args)
        proof_root_path = remote_proof_root(config)
        proof_root_path.mkdir(parents=True, exist_ok=False)
        bundle_payload = materialize_mini_bundle(
            source_bundle_root=Path(config.source_bundle_root),
            target_bundle_root=remote_bundle_root(config),
            train_manifest_family=config.train_manifest_family,
            eval_manifest_family=config.eval_manifest_family,
            train_line_start=config.train_line_start,
            train_line_end=config.train_line_end,
            eval_line_start=config.eval_line_start,
            eval_line_end=config.eval_line_end,
        )
        launch_payload = run_local_qwen_train_json(
            qwen_train_launch_args(config),
            label=f"{config.task_label.lower()} local qwen-train launch",
        )
        payload = {
            "proof_id": config.proof_id,
            "task_label": config.task_label,
            "mini_bundle": asdict(bundle_payload),
            "remote_proof_root": proof_root_path.as_posix(),
            "remote_launch_root": remote_launch_root(config).as_posix(),
            "qwen_train_launch": launch_payload,
        }
        write_json(proof_root_path / "launch.json", payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "remote-status":
        config = _config_for_remote_status(args)
        status_payload = run_local_qwen_train_json(
            qwen_train_status_args(config),
            label=f"{DEFAULT_COMMAND_NAME} local qwen-train status",
        )
        payload = {
            "proof_id": config.proof_id,
            "remote_proof_root": remote_proof_root(config).as_posix(),
            "remote_launch_root": remote_launch_root(config).as_posix(),
            "status": status_payload,
        }
        write_json(remote_proof_root(config) / "status.json", payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    raise SystemExit(f"Unsupported fresh-start proof command: {args.command}")


def _add_remote_launch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--proof-id", required=True)
    parser.add_argument("--remote-proof-output-root", type=Path, required=True)
    parser.add_argument("--remote-training-output-root", type=Path, required=True)
    parser.add_argument("--source-bundle-root", type=Path, required=True)
    parser.add_argument("--train-manifest-family", required=True)
    parser.add_argument("--eval-manifest-family", required=True)
    parser.add_argument("--text-embedding-mask-policy", required=True)
    parser.add_argument("--throughput-profile-label", required=True)
    parser.add_argument("--train-line-start", type=int, required=True)
    parser.add_argument("--train-line-end", type=int, required=True)
    parser.add_argument("--eval-line-start", type=int, required=True)
    parser.add_argument("--eval-line-end", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--checkpoint-interval-steps", type=int, required=True)
    parser.add_argument("--eval-interval-steps", type=int, required=True)
    parser.add_argument("--gradient-accumulation-steps", type=int, required=True)
    parser.add_argument("--launch-id", required=True)
    parser.add_argument("--skip-build", action="store_true")


def _config_from_remote_launch_args(args: argparse.Namespace) -> Story30FreshstartProofConfig:
    return Story30FreshstartProofConfig(
        task_label="Task 211",
        command_name=DEFAULT_COMMAND_NAME,
        prepared_at="remote-launch",
        proof_id=str(args.proof_id),
        local_proof_root="remote-only",
        remote_proof_output_root=Path(args.remote_proof_output_root).as_posix(),
        remote_training_output_root=Path(args.remote_training_output_root).as_posix(),
        source_bundle_root=Path(args.source_bundle_root).as_posix(),
        train_manifest_family=str(args.train_manifest_family),
        eval_manifest_family=str(args.eval_manifest_family),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        throughput_profile_label=str(args.throughput_profile_label),
        train_line_start=int(args.train_line_start),
        train_line_end=int(args.train_line_end),
        eval_line_start=int(args.eval_line_start),
        eval_line_end=int(args.eval_line_end),
        batch_size=int(args.batch_size),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        eval_interval_steps=int(args.eval_interval_steps),
        gradient_accumulation_steps=int(args.gradient_accumulation_steps),
        required_scratch_free_bytes=0,
        skip_build=bool(args.skip_build),
        launch_id=str(args.launch_id),
    )


def _config_for_remote_status(args: argparse.Namespace) -> Story30FreshstartProofConfig:
    return Story30FreshstartProofConfig(
        task_label="Task 211",
        command_name=DEFAULT_COMMAND_NAME,
        prepared_at="remote-status",
        proof_id=str(args.proof_id),
        local_proof_root="remote-only",
        remote_proof_output_root=Path(args.remote_proof_output_root).as_posix(),
        remote_training_output_root=Path(args.remote_training_output_root).as_posix(),
        source_bundle_root="",
        train_manifest_family=DEFAULT_TRAIN_MANIFEST_FAMILY,
        eval_manifest_family=DEFAULT_EVAL_MANIFEST_FAMILY,
        text_embedding_mask_policy=DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
        throughput_profile_label=DEFAULT_THROUGHPUT_PROFILE_LABEL,
        train_line_start=DEFAULT_TRAIN_LINE_START,
        train_line_end=DEFAULT_TRAIN_LINE_END,
        eval_line_start=DEFAULT_EVAL_LINE_START,
        eval_line_end=DEFAULT_EVAL_LINE_END,
        batch_size=DEFAULT_BATCH_SIZE,
        max_steps=DEFAULT_MAX_STEPS,
        checkpoint_interval_steps=DEFAULT_CHECKPOINT_INTERVAL_STEPS,
        eval_interval_steps=DEFAULT_EVAL_INTERVAL_STEPS,
        gradient_accumulation_steps=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
        required_scratch_free_bytes=0,
        skip_build=False,
        launch_id=str(args.launch_id),
    )


def _render_plan_markdown(config: Story30FreshstartProofConfig) -> str:
    train_slice = (
        f"{config.train_manifest_family} lines {config.train_line_start}..{config.train_line_end}"
    )
    eval_slice = (
        f"{config.eval_manifest_family} lines {config.eval_line_start}..{config.eval_line_end}"
    )
    prepare_command = (
        f"pdm run {config.command_name} prepare --proof-id {config.proof_id}"
        f"{' --skip-build' if config.skip_build else ''}"
    )
    return "\n".join(
        [
            f"# {config.task_label} Fresh-Start Proof Plan",
            "",
            f"- command_name: `{config.command_name}`",
            f"- proof_id: `{config.proof_id}`",
            f"- source_bundle_root: `{config.source_bundle_root}`",
            f"- train_slice: `{train_slice}`",
            f"- eval_slice: `{eval_slice}`",
            f"- batch_size: `{config.batch_size}`",
            f"- max_steps: `{config.max_steps}`",
            f"- gradient_accumulation_steps: `{config.gradient_accumulation_steps}`",
            f"- text_embedding_mask_policy: `{config.text_embedding_mask_policy}`",
            "",
            "## Commands",
            "",
            f"```bash\n{prepare_command}\n```",
            "",
            f"```bash\npdm run {config.command_name} launch --proof-id {config.proof_id}\n```",
            "",
            f"```bash\npdm run {config.command_name} status --proof-id {config.proof_id}\n```",
        ]
    )


def _render_checklist_markdown(config: Story30FreshstartProofConfig) -> str:
    train_slice = (
        f"{config.train_manifest_family} lines {config.train_line_start}..{config.train_line_end}"
    )
    eval_slice = (
        f"{config.eval_manifest_family} lines {config.eval_line_start}..{config.eval_line_end}"
    )
    return "\n".join(
        [
            f"# {config.task_label} Fresh-Start Proof Checklist",
            "",
            "- [ ] Local proof package prepared",
            "- [ ] Hemma scratch headroom audited",
            "- [ ] Mini-bundle materialized from the canonical pilot bundle",
            "- [ ] Detached fresh-start training launch recorded",
            "- [ ] Status captured and decision written back into docs/reference",
            "",
            "## Probe Contract",
            "",
            f"- train slice: `{train_slice}`",
            f"- eval slice: `{eval_slice}`",
            f"- launch_id: `{config.launch_id}`",
            f"- remote training output root: `{config.remote_training_output_root}`",
            f"- remote proof output root: `{config.remote_proof_output_root}`",
        ]
    )


def _render_status_markdown(payload: dict[str, object]) -> str:
    status_payload = payload.get("status")
    current_phase = None
    current_optimizer_step = None
    current_train_iteration = None
    failure = None
    if isinstance(status_payload, dict):
        pilot_status = status_payload.get("pilot_status")
        if isinstance(pilot_status, dict):
            current_phase = pilot_status.get("current_phase")
            current_optimizer_step = pilot_status.get("current_optimizer_step")
            current_train_iteration = pilot_status.get("current_train_iteration")
            failure = pilot_status.get("error")
    top_level_status = (
        None if not isinstance(status_payload, dict) else status_payload.get("status")
    )
    running = None if not isinstance(status_payload, dict) else status_payload.get("running")
    exit_code = None if not isinstance(status_payload, dict) else status_payload.get("exit_code")
    return "\n".join(
        [
            "# Task 211 Fresh-Start Status",
            "",
            f"- proof_id: `{payload.get('proof_id')}`",
            f"- remote_launch_root: `{payload.get('remote_launch_root')}`",
            f"- status: `{top_level_status}`",
            f"- running: `{running}`",
            f"- exit_code: `{exit_code}`",
            f"- current_phase: `{current_phase}`",
            f"- current_optimizer_step: `{current_optimizer_step}`",
            f"- current_train_iteration: `{current_train_iteration}`",
            f"- failure: `{failure}`",
            "",
            "## Payload",
            "",
            "```json",
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            "```",
        ]
    )
