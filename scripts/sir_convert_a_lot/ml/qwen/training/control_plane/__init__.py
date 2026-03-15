"""Bounded control-plane package for Qwen training host-side commands.

Purpose:
    Expose the canonical parser and dispatch surfaces after splitting the old
    `qwen_train.py` god file into focused use-case and policy modules.

Relationships:
    - Imported by the public CLI entrypoint.
    - Shared across launch, resume, eval, schedule, diagnose, status, and stop.
"""

from .command_registry import dispatch_command
from .parser import build_parser

__all__ = ["build_parser", "dispatch_command"]
