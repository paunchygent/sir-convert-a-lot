"""Terminal artifact object-store runtime configuration.

Purpose:
    Parse and validate the approved local/R2 terminal artifact storage backend
    without exposing secret values to logs, readiness, or retained proof.

Relationships:
    - Used by `runtime_config` to build `ServiceConfig`.
    - Used by `object_store_adapters` to choose local or R2 storage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from scripts.sir_convert_a_lot.infrastructure.object_store_models import ObjectStoreBackend

R2_REQUIRED_ENV_NAMES: tuple[str, ...] = (
    "SIR_CONVERT_A_LOT_R2_ENDPOINT_URL",
    "SIR_CONVERT_A_LOT_R2_REGION",
    "SIR_CONVERT_A_LOT_R2_BUCKET",
    "SIR_CONVERT_A_LOT_R2_ACCESS_KEY_ID",
    "SIR_CONVERT_A_LOT_R2_SECRET_ACCESS_KEY",
    "SIR_CONVERT_A_LOT_R2_KEY_PREFIX",
)


@dataclass(frozen=True)
class TerminalObjectStoreConfig:
    """Object-store configuration for terminal artifact blobs."""

    backend: ObjectStoreBackend = "local"
    key_prefix: str = "local"
    endpoint_url: str | None = None
    region: str | None = None
    bucket: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    force_path_style: bool = False

    def secret_source_labels(self) -> dict[str, str]:
        """Return redacted secret/config source labels for readiness proof."""
        if self.backend == "local":
            return {}
        return {
            name: "env:present"
            for name, value in (
                ("SIR_CONVERT_A_LOT_R2_ENDPOINT_URL", self.endpoint_url),
                ("SIR_CONVERT_A_LOT_R2_REGION", self.region),
                ("SIR_CONVERT_A_LOT_R2_BUCKET", self.bucket),
                ("SIR_CONVERT_A_LOT_R2_ACCESS_KEY_ID", self.access_key_id),
                ("SIR_CONVERT_A_LOT_R2_SECRET_ACCESS_KEY", self.secret_access_key),
                ("SIR_CONVERT_A_LOT_R2_KEY_PREFIX", self.key_prefix),
            )
            if value is not None and value.strip() != ""
        }


def terminal_object_store_config_from_env() -> TerminalObjectStoreConfig:
    """Parse approved object-store environment variables fail-closed."""
    backend_raw = os.getenv("SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND", "local").strip().lower()
    if backend_raw not in {"local", "r2"}:
        raise ValueError("Invalid SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND. Use one of: local, r2.")
    backend: ObjectStoreBackend = "r2" if backend_raw == "r2" else "local"
    if backend == "local":
        return TerminalObjectStoreConfig(
            backend="local",
            key_prefix=_optional_env("SIR_CONVERT_A_LOT_R2_KEY_PREFIX") or "local",
            force_path_style=_bool_env("SIR_CONVERT_A_LOT_R2_FORCE_PATH_STYLE", default=False),
        )

    missing = tuple(name for name in R2_REQUIRED_ENV_NAMES if _optional_env(name) is None)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required R2 object-store configuration: {joined}")
    return TerminalObjectStoreConfig(
        backend="r2",
        endpoint_url=_required_env("SIR_CONVERT_A_LOT_R2_ENDPOINT_URL"),
        region=_required_env("SIR_CONVERT_A_LOT_R2_REGION"),
        bucket=_required_env("SIR_CONVERT_A_LOT_R2_BUCKET"),
        access_key_id=_required_env("SIR_CONVERT_A_LOT_R2_ACCESS_KEY_ID"),
        secret_access_key=_required_env("SIR_CONVERT_A_LOT_R2_SECRET_ACCESS_KEY"),
        key_prefix=_required_env("SIR_CONVERT_A_LOT_R2_KEY_PREFIX"),
        force_path_style=_bool_env("SIR_CONVERT_A_LOT_R2_FORCE_PATH_STYLE", default=False),
    )


def _required_env(name: str) -> str:
    value = _optional_env(name)
    if value is None:
        raise ValueError(f"Missing required object-store configuration: {name}")
    return value


def _optional_env(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    return value if value != "" else None


def _bool_env(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value for {name}: {raw!r}.")
