"""Dependency-injection ports for Qwen training metadata control-plane logic.

Purpose:
    Define stable port contracts for launch metadata loading, pointer
    resolution, artifact persistence, and status markdown projection.

Relationships:
    - Consumed by control-plane use cases and composition-root wiring.
    - Implemented by file-backed adapters in control-plane modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch, DetachedStatus


@dataclass(frozen=True)
class LaunchMetadataCompatibilityDefaults:
    """Default values for legacy launch-payload compatibility resolution."""

    default_throughput_profile_label: str
    default_legacy_small_batch_throughput_profile_label: str
    default_durable_checkpoint_retention: int
    default_durable_checkpoint_min_free_bytes: int
    default_dataloader_num_workers: int
    default_dataloader_pin_memory: bool
    default_dataloader_persistent_workers: bool
    default_dataloader_prefetch_factor: int
    default_non_blocking_transfer: bool
    default_data_path_proof_mode: bool
    default_heartbeat_interval_optimizer_steps: int
    default_eval_interval_steps: int
    default_finite_loss_max_consecutive_steps: int
    default_ref_mel_cache_enabled: bool
    default_ref_mel_cache_max_items: int
    default_torch_profiler_enabled: bool
    default_torch_profiler_wait_steps: int
    default_torch_profiler_warmup_steps: int
    default_torch_profiler_active_steps: int
    default_torch_profiler_repeat: int
    default_torch_profiler_record_shapes: bool
    default_torch_profiler_profile_memory: bool
    default_torch_profiler_with_stack: bool
    default_rocm_profiler_enabled: bool


class LaunchMetadataLoaderPort(Protocol):
    """Load one detached launch payload into the domain launch contract."""

    def load(
        self,
        launch_root_path: Path,
        *,
        defaults: LaunchMetadataCompatibilityDefaults,
    ) -> DetachedLaunch:
        """Load one persisted detached launch payload."""


class LaunchPointerResolverPort(Protocol):
    """Resolve launch/checkpoint pointers and explicit resume checkpoint ownership."""

    def resolve_launch_root(self, output_root: Path, launch_root_arg: Path | None) -> Path:
        """Resolve the effective launch root from args or latest-launch pointer."""

    def load_latest_checkpoint(self, run_root: Path) -> Path:
        """Resolve the latest-checkpoint pointer for one source run root."""

    def validate_resume_checkpoint_path(self, run_root: Path, checkpoint_path: Path) -> Path:
        """Validate explicit resume checkpoint ownership against one run root."""


class ArtifactWriterPort(Protocol):
    """Write deterministic metadata artifacts for detached control-plane flows."""

    def write_json(self, path: Path, payload: object) -> None:
        """Write one deterministic JSON artifact."""

    def write_markdown(self, path: Path, markdown: str) -> None:
        """Write one deterministic markdown artifact."""

    def write_latest_pointer(self, output_root: Path, launch_root_path: Path) -> None:
        """Persist the latest-launch pointer for status/stop default resolution."""


class StatusMarkdownRendererPort(Protocol):
    """Render detached status payloads into operator-facing markdown summaries."""

    def render(self, status: DetachedStatus) -> str:
        """Render one detached status markdown summary."""
