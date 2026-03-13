"""Data contracts and stable identifiers for the detached Task 101 pilot lane.

Purpose:
    Centralize the immutable Task 101 runtime dataclasses and deterministic
    identifier/path helpers shared across the detached launcher, runtime, and
    metadata surfaces.

Relationships:
    - Imported by `task101_qwen_pilot_runtime.py` for the Docker-facing runtime
      orchestration.
    - Reused by the detached launcher metadata helper and related tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Task101PilotSettings:
    """Normalized settings for the detached Task 101 Hemma pilot."""

    output_root: Path
    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    scratch_build_root: Path
    scratch_build_home_mount: Path
    pilot_bundle_root: Path
    runs_root: Path
    model_id: str
    train_manifest_family: str
    eval_manifest_family: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int
    checkpoint_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    dataloader_num_workers: int = 4
    dataloader_pin_memory: bool = True
    dataloader_persistent_workers: bool = True
    dataloader_prefetch_factor: int = 4
    non_blocking_transfer: bool = True
    ref_mel_cache_enabled: bool = True
    ref_mel_cache_max_items: int = 2048
    torch_profiler_enabled: bool = False
    torch_profiler_wait_steps: int = 1
    torch_profiler_warmup_steps: int = 1
    torch_profiler_active_steps: int = 4
    torch_profiler_repeat: int = 1
    torch_profiler_record_shapes: bool = True
    torch_profiler_profile_memory: bool = True
    torch_profiler_with_stack: bool = False
    rocm_profiler_enabled: bool = False


@dataclass(frozen=True)
class Task101PilotSettingsSnapshot:
    """JSON-serializable snapshot of one Task 101 pilot configuration."""

    output_root: str
    image: str
    hf_cache_dir: str
    hf_cache_home_mount: str
    scratch_build_root: str
    scratch_build_home_mount: str
    pilot_bundle_root: str
    runs_root: str
    model_id: str
    train_manifest_family: str
    eval_manifest_family: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int
    checkpoint_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    dataloader_num_workers: int = 4
    dataloader_pin_memory: bool = True
    dataloader_persistent_workers: bool = True
    dataloader_prefetch_factor: int = 4
    non_blocking_transfer: bool = True
    ref_mel_cache_enabled: bool = True
    ref_mel_cache_max_items: int = 2048
    torch_profiler_enabled: bool = False
    torch_profiler_wait_steps: int = 1
    torch_profiler_warmup_steps: int = 1
    torch_profiler_active_steps: int = 4
    torch_profiler_repeat: int = 1
    torch_profiler_record_shapes: bool = True
    torch_profiler_profile_memory: bool = True
    torch_profiler_with_stack: bool = False
    rocm_profiler_enabled: bool = False


@dataclass(frozen=True)
class Task101DetachedLaunch:
    """Deterministic launch metadata for one detached Task 101 pilot."""

    generated_at: str
    launch_id: str
    container_name: str
    container_id: str
    repo_root: str
    run_root: str
    pilot_bundle_root: str
    train_jsonl: str
    eval_jsonl: str
    train_manifest_family: str
    eval_manifest_family: str
    dockerfile_path: str | None
    resumed_from_checkpoint_path: str | None
    settings: Task101PilotSettingsSnapshot
    command: list[str]
    tracking: dict[str, object] | None = None
    resource_monitor: dict[str, object] | None = None


@dataclass(frozen=True)
class Task101DetachedStatus:
    """Deterministic status view for one detached Task 101 pilot."""

    checked_at: str
    launch_id: str
    container_name: str
    container_id: str
    status: str
    running: bool
    exit_code: int
    oom_killed: bool
    started_at: str
    finished_at: str
    pilot_status_found: bool
    pilot_status: dict[str, object] | None
    pilot_report_found: bool
    pilot_report: dict[str, object] | None
    latest_checkpoint_found: bool
    latest_checkpoint: dict[str, object] | None
    logs_tail: str
    resource_monitor: dict[str, object] | None = None


@dataclass(frozen=True)
class Task101DetachedStop:
    """Deterministic stop result for one detached Task 101 pilot container."""

    stopped_at: str
    launch_id: str
    container_name: str
    container_id: str
    stop_output: str


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_launch_id() -> str:
    """Return one deterministic launch identifier for the detached pilot."""
    return f"task101-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"


def default_container_name(launch_id: str) -> str:
    """Return the canonical detached container name for one launch id."""
    return f"{launch_id}-container"


def run_root_for_launch(settings: Task101PilotSettings, *, launch_id: str) -> Path:
    """Return the scratch-backed run root for one detached pilot launch."""
    return settings.runs_root / launch_id


def snapshot_settings(settings: Task101PilotSettings) -> Task101PilotSettingsSnapshot:
    """Convert one runtime settings object into a JSON-safe snapshot."""
    return Task101PilotSettingsSnapshot(
        output_root=settings.output_root.as_posix(),
        image=settings.image,
        hf_cache_dir=settings.hf_cache_dir.as_posix(),
        hf_cache_home_mount=settings.hf_cache_home_mount.as_posix(),
        scratch_build_root=settings.scratch_build_root.as_posix(),
        scratch_build_home_mount=settings.scratch_build_home_mount.as_posix(),
        pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
        runs_root=settings.runs_root.as_posix(),
        model_id=settings.model_id,
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
        batch_size=settings.batch_size,
        lr=settings.lr,
        num_epochs=settings.num_epochs,
        max_steps=settings.max_steps,
        checkpoint_interval_steps=settings.checkpoint_interval_steps,
        durable_checkpoint_retention=settings.durable_checkpoint_retention,
        durable_checkpoint_min_free_bytes=settings.durable_checkpoint_min_free_bytes,
        dataloader_num_workers=settings.dataloader_num_workers,
        dataloader_pin_memory=settings.dataloader_pin_memory,
        dataloader_persistent_workers=settings.dataloader_persistent_workers,
        dataloader_prefetch_factor=settings.dataloader_prefetch_factor,
        non_blocking_transfer=settings.non_blocking_transfer,
        ref_mel_cache_enabled=settings.ref_mel_cache_enabled,
        ref_mel_cache_max_items=settings.ref_mel_cache_max_items,
        torch_profiler_enabled=settings.torch_profiler_enabled,
        torch_profiler_wait_steps=settings.torch_profiler_wait_steps,
        torch_profiler_warmup_steps=settings.torch_profiler_warmup_steps,
        torch_profiler_active_steps=settings.torch_profiler_active_steps,
        torch_profiler_repeat=settings.torch_profiler_repeat,
        torch_profiler_record_shapes=settings.torch_profiler_record_shapes,
        torch_profiler_profile_memory=settings.torch_profiler_profile_memory,
        torch_profiler_with_stack=settings.torch_profiler_with_stack,
        rocm_profiler_enabled=settings.rocm_profiler_enabled,
    )


def settings_from_snapshot(snapshot: Task101PilotSettingsSnapshot) -> Task101PilotSettings:
    """Rehydrate runtime settings from one launch metadata snapshot."""
    return Task101PilotSettings(
        output_root=Path(snapshot.output_root),
        image=snapshot.image,
        hf_cache_dir=Path(snapshot.hf_cache_dir),
        hf_cache_home_mount=Path(snapshot.hf_cache_home_mount),
        scratch_build_root=Path(snapshot.scratch_build_root),
        scratch_build_home_mount=Path(snapshot.scratch_build_home_mount),
        pilot_bundle_root=Path(snapshot.pilot_bundle_root),
        runs_root=Path(snapshot.runs_root),
        model_id=snapshot.model_id,
        train_manifest_family=snapshot.train_manifest_family,
        eval_manifest_family=snapshot.eval_manifest_family,
        batch_size=snapshot.batch_size,
        lr=snapshot.lr,
        num_epochs=snapshot.num_epochs,
        max_steps=snapshot.max_steps,
        checkpoint_interval_steps=snapshot.checkpoint_interval_steps,
        durable_checkpoint_retention=snapshot.durable_checkpoint_retention,
        durable_checkpoint_min_free_bytes=snapshot.durable_checkpoint_min_free_bytes,
        dataloader_num_workers=snapshot.dataloader_num_workers,
        dataloader_pin_memory=snapshot.dataloader_pin_memory,
        dataloader_persistent_workers=snapshot.dataloader_persistent_workers,
        dataloader_prefetch_factor=snapshot.dataloader_prefetch_factor,
        non_blocking_transfer=snapshot.non_blocking_transfer,
        ref_mel_cache_enabled=snapshot.ref_mel_cache_enabled,
        ref_mel_cache_max_items=snapshot.ref_mel_cache_max_items,
        torch_profiler_enabled=snapshot.torch_profiler_enabled,
        torch_profiler_wait_steps=snapshot.torch_profiler_wait_steps,
        torch_profiler_warmup_steps=snapshot.torch_profiler_warmup_steps,
        torch_profiler_active_steps=snapshot.torch_profiler_active_steps,
        torch_profiler_repeat=snapshot.torch_profiler_repeat,
        torch_profiler_record_shapes=snapshot.torch_profiler_record_shapes,
        torch_profiler_profile_memory=snapshot.torch_profiler_profile_memory,
        torch_profiler_with_stack=snapshot.torch_profiler_with_stack,
        rocm_profiler_enabled=snapshot.rocm_profiler_enabled,
    )
