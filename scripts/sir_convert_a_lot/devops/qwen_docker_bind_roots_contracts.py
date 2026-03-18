"""Contracts for persistent Hemma Docker-visible Qwen bind roots.

Purpose:
    Define the canonical scratch-backed build/cache bind roots, the installable
    service contract, and the machine-readable reports for the permanent Hemma
    Docker bind-root surface.

Relationships:
    - Used by `qwen_docker_bind_roots_runtime.py` for service installation,
      inspection, and probe execution.
    - Used by `ml.qwen.common.runtime` to prefer installed persistent home bind
      roots over ad hoc fallback mounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.storage import DEFAULT_SCRATCH_BUILD_ROOT

DEFAULT_REPO_ROOT = Path("/home/paunchygent/apps/sir-convert-a-lot")
DEFAULT_HOME_BIND_ROOT = Path("/home/paunchygent/.data/sir-convert-a-lot")
DEFAULT_SERVICE_NAME = "sir-convert-a-lot-qwen-docker-bind-roots.service"
DEFAULT_SERVICE_PATH = Path("/etc/systemd/system") / DEFAULT_SERVICE_NAME
DEFAULT_OUTPUT_ROOT = Path("build/verification/task-242-hemma-qwen-docker-bind-roots")
DEFAULT_PROBE_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:task100"
DEFAULT_BUILD_CANONICAL_ROOT = DEFAULT_SCRATCH_BUILD_ROOT
DEFAULT_BUILD_HOME_ROOT = DEFAULT_HOME_BIND_ROOT / "build"
DEFAULT_CACHE_CANONICAL_ROOT = Path("/srv/scratch/sir-convert-a-lot/cache")
DEFAULT_CACHE_HOME_ROOT = DEFAULT_HOME_BIND_ROOT / "cache"


@dataclass(frozen=True)
class QwenDockerBindRoot:
    """One canonical scratch-backed root exposed through a Docker-visible home path."""

    label: str
    canonical_root: Path
    home_root: Path


@dataclass(frozen=True)
class QwenDockerBindRootsSettings:
    """Normalized settings for the permanent Hemma bind-root command surface."""

    repo_root: Path
    service_name: str
    service_path: Path
    probe_image: str
    bind_roots: tuple[QwenDockerBindRoot, ...]


@dataclass(frozen=True)
class QwenDockerBindRootState:
    """Observed host mount state for one canonical/home bind-root pair."""

    label: str
    canonical_root: str
    home_root: str
    canonical_exists: bool
    home_exists: bool
    mount_source: str | None
    mounted_expected_source: bool


@dataclass(frozen=True)
class QwenDockerBindRootsInstallReport:
    """Deterministic install/refresh report for the system bind-root service."""

    installed_at: str
    service_name: str
    service_path: str
    service_enabled: bool
    service_active: bool
    bind_roots: tuple[QwenDockerBindRootState, ...]


@dataclass(frozen=True)
class QwenDockerBindRootsStatusReport:
    """Current service and bind-root status for the permanent mount contract."""

    checked_at: str
    service_name: str
    service_path: str
    service_unit_exists: bool
    service_enabled: bool
    service_active: bool
    bind_roots: tuple[QwenDockerBindRootState, ...]


@dataclass(frozen=True)
class QwenDockerBindProbeResult:
    """Docker bind-mount probe result for one canonical/home bind-root pair."""

    label: str
    canonical_root: str
    home_root: str
    canonical_probe_ok: bool
    home_probe_ok: bool
    preferred_effective_root: str


@dataclass(frozen=True)
class QwenDockerBindRootsProbeReport:
    """Deterministic Docker bind-mount probe report for the permanent contract."""

    checked_at: str
    service_name: str
    probe_image: str
    probe_results: tuple[QwenDockerBindProbeResult, ...]


def default_bind_roots() -> tuple[QwenDockerBindRoot, ...]:
    """Return the canonical scratch-backed root mappings for Qwen workloads."""
    return (
        QwenDockerBindRoot(
            label="build",
            canonical_root=DEFAULT_BUILD_CANONICAL_ROOT,
            home_root=DEFAULT_BUILD_HOME_ROOT,
        ),
        QwenDockerBindRoot(
            label="cache",
            canonical_root=DEFAULT_CACHE_CANONICAL_ROOT,
            home_root=DEFAULT_CACHE_HOME_ROOT,
        ),
    )


def default_settings() -> QwenDockerBindRootsSettings:
    """Return the default persistent Hemma bind-root settings."""
    return QwenDockerBindRootsSettings(
        repo_root=DEFAULT_REPO_ROOT,
        service_name=DEFAULT_SERVICE_NAME,
        service_path=DEFAULT_SERVICE_PATH,
        probe_image=DEFAULT_PROBE_IMAGE,
        bind_roots=default_bind_roots(),
    )


def match_bind_root(
    canonical_path: Path,
    *,
    bind_roots: tuple[QwenDockerBindRoot, ...],
) -> tuple[QwenDockerBindRoot, Path] | None:
    """Return the matching bind-root pair and relative suffix for one canonical path."""
    for bind_root in bind_roots:
        try:
            relative_suffix = canonical_path.relative_to(bind_root.canonical_root)
        except ValueError:
            continue
        return bind_root, relative_suffix
    return None


def resolve_persistent_home_path(
    canonical_path: Path,
    *,
    bind_roots: tuple[QwenDockerBindRoot, ...],
) -> Path | None:
    """Map one canonical path onto the installed persistent home bind-root tree."""
    match = match_bind_root(canonical_path, bind_roots=bind_roots)
    if match is None:
        return None
    bind_root, relative_suffix = match
    return bind_root.home_root / relative_suffix
