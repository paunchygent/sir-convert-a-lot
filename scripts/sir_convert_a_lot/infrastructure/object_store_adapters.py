"""Object-store adapters for terminal Sir Convert artifacts.

Purpose:
    Provide deterministic local and Cloudflare R2-backed implementations of
    the terminal artifact store port without leaking SDK details into routes or
    conversion workers.

Relationships:
    - Built by `runtime_engine_v2` from `TerminalObjectStoreConfig`.
    - Persists refs consumed by `job_store_v2` and HTTP artifact routes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from scripts.sir_convert_a_lot.infrastructure.object_store_config import (
    TerminalObjectStoreConfig,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_keys import (
    terminal_artifact_object_key,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    ObjectStoreBackend,
    ObjectStoreMissingError,
    ObjectStoreReadiness,
    ObjectStoreUnavailableError,
    TerminalArtifactObjectRef,
    TerminalArtifactRead,
    TerminalArtifactStore,
    TerminalArtifactWriteRequest,
)

_LOCAL_BUCKET = "local-terminal-artifacts"


def build_terminal_artifact_store(
    *,
    config: TerminalObjectStoreConfig,
    data_root: Path,
    runtime_profile: str,
) -> TerminalArtifactStore:
    """Build the configured terminal artifact store adapter."""
    if config.backend == "local":
        return LocalTerminalArtifactStore(
            data_root=data_root,
            key_prefix=config.key_prefix,
            runtime_profile=runtime_profile,
        )
    return R2TerminalArtifactStore(config=config, runtime_profile=runtime_profile)


@dataclass
class LocalTerminalArtifactStore:
    """Deterministic filesystem-backed object-store adapter for tests/local runs."""

    data_root: Path
    key_prefix: str
    runtime_profile: str
    backend: ObjectStoreBackend = "local"
    read_count: int = 0

    def put_artifact(self, request: TerminalArtifactWriteRequest) -> TerminalArtifactObjectRef:
        """Persist one artifact under the local object-store root."""
        digest = hashlib.sha256(request.payload).hexdigest()
        key = terminal_artifact_object_key(
            key_prefix=self.key_prefix,
            runtime_profile=self.runtime_profile,
            request=request,
            content_sha256=digest,
        )
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(request.payload)
        return TerminalArtifactObjectRef(
            backend="local",
            bucket=_LOCAL_BUCKET,
            key=key,
            content_type=request.content_type,
            size_bytes=len(request.payload),
            sha256=digest,
            artifact_class=request.artifact_class,
            artifact_key=request.artifact_key,
        )

    def read_artifact(self, ref: TerminalArtifactObjectRef) -> TerminalArtifactRead:
        """Read one local object-store artifact."""
        self.read_count += 1
        path = self._path_for_key(ref.key)
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ObjectStoreMissingError() from exc
        return TerminalArtifactRead(ref=ref, content=content)

    def readiness(self) -> ObjectStoreReadiness:
        """Return local adapter readiness by writing and reading a sentinel."""
        request = TerminalArtifactWriteRequest(
            job_id="readyz",
            route_key="readyz",
            owner_scope_sha256="readyz",
            artifact_class="sentinel",
            artifact_key="readyz",
            filename="readyz.txt",
            content_type="text/plain",
            payload=b"readyz",
        )
        try:
            ref = self.put_artifact(request)
            self.read_artifact(ref)
        except (OSError, ObjectStoreMissingError) as exc:
            return ObjectStoreReadiness(
                backend="local",
                config_ready=True,
                reachable=False,
                api_access="unreachable",
                worker_access="unreachable",
                secret_sources={},
                reason=exc.__class__.__name__,
            )
        return ObjectStoreReadiness(
            backend="local",
            config_ready=True,
            reachable=True,
            api_access="read_write",
            worker_access="read_write",
            secret_sources={},
        )

    def remove_for_test(self, ref: TerminalArtifactObjectRef) -> None:
        """Remove one local object; used only by deterministic route tests."""
        path = self._path_for_key(ref.key)
        if path.exists():
            path.unlink()

    def _path_for_key(self, key: str) -> Path:
        return self.data_root / "terminal_object_store" / key


class R2TerminalArtifactStore:
    """Cloudflare R2 implementation of the terminal artifact object-store port."""

    backend: ObjectStoreBackend = "r2"

    def __init__(self, *, config: TerminalObjectStoreConfig, runtime_profile: str) -> None:
        self._config = config
        self._runtime_profile = runtime_profile
        addressing_style = "path" if config.force_path_style else "virtual"
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            region_name=config.region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": addressing_style},
            ),
        )

    def put_artifact(self, request: TerminalArtifactWriteRequest) -> TerminalArtifactObjectRef:
        """Persist one terminal artifact object through the S3-compatible API."""
        bucket = self._bucket()
        digest = hashlib.sha256(request.payload).hexdigest()
        key = terminal_artifact_object_key(
            key_prefix=self._config.key_prefix,
            runtime_profile=self._runtime_profile,
            request=request,
            content_sha256=digest,
        )
        try:
            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=request.payload,
                ContentType=request.content_type,
                Metadata={
                    "schema_version": "terminal_artifact_object_v1",
                    "job_id": request.job_id,
                    "artifact_class": request.artifact_class,
                    "artifact_key": request.artifact_key,
                    "sha256": digest,
                },
            )
        except ClientError as exc:
            raise ObjectStoreUnavailableError() from exc
        return TerminalArtifactObjectRef(
            backend="r2",
            bucket=bucket,
            key=key,
            content_type=request.content_type,
            size_bytes=len(request.payload),
            sha256=digest,
            artifact_class=request.artifact_class,
            artifact_key=request.artifact_key,
        )

    def read_artifact(self, ref: TerminalArtifactObjectRef) -> TerminalArtifactRead:
        """Read one terminal artifact object through the S3-compatible API."""
        try:
            response = self._client.get_object(Bucket=ref.bucket, Key=ref.key)
            body = response["Body"]
            content = body.read()
        except ClientError as exc:
            if _client_error_is_missing(exc):
                raise ObjectStoreMissingError() from exc
            raise ObjectStoreUnavailableError() from exc
        if not isinstance(content, bytes):
            raise ObjectStoreUnavailableError()
        return TerminalArtifactRead(ref=ref, content=content)

    def readiness(self) -> ObjectStoreReadiness:
        """Return R2 readiness by writing and reading a scoped sentinel object."""
        request = TerminalArtifactWriteRequest(
            job_id="readyz",
            route_key="readyz",
            owner_scope_sha256="readyz",
            artifact_class="sentinel",
            artifact_key="readyz",
            filename="readyz.txt",
            content_type="text/plain",
            payload=b"readyz",
        )
        try:
            ref = self.put_artifact(request)
            self.read_artifact(ref)
        except (ObjectStoreMissingError, ObjectStoreUnavailableError) as exc:
            return ObjectStoreReadiness(
                backend="r2",
                config_ready=True,
                reachable=False,
                api_access="unreachable",
                worker_access="unreachable",
                secret_sources=self._config.secret_source_labels(),
                reason=exc.__class__.__name__,
            )
        return ObjectStoreReadiness(
            backend="r2",
            config_ready=True,
            reachable=True,
            api_access="read_write",
            worker_access="read_write",
            secret_sources=self._config.secret_source_labels(),
        )

    def _bucket(self) -> str:
        bucket = self._config.bucket
        if bucket is None or bucket.strip() == "":
            raise ObjectStoreUnavailableError()
        return bucket


def _client_error_is_missing(exc: ClientError) -> bool:
    code_obj = exc.response.get("Error", {}).get("Code")
    return code_obj in {"404", "NoSuchKey", "NotFound"}
