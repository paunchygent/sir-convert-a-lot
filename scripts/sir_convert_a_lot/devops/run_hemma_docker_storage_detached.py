"""Launch and inspect detached Hemma Docker storage remediation.

Purpose:
    Provide the committed launch/status surface for the host-wide Hemma Docker storage remediation
    Docker storage migration so the live Hemma change can run detached from the
    local client session.

Relationships:
    - Wraps `hemma_docker_storage_detached_runtime.py`.
    - Launches the committed `hemma-docker-storage-remediation` runner on
      Hemma through a remote tmux session.
    - Writes deterministic local launch/status artifacts under
      `build/verification/hemma-docker-storage-remediation-detached/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.hemma_docker_storage_detached_runtime import (
    DEFAULT_REMOTE_OUTPUT_ROOT,
    DEFAULT_SESSION_NAME_PREFIX,
    HemmaDockerStorageDetachedLaunch,
    HemmaDockerStorageDetachedStatus,
    default_session_name,
    inspect_detached_docker_storage_migration,
    launch_detached_docker_storage_migration,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/hemma-docker-storage-remediation-detached")


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for detached Hemma Docker storage workflows."""
    parser = argparse.ArgumentParser(
        description="Launch and inspect detached Hemma Docker storage remediation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser(
        "launch", help="Launch one detached Hemma Docker storage remediation migration run."
    )
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--remote-output-root", type=Path, default=DEFAULT_REMOTE_OUTPUT_ROOT)
    launch.add_argument("--session-name", default=None)
    launch.add_argument("--session-name-prefix", default=DEFAULT_SESSION_NAME_PREFIX)

    status = subparsers.add_parser(
        "status", help="Inspect one detached Hemma Docker storage remediation migration run."
    )
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    status.add_argument("--session-name", default=None)

    return parser


def _prepare_output_root(output_root: Path) -> None:
    """Create the deterministic local output root for detached Hemma Docker storage remediation
    artifacts.
    """
    output_root.mkdir(parents=True, exist_ok=True)


def _launch_path(output_root: Path) -> Path:
    """Return the canonical detached launch metadata path."""
    return output_root / "launch.json"


def _status_path(output_root: Path) -> Path:
    """Return the canonical detached status metadata path."""
    return output_root / "status.json"


def _status_markdown_path(output_root: Path) -> Path:
    """Return the canonical detached status markdown path."""
    return output_root / "status.md"


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload with stable formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one Markdown artifact with deterministic formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _load_launch(output_root: Path) -> HemmaDockerStorageDetachedLaunch:
    """Load the previously written detached Hemma Docker storage remediation launch metadata."""
    payload = json.loads(_launch_path(output_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Detached Hemma Docker storage remediation launch metadata was malformed.")
    return HemmaDockerStorageDetachedLaunch(
        generated_at=_required_str(payload, "generated_at"),
        session_name=_required_str(payload, "session_name"),
        remote_repo_root=_required_str(payload, "remote_repo_root"),
        remote_output_root=_required_str(payload, "remote_output_root"),
        remote_log_path=_required_str(payload, "remote_log_path"),
        remote_exit_code_path=_required_str(payload, "remote_exit_code_path"),
        remote_command=_required_str(payload, "remote_command"),
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from one metadata payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(
            f"Detached Hemma Docker storage remediation metadata returned malformed `{key}`."
        )
    return value


def _render_status_markdown(status: HemmaDockerStorageDetachedStatus) -> str:
    """Render one concise Markdown status view for detached Hemma Docker storage remediation."""
    lines = [
        "# Hemma Docker storage remediation Detached Docker Storage Migration Status",
        "",
        f"- checked_at: `{status.checked_at}`",
        f"- session_name: `{status.session_name}`",
        f"- session_exists: `{status.session_exists}`",
        f"- exit_code: `{status.exit_code}`",
        f"- report_found: `{status.report_found}`",
        "",
        "## Log Tail",
        "",
        "```text",
        status.log_tail,
        "```",
    ]
    if status.report_payload is not None:
        lines.extend(
            [
                "",
                "## Remote Hemma Docker storage remediation Report",
                "",
                "```json",
                json.dumps(status.report_payload, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Launch or inspect detached Hemma Docker storage remediation."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)
    _prepare_output_root(output_root)

    if args.command == "launch":
        session_name = (
            str(args.session_name)
            if args.session_name is not None
            else default_session_name(str(args.session_name_prefix))
        )
        launch = launch_detached_docker_storage_migration(
            session_name=session_name,
            output_root=Path(args.remote_output_root),
        )
        payload = asdict(launch)
        _write_json(_launch_path(output_root), payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "status":
        launch = _load_launch(output_root)
        if args.session_name is not None:
            launch = HemmaDockerStorageDetachedLaunch(
                generated_at=launch.generated_at,
                session_name=str(args.session_name),
                remote_repo_root=launch.remote_repo_root,
                remote_output_root=launch.remote_output_root,
                remote_log_path=launch.remote_log_path,
                remote_exit_code_path=launch.remote_exit_code_path,
                remote_command=launch.remote_command,
            )
        status = inspect_detached_docker_storage_migration(launch)
        payload = asdict(status)
        _write_json(_status_path(output_root), payload)
        _write_markdown(_status_markdown_path(output_root), _render_status_markdown(status))
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    raise SystemExit(
        f"Unsupported detached Hemma Docker storage remediation command: {args.command}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
