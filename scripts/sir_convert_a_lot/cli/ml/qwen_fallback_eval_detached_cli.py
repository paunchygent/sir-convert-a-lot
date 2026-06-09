"""Launch and inspect detached Qwen fallback proof lane fallback standalone eval on Hemma.

Purpose:
    Provide the committed detached execution surface for the Qwen fallback proof lane fallback
    standalone eval so Hemma proof evidence survives the local client session.

Relationships:
    - Wraps `ml.qwen.training.qwen_fallback_eval_detached`.
    - Used by the shared Qwen fallback proof lane proof wrapper during fallback close-out.
"""

from __future__ import annotations

import argparse
import json
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_fallback_eval_detached import (
    DetachedQwenFallbackEvalLaunch,
    inspect_detached_qwen_fallback_eval,
    launch_detached_qwen_fallback_eval,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the committed CLI parser for detached Qwen fallback proof lane eval workflows."""
    parser = argparse.ArgumentParser(
        description="Launch and inspect detached Qwen fallback standalone eval on Hemma."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    launch = subparsers.add_parser("launch", help="Launch one detached fallback eval worker.")
    launch.add_argument("--output-root", type=Path, required=True)
    launch.add_argument("--launch-id", default=None)
    launch.add_argument("eval_args", nargs=argparse.REMAINDER)

    status = subparsers.add_parser("status", help="Inspect one detached fallback eval worker.")
    status.add_argument("--output-root", type=Path, required=True)
    return parser


def _launch_metadata_path(output_root: Path) -> Path:
    """Return the canonical launch metadata path."""
    return output_root / "launch.json"


def _status_metadata_path(output_root: Path) -> Path:
    """Return the canonical detached status metadata path."""
    return output_root / "status.json"


def _status_markdown_path(output_root: Path) -> Path:
    """Return the canonical detached status markdown path."""
    return output_root / "status.md"


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic Markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _status_markdown(status_payload: dict[str, object]) -> str:
    """Render one concise Markdown summary for detached Qwen fallback proof lane eval status."""
    lines = [
        "# Detached Qwen fallback proof lane Fallback Eval Status",
        "",
        f"- checked_at: `{status_payload.get('checked_at')}`",
        f"- launch_id: `{status_payload.get('launch_id')}`",
        f"- pid: `{status_payload.get('pid')}`",
        f"- running: `{status_payload.get('running')}`",
        f"- exit_code: `{status_payload.get('exit_code')}`",
        f"- started_at: `{status_payload.get('started_at')}`",
        f"- finished_at: `{status_payload.get('finished_at')}`",
        f"- report_found: `{status_payload.get('report_found')}`",
        f"- eval_status_found: `{status_payload.get('eval_status_found')}`",
        f"- failure_found: `{status_payload.get('failure_found')}`",
        "",
        "## Logs Tail",
        "",
        "```text",
        str(status_payload.get("logs_tail", "")),
        "```",
    ]
    report = status_payload.get("report")
    if isinstance(report, dict):
        lines.extend(
            [
                "",
                "## Report",
                "",
                "```json",
                json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    eval_status = status_payload.get("eval_status")
    if isinstance(eval_status, dict):
        lines.extend(
            [
                "",
                "## Eval Status",
                "",
                "```json",
                json.dumps(eval_status, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    failure_text = status_payload.get("failure_text")
    if isinstance(failure_text, str) and failure_text.strip() != "":
        lines.extend(
            [
                "",
                "## Failure",
                "",
                "```text",
                failure_text.rstrip(),
                "```",
            ]
        )
    return "\n".join(lines)


def _load_launch(output_root: Path) -> DetachedQwenFallbackEvalLaunch:
    """Load one persisted detached Qwen fallback proof lane eval launch payload."""
    payload = json.loads(_launch_metadata_path(output_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Detached Qwen fallback proof lane eval launch metadata was malformed.")
    return DetachedQwenFallbackEvalLaunch(
        generated_at=_required_str(payload, "generated_at"),
        launch_id=_required_str(payload, "launch_id"),
        pid=_required_int(payload, "pid"),
        repo_root=_required_str(payload, "repo_root"),
        output_root=_required_str(payload, "output_root"),
        log_path=_required_str(payload, "log_path"),
        worker_status_path=_required_str(payload, "worker_status_path"),
        report_path=_required_str(payload, "report_path"),
        eval_status_path=_required_str(payload, "eval_status_path"),
        failure_path=_required_str(payload, "failure_path"),
        eval_args=_required_str_list(payload, "eval_args"),
        command=_required_str_list(payload, "command"),
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(
            f"Detached Qwen fallback proof lane eval metadata returned malformed `{key}`."
        )
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(
            f"Detached Qwen fallback proof lane eval metadata returned malformed `{key}`."
        )
    return value


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(
            f"Detached Qwen fallback proof lane eval metadata returned malformed `{key}`."
        )
    return list(value)


def main(argv: list[str] | None = None) -> int:
    """Launch or inspect the detached Qwen fallback proof lane fallback eval worker on Hemma."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    if args.command == "launch":
        for artifact_path in (
            _launch_metadata_path(output_root),
            _status_metadata_path(output_root),
            _status_markdown_path(output_root),
        ):
            with suppress(FileNotFoundError):
                artifact_path.unlink()
        launch = launch_detached_qwen_fallback_eval(
            output_root=output_root,
            repo_root=Path.cwd().resolve(),
            eval_args=args.eval_args,
            launch_id=args.launch_id,
        )
        payload = asdict(launch)
        _write_json(_launch_metadata_path(output_root), payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.command == "status":
        launch = _load_launch(output_root)
        status = inspect_detached_qwen_fallback_eval(launch)
        payload = asdict(status)
        with suppress(FileNotFoundError):
            _status_metadata_path(output_root).unlink()
        _write_json(_status_metadata_path(output_root), payload)
        _write_markdown(_status_markdown_path(output_root), _status_markdown(payload))
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    raise SystemExit(f"Unsupported detached Qwen fallback proof lane eval command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
