"""GPU runtime probing utilities for Sir Convert-a-Lot infrastructure.

Purpose:
    Provide deterministic, exception-safe detection of the active torch GPU
    runtime so backend policy decisions can fail closed when GPU execution is
    requested but unavailable.

Relationships:
    - Used by `infrastructure.docling_backend` to enforce GPU runtime checks.
    - Used by Hemma verification scripts for deterministic runtime evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GpuRuntimeProbeResult:
    """Snapshot of torch GPU runtime availability and implementation details."""

    runtime_kind: Literal["rocm", "cuda", "none"]
    torch_version: str | None
    hip_version: str | None
    cuda_version: str | None
    is_available: bool
    device_count: int
    device_name: str | None

    def as_details(self) -> dict[str, object]:
        """Return deterministic detail payload used by error envelopes."""
        return {
            "runtime_kind": self.runtime_kind,
            "torch_version": self.torch_version,
            "hip_version": self.hip_version,
            "cuda_version": self.cuda_version,
            "is_available": self.is_available,
            "device_count": self.device_count,
            "device_name": self.device_name,
        }


def _runtime_kind_from_versions(
    hip_version: str | None, cuda_version: str | None
) -> Literal["rocm", "cuda", "none"]:
    if hip_version is not None and hip_version.strip() != "":
        return "rocm"
    if cuda_version is not None and cuda_version.strip() != "":
        return "cuda"
    return "none"


def probe_torch_gpu_runtime() -> GpuRuntimeProbeResult:
    """Return torch runtime probe results without raising exceptions."""
    try:
        import torch
    except Exception:
        return GpuRuntimeProbeResult(
            runtime_kind="none",
            torch_version=None,
            hip_version=None,
            cuda_version=None,
            is_available=False,
            device_count=0,
            device_name=None,
        )

    torch_version_obj = getattr(torch, "__version__", None)
    torch_version = str(torch_version_obj) if torch_version_obj is not None else None
    version_obj = getattr(torch, "version", None)
    hip_version_obj = getattr(version_obj, "hip", None) if version_obj is not None else None
    cuda_version_obj = getattr(version_obj, "cuda", None) if version_obj is not None else None
    hip_version = str(hip_version_obj) if hip_version_obj is not None else None
    cuda_version = str(cuda_version_obj) if cuda_version_obj is not None else None
    runtime_kind = _runtime_kind_from_versions(hip_version=hip_version, cuda_version=cuda_version)

    try:
        is_available = bool(torch.cuda.is_available())
    except Exception:
        is_available = False

    if not is_available:
        return GpuRuntimeProbeResult(
            runtime_kind=runtime_kind if runtime_kind in {"rocm", "cuda"} else "none",
            torch_version=torch_version,
            hip_version=hip_version,
            cuda_version=cuda_version,
            is_available=False,
            device_count=0,
            device_name=None,
        )

    try:
        device_count = int(torch.cuda.device_count())
    except Exception:
        device_count = 0

    device_name: str | None = None
    if device_count > 0:
        try:
            device_name_obj = torch.cuda.get_device_name(0)
            device_name = str(device_name_obj)
        except Exception:
            device_name = None

    return GpuRuntimeProbeResult(
        runtime_kind=runtime_kind if runtime_kind in {"rocm", "cuda"} else "none",
        torch_version=torch_version,
        hip_version=hip_version,
        cuda_version=cuda_version,
        is_available=True,
        device_count=device_count,
        device_name=device_name,
    )
