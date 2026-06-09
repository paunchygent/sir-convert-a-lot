"""Tests for Hemma GPU runtime verification helpers.

Purpose:
    Guard parser behavior used by the deploy-time GPU verification flow so
    `rocm-smi` sampling reflects real GPU busy signals.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime`.
    - Protects Hemma deploy verification live verification accuracy.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.devops import verify_hemma_gpu_runtime
from scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime import _extract_gpu_busy_peak


def test_extract_gpu_busy_peak_reads_max_busy_value() -> None:
    smi_output = (
        "GPU[0]\t\t: GPU use (%): 3\nGPU[1]\t\t: GPU use (%): 67\nGPU[2]\t\t: GPU use (%): 42\n"
    )

    assert _extract_gpu_busy_peak(smi_output) == 67


def test_extract_gpu_busy_peak_returns_zero_when_metric_missing() -> None:
    smi_output = "GPU[0]\t\t: VRAM Total Used Memory (B): 3072180224\n"

    assert _extract_gpu_busy_peak(smi_output) == 0


def test_probe_torch_runtime_in_docker_executes_python_directly(monkeypatch) -> None:
    calls: list[tuple[list[str], str]] = []

    def fake_run_checked(command: list[str], *, label: str) -> str:
        calls.append((command, label))
        if label == "docker ps":
            return "sir_convert_a_lot_prod\n"
        if label in {"docker /dev/kfd check", "docker /dev/dri check"}:
            return ""
        if label == "docker torch runtime probe":
            return (
                '{"is_available": true, "runtime_kind": "rocm", '
                '"torch_version": "2.10.0+rocm7.1"}\n'
            )
        raise AssertionError(f"unexpected label: {label}")

    monkeypatch.setattr(verify_hemma_gpu_runtime, "_run_checked", fake_run_checked)

    result = verify_hemma_gpu_runtime._probe_torch_runtime_in_docker(
        container="sir_convert_a_lot_prod",
        expected_torch_version="2.10.0+rocm7.1",
    )

    assert result.runtime_kind == "rocm"
    probe_command = calls[-1][0]
    assert probe_command[:5] == ["sudo", "-n", "docker", "exec", "sir_convert_a_lot_prod"]
    assert "pdm" not in probe_command
    assert "python" in probe_command
