"""Tests for the service image build contract helpers.

Purpose:
    Guard the canonical ROCm runtime pin contract used by the service image
    build and deploy-time verification surfaces.

Relationships:
    - Covers `scripts.sir_convert_a_lot.devops.service_image_build_contract`.
    - Supports the root `Dockerfile` and Hemma GPU runtime verification flow.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.service_image_build_contract import (
    RocmRuntimeContract,
    load_rocm_runtime_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_load_rocm_runtime_contract_reads_current_pyproject_pins() -> None:
    contract = load_rocm_runtime_contract(REPO_ROOT)

    assert contract.torch_index_url == "https://download.pytorch.org/whl/rocm7.1"
    assert contract.torch_version == "2.10.0+rocm7.1"
    assert contract.torchvision_version == "0.25.0+rocm7.1"
    assert contract.torchaudio_version == "2.10.0+rocm7.1"


def test_rocm_runtime_contract_emits_shell_exports_for_docker_build_steps() -> None:
    contract = RocmRuntimeContract(
        torch_index_url="https://example.invalid/simple",
        torch_version="2.0.0+rocmX",
        torchvision_version="0.1.0+rocmX",
        torchaudio_version="0.2.0+rocmX",
    )

    shell_exports = contract.as_shell_exports()

    assert (
        "export SIR_CONVERT_A_LOT_TORCH_ROCM_INDEX_URL=https://example.invalid/simple\n"
        in shell_exports
    )
    assert "export SIR_CONVERT_A_LOT_TORCH_VERSION=2.0.0+rocmX\n" in shell_exports
    assert "export SIR_CONVERT_A_LOT_TORCHVISION_VERSION=0.1.0+rocmX\n" in shell_exports
    assert "export SIR_CONVERT_A_LOT_TORCHAUDIO_VERSION=0.2.0+rocmX\n" in shell_exports
