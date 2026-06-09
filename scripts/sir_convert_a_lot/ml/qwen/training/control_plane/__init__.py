"""Bounded control-plane package for Qwen training host-side commands.

Purpose:
    Expose the canonical parser and dispatch surfaces for Qwen training
    host-side commands.

Relationships:
    - Imported by the public CLI entrypoint.
    - Keeps command use cases separate from the public CLI entrypoint.
"""

from .command_registry import dispatch_command
from .parser import build_parser

__all__ = ["build_parser", "dispatch_command"]
