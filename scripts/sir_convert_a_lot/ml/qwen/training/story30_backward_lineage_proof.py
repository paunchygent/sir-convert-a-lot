"""CLI implementation for the Story 30 backward-lineage proof.

Purpose:
    Expose one deterministic `prepare`, `launch`, and `status` surface for the
    T212 backward-lineage Hemma proof lane while delegating the actual detached
    proof execution to bounded helpers.

Relationships:
    - Uses `story30_backward_lineage_artifacts.py` for proof-package state.
    - Uses `story30_backward_lineage_detached.py` for the remote background worker.
    - Uses `story30_backward_lineage_runner.py` for the host-side proof logic.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_artifacts import (
    DEFAULT_COMMAND_NAME,
    DEFAULT_HOOK_PROFILE,
    DEFAULT_LOCAL_PROOF_ROOT,
    DEFAULT_MANIFEST_FAMILY,
    DEFAULT_REMOTE_PROOF_OUTPUT_ROOT,
    DEFAULT_REQUIRED_SCRATCH_FREE_BYTES,
    DEFAULT_SOURCE_BUNDLE_ROOT,
    DEFAULT_SOURCE_LINES,
    DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
    Story30BackwardLineageProofConfig,
    build_prepare_config,
    checklist_path,
    config_path,
    latest_pointer_path,
    launch_path,
    load_config,
    plan_path,
    remote_proof_root,
    resolve_proof_root,
    status_markdown_path,
    status_path,
    task_label_for_hook_profile,
    write_json,
    write_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_detached import (
    DetachedBackwardLineageLaunch,
    inspect_detached_backward_lineage_proof,
    launch_detached_backward_lineage_proof,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_runtime import (
    ensure_remote_scratch_headroom,
    remote_launch_proof_args,
    remote_status_proof_args,
    run_remote_json,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for the T212 proof surface."""
    parser = argparse.ArgumentParser(
        description="Prepare and operate the Story 30 backward-lineage proof surface."
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
    prepare.add_argument("--source-bundle-root", type=Path, default=DEFAULT_SOURCE_BUNDLE_ROOT)
    prepare.add_argument("--manifest-family", default=DEFAULT_MANIFEST_FAMILY)
    prepare.add_argument(
        "--source-lines",
        default=",".join(str(value) for value in DEFAULT_SOURCE_LINES),
    )
    prepare.add_argument("--text-embedding-mask-policy", default=DEFAULT_TEXT_EMBEDDING_MASK_POLICY)
    prepare.add_argument("--hook-profile", default=DEFAULT_HOOK_PROFILE)
    prepare.add_argument(
        "--required-scratch-free-bytes",
        type=int,
        default=DEFAULT_REQUIRED_SCRATCH_FREE_BYTES,
    )
    prepare.add_argument("--skip-build", action="store_true")

    for command_name, help_text in (
        ("launch", "Launch the detached backward-lineage Hemma probe."),
        ("status", "Inspect the detached backward-lineage Hemma probe."),
    ):
        command_parser = subparsers.add_parser(command_name, help=help_text)
        command_parser.add_argument("--output-root", type=Path, default=DEFAULT_LOCAL_PROOF_ROOT)
        command_parser.add_argument("--proof-id", default=None)
        command_parser.add_argument("--proof-root", type=Path, default=None)

    remote_launch = subparsers.add_parser("remote-launch", help=argparse.SUPPRESS)
    remote_launch.add_argument("--proof-id", required=True)
    remote_launch.add_argument("--remote-proof-output-root", type=Path, required=True)
    remote_launch.add_argument("--source-bundle-root", type=Path, required=True)
    remote_launch.add_argument("--manifest-family", required=True)
    remote_launch.add_argument("--source-lines", required=True)
    remote_launch.add_argument("--text-embedding-mask-policy", required=True)
    remote_launch.add_argument("--hook-profile", required=True)
    remote_launch.add_argument("--launch-id", required=True)
    remote_launch.add_argument("--skip-build", action="store_true")

    remote_status = subparsers.add_parser("remote-status", help=argparse.SUPPRESS)
    remote_status.add_argument("--proof-id", required=True)
    remote_status.add_argument("--remote-proof-output-root", type=Path, required=True)
    remote_status.add_argument("--launch-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Prepare or operate the Story 30 backward-lineage proof surface."""
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
                label=f"{config.task_label.lower()} backward-lineage launch",
            )
            write_json(launch_path(local_root), payload)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        payload = run_remote_json(
            remote_status_proof_args(config),
            label=f"{config.task_label.lower()} backward-lineage status",
        )
        write_json(status_path(local_root), payload)
        write_markdown(status_markdown_path(local_root), _render_status_markdown(payload))
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "remote-launch":
        config = _config_from_remote_launch_args(args)
        launch = launch_detached_backward_lineage_proof(
            output_root=remote_proof_root(config),
            repo_root=Path.cwd(),
            proof_args=_runner_args(config),
            launch_id=config.launch_id,
        )
        payload = _serialize_dataclass_like(launch)
        write_json(remote_proof_root(config) / "launch.json", payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "remote-status":
        config = _config_for_remote_status(args)
        launch = _load_remote_launch(remote_proof_root(config) / "launch.json")
        status = inspect_detached_backward_lineage_proof(launch)
        payload = _serialize_dataclass_like(status)
        write_json(remote_proof_root(config) / "status.json", payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    raise SystemExit(f"Unsupported backward-lineage proof command: {args.command}")


def _config_from_remote_launch_args(args: argparse.Namespace) -> Story30BackwardLineageProofConfig:
    hook_profile = str(args.hook_profile)
    return Story30BackwardLineageProofConfig(
        task_label=task_label_for_hook_profile(hook_profile),
        command_name=DEFAULT_COMMAND_NAME,
        prepared_at="remote-launch",
        proof_id=str(args.proof_id),
        local_proof_root="remote",
        remote_proof_output_root=Path(args.remote_proof_output_root).as_posix(),
        source_bundle_root=Path(args.source_bundle_root).as_posix(),
        manifest_family=str(args.manifest_family),
        source_lines=_parse_source_lines_pair(str(args.source_lines)),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        hook_profile=hook_profile,
        required_scratch_free_bytes=DEFAULT_REQUIRED_SCRATCH_FREE_BYTES,
        skip_build=bool(args.skip_build),
        launch_id=str(args.launch_id),
    )


def _config_for_remote_status(args: argparse.Namespace) -> Story30BackwardLineageProofConfig:
    return Story30BackwardLineageProofConfig(
        task_label=task_label_for_hook_profile(DEFAULT_HOOK_PROFILE),
        command_name=DEFAULT_COMMAND_NAME,
        prepared_at="remote-status",
        proof_id=str(args.proof_id),
        local_proof_root="remote",
        remote_proof_output_root=Path(args.remote_proof_output_root).as_posix(),
        source_bundle_root="",
        manifest_family=DEFAULT_MANIFEST_FAMILY,
        source_lines=DEFAULT_SOURCE_LINES,
        text_embedding_mask_policy=DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
        hook_profile=DEFAULT_HOOK_PROFILE,
        required_scratch_free_bytes=DEFAULT_REQUIRED_SCRATCH_FREE_BYTES,
        skip_build=True,
        launch_id=str(args.launch_id),
    )


def _load_remote_launch(path: Path) -> DetachedBackwardLineageLaunch:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Backward-lineage remote launch payload was malformed.")
    return DetachedBackwardLineageLaunch(
        generated_at=str(payload["generated_at"]),
        launch_id=str(payload["launch_id"]),
        pid=int(payload["pid"]),
        repo_root=str(payload["repo_root"]),
        output_root=str(payload["output_root"]),
        log_path=str(payload["log_path"]),
        worker_status_path=str(payload["worker_status_path"]),
        report_path=str(payload["report_path"]),
        failure_path=str(payload["failure_path"]),
        proof_args=[str(value) for value in payload["proof_args"]],
        command=[str(value) for value in payload["command"]],
    )


def _runner_args(config: Story30BackwardLineageProofConfig) -> list[str]:
    command = [
        "--source-bundle-root",
        config.source_bundle_root,
        "--manifest-family",
        config.manifest_family,
        "--source-lines",
        ",".join(str(value) for value in config.source_lines),
        "--text-embedding-mask-policy",
        config.text_embedding_mask_policy,
        "--hook-profile",
        config.hook_profile,
    ]
    if config.skip_build:
        command.append("--skip-build")
    return command


def _parse_source_lines_pair(raw_value: str) -> tuple[int, int]:
    """Parse the canonical two-line source tuple from one CLI string."""
    pieces = [piece.strip() for piece in raw_value.split(",") if piece.strip() != ""]
    if len(pieces) != 2:
        raise SystemExit("Backward-lineage proof requires exactly two source lines.")
    return int(pieces[0]), int(pieces[1])


def _serialize_dataclass_like(payload: object) -> dict[str, object]:
    """Serialize one dataclass payload or one attribute object into JSON data."""
    if is_dataclass(payload) and not isinstance(payload, type):
        serialized = asdict(payload)
        if not isinstance(serialized, dict):
            raise SystemExit("Backward-lineage payload serialization did not produce an object.")
        return serialized
    if hasattr(payload, "__dict__"):
        serialized = dict(vars(payload))
        if all(isinstance(key, str) for key in serialized):
            return {str(key): value for key, value in serialized.items()}
    raise SystemExit("Backward-lineage payload could not be serialized as an object.")


def _render_plan_markdown(config: Story30BackwardLineageProofConfig) -> str:
    source_lines = ", ".join(str(value) for value in config.source_lines)
    return "\n".join(
        [
            "# Story 30 Backward-Lineage Proof Plan",
            "",
            f"- Proof id: `{config.proof_id}`",
            f"- Manifest family: `{config.manifest_family}`",
            f"- Source lines: `{source_lines}`",
            f"- Mask policy: `{config.text_embedding_mask_policy}`",
            f"- Hook profile: `{config.hook_profile}`",
            f"- Launch: `pdm run {config.command_name} launch --proof-id {config.proof_id}`",
            f"- Status: `pdm run {config.command_name} status --proof-id {config.proof_id}`",
            "- Branch order: `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation.",
        ]
    )


def _render_checklist_markdown(config: Story30BackwardLineageProofConfig) -> str:
    source_lines = ", ".join(str(value) for value in config.source_lines)
    return "\n".join(
        [
            "# Story 30 Backward-Lineage Checklist",
            "",
            f"- [ ] Mini-bundle materialized for source lines `{source_lines}`.",
            "- [ ] Detached Hemma worker launched.",
            "- [ ] Pair probes completed in branch order.",
            "- [ ] Row-isolation probes completed.",
            "- [ ] First non-finite backward edge/tensor recorded.",
        ]
    )


def _render_status_markdown(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Story 30 Backward-Lineage Status",
            "",
            f"```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```",
        ]
    )
