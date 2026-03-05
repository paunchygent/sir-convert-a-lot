"""Tests for Hemma GPU runtime verification helpers.

Purpose:
    Guard parser behavior used by the deploy-time GPU verification flow so
    `rocm-smi` sampling reflects real GPU busy signals.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime`.
    - Protects Task 76 live verification accuracy.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime import _extract_gpu_busy_peak


def test_extract_gpu_busy_peak_reads_max_busy_value() -> None:
    smi_output = (
        "GPU[0]\t\t: GPU use (%): 3\nGPU[1]\t\t: GPU use (%): 67\nGPU[2]\t\t: GPU use (%): 42\n"
    )

    assert _extract_gpu_busy_peak(smi_output) == 67


def test_extract_gpu_busy_peak_returns_zero_when_metric_missing() -> None:
    smi_output = "GPU[0]\t\t: VRAM Total Used Memory (B): 3072180224\n"

    assert _extract_gpu_busy_peak(smi_output) == 0
