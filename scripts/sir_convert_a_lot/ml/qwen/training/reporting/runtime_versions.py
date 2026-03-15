"""Runtime version helpers for Qwen training reports.

Purpose:
    Centralize package/runtime version lookup and runtime-capability projection
    used by machine-readable training reports.

Relationships:
    - Used by `report_builders`.
    - Keeps environment discovery out of status and failure-projection logic.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
from typing import TypedDict

import torch


class RuntimeEnvironmentPayload(TypedDict):
    """Typed runtime-environment payload shared by training report builders."""

    torch_version: str
    torchaudio_version: str | None
    torch_cuda_available: bool
    torch_cuda_device_count: int
    torch_hip_version: str
    flash_attn_importable: bool
    flash_attn_version: str | None


def package_version(distribution_name: str) -> str | None:
    """Return one installed package version, or `None` when it is absent."""
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def runtime_environment_payload() -> RuntimeEnvironmentPayload:
    """Return the runtime environment payload shared by report builders."""
    return {
        "torch_version": str(torch.__version__),
        "torchaudio_version": package_version("torchaudio"),
        "torch_cuda_available": True,
        "torch_cuda_device_count": int(torch.cuda.device_count()),
        "torch_hip_version": str(torch.version.hip),
        "flash_attn_importable": importlib.util.find_spec("flash_attn") is not None,
        "flash_attn_version": package_version("flash-attn"),
    }
