"""Launch-metadata loading adapter scaffold for Qwen control-plane flows.

Purpose:
    Host the bounded, file-backed implementation that will deserialize
    `launch.json` payloads into `DetachedLaunch` with compatibility defaults.

Relationships:
    - Implements `LaunchMetadataLoaderPort`.
    - Used by `launch_loader.py` and all use cases that inspect prior launches.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch

from .metadata_ports import LaunchMetadataCompatibilityDefaults, LaunchMetadataLoaderPort


class JsonLaunchMetadataLoader(LaunchMetadataLoaderPort):
    """File-backed launch metadata loader.

    This scaffold intentionally has no runtime wiring yet. Task 200 owns the
    bounded deserialization implementation for launch metadata payloads.
    """

    def load(
        self,
        launch_root_path: Path,
        *,
        defaults: LaunchMetadataCompatibilityDefaults,
    ) -> DetachedLaunch:
        """Load one persisted detached launch payload from `launch.json`."""
        del launch_root_path
        del defaults
        raise NotImplementedError(
            "Task 200 implementation pending for launch metadata deserialization."
        )
