"""Regression tests for Hemma v2 smoke helper runtime probes.

Purpose:
    Lock the in-container command shape used by the Hemma Task 39 / Task 76
    smoke verifier so runtime-version checks match the deployed image contract.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions_helpers`.
    - Protects `pdm run hemma-deploy-and-verify` from false-negative runtime
      probe failures on Hemma.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops import verify_hemma_v2_conversions_helpers


def test_probe_docker_runtime_executes_weasyprint_with_python_directly(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[list[str], str]] = []

    def fake_run_checked(command: list[str], *, label: str) -> str:
        calls.append((command, label))
        if label == "docker ps":
            return "sir_convert_a_lot_prod\n"
        if label == "pandoc --version":
            return "pandoc 3.6.1"
        if label == "weasyprint version":
            return "68.1"
        raise AssertionError(f"unexpected label: {label}")

    monkeypatch.setattr(verify_hemma_v2_conversions_helpers, "run_checked", fake_run_checked)

    runtime_versions = verify_hemma_v2_conversions_helpers.probe_docker_runtime(
        prod_container="sir_convert_a_lot_prod",
        output_dir=tmp_path,
    )

    assert runtime_versions == {
        "pandoc_version": "pandoc 3.6.1",
        "weasyprint_version": "68.1",
    }
    weasyprint_command = calls[-1][0]
    assert weasyprint_command[:5] == [
        "sudo",
        "-n",
        "docker",
        "exec",
        "sir_convert_a_lot_prod",
    ]
    assert "pdm" not in weasyprint_command
    assert "python" in weasyprint_command
    assert (tmp_path / "pandoc_version.txt").read_text(encoding="utf-8") == "pandoc 3.6.1\n"
    assert (tmp_path / "weasyprint_version.txt").read_text(encoding="utf-8") == "68.1\n"


def test_count_pdf_image_objects_counts_embedded_image_markers() -> None:
    pdf_bytes = b"%PDF-1.7\n/Subtype /Image\nq\n/Subtype /Image\n"

    assert verify_hemma_v2_conversions_helpers.count_pdf_image_objects(pdf_bytes) == 2
