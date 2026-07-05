"""Terminal artifact object-store contracts.

Purpose:
    Define Sir Convert-owned object references, read/write payloads, readiness
    evidence, and adapter exceptions for terminal artifact blobs.

Relationships:
    - Used by `object_store_adapters` for local and R2 implementations.
    - Stored by `job_store_v2` in terminal result metadata.
    - Consumed by HTTP artifact routes after owner/grant authorization.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

ObjectStoreBackend = Literal["local", "r2"]
ObjectStoreAccessMode = Literal["read_write", "not_configured", "unreachable"]


@dataclass(frozen=True)
class TerminalArtifactObjectRef:
    """Opaque persisted object identity for one terminal artifact blob."""

    backend: ObjectStoreBackend
    bucket: str
    key: str
    content_type: str
    size_bytes: int
    sha256: str
    artifact_class: str
    artifact_key: str

    def to_json(self) -> dict[str, object]:
        """Return a manifest-safe JSON object without secret material."""
        return {
            "backend": self.backend,
            "bucket": self.bucket,
            "key": self.key,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "artifact_class": self.artifact_class,
            "artifact_key": self.artifact_key,
        }


@dataclass(frozen=True)
class TerminalArtifactWriteRequest:
    """Write intent for a terminal artifact object."""

    job_id: str
    route_key: str
    owner_scope_sha256: str
    artifact_class: str
    artifact_key: str
    filename: str
    content_type: str
    payload: bytes


@dataclass(frozen=True)
class TerminalArtifactRead:
    """Server-side artifact read result returned by object-store adapters."""

    ref: TerminalArtifactObjectRef
    content: bytes

    def iter_bytes(self) -> Iterator[bytes]:
        """Yield bytes for a streaming HTTP response."""
        yield self.content


@dataclass(frozen=True)
class ObjectStoreReadiness:
    """Redacted readiness evidence for configured object storage."""

    backend: ObjectStoreBackend
    config_ready: bool
    reachable: bool
    api_access: ObjectStoreAccessMode
    worker_access: ObjectStoreAccessMode
    secret_sources: dict[str, str]
    reason: str | None = None

    def to_json(self) -> dict[str, object]:
        """Return readiness fields safe for `/readyz` and retained proof."""
        return {
            "backend": self.backend,
            "config_ready": self.config_ready,
            "reachable": self.reachable,
            "api_access": self.api_access,
            "worker_access": self.worker_access,
            "secret_sources": dict(self.secret_sources),
            "reason": self.reason,
        }


class ObjectStoreMissingError(Exception):
    """Raised when a referenced terminal artifact object is absent."""


class ObjectStoreUnavailableError(Exception):
    """Raised when object storage cannot serve the requested operation."""


@runtime_checkable
class TerminalArtifactStore(Protocol):
    """Port for terminal artifact object persistence and reads."""

    backend: ObjectStoreBackend

    def put_artifact(self, request: TerminalArtifactWriteRequest) -> TerminalArtifactObjectRef:
        """Persist one artifact and return its opaque object reference."""

    def read_artifact(self, ref: TerminalArtifactObjectRef) -> TerminalArtifactRead:
        """Read one artifact through the object-store boundary."""

    def readiness(self) -> ObjectStoreReadiness:
        """Return redacted adapter readiness evidence."""


def terminal_artifact_object_ref_from_json(
    payload: object,
) -> TerminalArtifactObjectRef | None:
    """Parse a persisted object reference, returning None for absent refs."""
    if not isinstance(payload, dict):
        return None
    backend_obj = payload.get("backend")
    bucket_obj = payload.get("bucket")
    key_obj = payload.get("key")
    content_type_obj = payload.get("content_type")
    size_obj = payload.get("size_bytes")
    sha_obj = payload.get("sha256")
    class_obj = payload.get("artifact_class")
    artifact_key_obj = payload.get("artifact_key")
    if backend_obj not in {"local", "r2"}:
        return None
    if not isinstance(bucket_obj, str) or bucket_obj.strip() == "":
        return None
    if not isinstance(key_obj, str) or key_obj.strip() == "":
        return None
    if not isinstance(content_type_obj, str) or content_type_obj.strip() == "":
        return None
    if not isinstance(size_obj, int) or isinstance(size_obj, bool) or size_obj < 0:
        return None
    if not isinstance(sha_obj, str) or sha_obj.strip() == "":
        return None
    if not isinstance(class_obj, str) or class_obj.strip() == "":
        return None
    if not isinstance(artifact_key_obj, str) or artifact_key_obj.strip() == "":
        return None
    return TerminalArtifactObjectRef(
        backend=backend_obj,
        bucket=bucket_obj,
        key=key_obj,
        content_type=content_type_obj,
        size_bytes=size_obj,
        sha256=sha_obj,
        artifact_class=class_obj,
        artifact_key=artifact_key_obj,
    )
