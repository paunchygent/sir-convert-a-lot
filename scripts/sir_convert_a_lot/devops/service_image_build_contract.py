"""Service image build contract helpers.

Purpose:
    Centralize the runtime pin contracts and shell-export helpers used by the
    production ROCm image and the CPU-only local dev image.

Relationships:
    - Used by the root `Dockerfile` and `Dockerfile.local`
      dependency-builder stages.
    - Used by `verify_hemma_gpu_runtime.py` to read the expected torch pin.
    - Covered by `tests/sir_convert_a_lot/test_service_image_build_contract.py`.
"""

from __future__ import annotations

import shlex
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RocmRuntimeContract:
    """Pinned ROCm runtime values for the service image."""

    torch_index_url: str
    torch_version: str
    torchvision_version: str
    torchaudio_version: str

    def as_shell_exports(self) -> str:
        """Return POSIX-shell export lines for the pinned runtime values."""
        exports = {
            "SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL": self.torch_index_url,
            "SIR_CONVERT_A_LOT_TORCH_VERSION": self.torch_version,
            "SIR_CONVERT_A_LOT_TORCHVISION_VERSION": self.torchvision_version,
            "SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION": self.torchaudio_version,
        }
        return "".join(f"export {name}={shlex.quote(value)}\n" for name, value in exports.items())


@dataclass(frozen=True)
class CpuRuntimeContract:
    """Pinned CPU runtime values for the local development service image."""

    torch_version: str
    torchvision_version: str
    torchaudio_version: str

    def as_shell_exports(self) -> str:
        """Return POSIX-shell export lines for the pinned CPU runtime values."""
        exports = {
            "SIR_CONVERT_A_LOT_TORCH_VERSION": self.torch_version,
            "SIR_CONVERT_A_LOT_TORCHVISION_VERSION": self.torchvision_version,
            "SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION": self.torchaudio_version,
        }
        return "".join(f"export {name}={shlex.quote(value)}\n" for name, value in exports.items())


def _require_non_empty_string(value: object, *, field: str) -> str:
    """Validate that a pyproject field is a non-empty string."""
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"pyproject field must be a non-empty string: {field}")
    return value.strip()


def load_rocm_runtime_contract(project_root: Path) -> RocmRuntimeContract:
    """Load the canonical ROCm runtime build pins from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    runtime_obj = config["tool"]["sir_convert_a_lot"]["rocm_runtime"]
    if not isinstance(runtime_obj, dict):
        raise ValueError("pyproject tool.sir_convert_a_lot.rocm_runtime must be a table.")
    return RocmRuntimeContract(
        torch_index_url=_require_non_empty_string(
            runtime_obj.get("torch_index_url"),
            field="tool.sir_convert_a_lot.rocm_runtime.torch_index_url",
        ),
        torch_version=_require_non_empty_string(
            runtime_obj.get("torch_version"),
            field="tool.sir_convert_a_lot.rocm_runtime.torch_version",
        ),
        torchvision_version=_require_non_empty_string(
            runtime_obj.get("torchvision_version"),
            field="tool.sir_convert_a_lot.rocm_runtime.torchvision_version",
        ),
        torchaudio_version=_require_non_empty_string(
            runtime_obj.get("torchaudio_version"),
            field="tool.sir_convert_a_lot.rocm_runtime.torchaudio_version",
        ),
    )


def load_cpu_runtime_contract(project_root: Path) -> CpuRuntimeContract:
    """Load the canonical CPU runtime build pins from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    runtime_obj = config["tool"]["sir_convert_a_lot"]["cpu_runtime"]
    if not isinstance(runtime_obj, dict):
        raise ValueError("pyproject tool.sir_convert_a_lot.cpu_runtime must be a table.")
    return CpuRuntimeContract(
        torch_version=_require_non_empty_string(
            runtime_obj.get("torch_version"),
            field="tool.sir_convert_a_lot.cpu_runtime.torch_version",
        ),
        torchvision_version=_require_non_empty_string(
            runtime_obj.get("torchvision_version"),
            field="tool.sir_convert_a_lot.cpu_runtime.torchvision_version",
        ),
        torchaudio_version=_require_non_empty_string(
            runtime_obj.get("torchaudio_version"),
            field="tool.sir_convert_a_lot.cpu_runtime.torchaudio_version",
        ),
    )
