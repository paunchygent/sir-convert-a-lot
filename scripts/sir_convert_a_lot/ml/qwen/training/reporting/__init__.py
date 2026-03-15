"""Bounded reporting package for Qwen training artifacts.

Purpose:
    Expose the canonical reporting and status-writing surfaces after splitting
    the old umbrella reporting module into focused owners.

Relationships:
    - Imported by the trainer entrypoint, evaluator, and reporting tests.
    - Replaces the former mixed-concern `training.reporting` module.
"""

from .artifact_io import merge_launch_tracking_metadata, write_json
from .config import StatusReporterConfig
from .report_builders import build_failed_training_report, build_training_report
from .status_writer import StatusReporter

__all__ = [
    "StatusReporter",
    "StatusReporterConfig",
    "build_failed_training_report",
    "build_training_report",
    "merge_launch_tracking_metadata",
    "write_json",
]
