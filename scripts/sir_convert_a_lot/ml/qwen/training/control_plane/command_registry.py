"""Command-dispatch registry for the Qwen training control plane.

Purpose:
    Map parsed `qwen-train` commands to bounded use-case handlers so the CLI
    entrypoint remains a pure composition root.

Relationships:
    - Imported by the public CLI entrypoint.
    - Dispatches into the command-specific use-case modules.
"""

from __future__ import annotations

from .diagnose_use_case import handle_diagnose
from .eval_use_case import handle_eval
from .launch_use_case import handle_launch
from .resume_use_case import handle_resume
from .schedule_use_case import handle_schedule
from .status_use_case import handle_status
from .stop_use_case import handle_stop


def dispatch_command(args) -> int:
    """Dispatch one parsed command namespace into its bounded use case."""
    handlers = {
        "launch": handle_launch,
        "resume": handle_resume,
        "eval": handle_eval,
        "diagnose-non-finite": handle_diagnose,
        "schedule": handle_schedule,
        "status": handle_status,
        "stop": handle_stop,
    }
    command = str(args.command)
    try:
        handler = handlers[command]
    except KeyError as exc:
        raise SystemExit(f"Unsupported qwen-train command: {command}") from exc
    return handler(args)
