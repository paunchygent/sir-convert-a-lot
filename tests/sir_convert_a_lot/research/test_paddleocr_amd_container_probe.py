"""Tests for the AMD PaddleOCR container probe native AMD PaddleOCR container probe.

Purpose:
    Prove the governed command contract for the Hemma-only PaddleOCR/PaddleX
    AMD GPU container probe without running model inference locally.

Relationships:
    Exercises `scripts.sir_convert_a_lot.devops.paddleocr_amd_container_probe`
    as the runtime-inventory and formula-recognition smoke surface for AMD PaddleOCR container
    probe.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.paddleocr_amd_container_probe import (
    DEFAULT_IMAGE,
    build_docker_command,
    render_inner_probe,
)


def test_build_docker_command_uses_official_amd_gpu_container(tmp_path: Path) -> None:
    command = build_docker_command(
        image=DEFAULT_IMAGE,
        input_path=tmp_path / "crop.png",
        output_dir=tmp_path / "out",
        model_name="PP-FormulaNet_plus-S",
        entrypoint_bash=False,
        inventory_only=True,
        timeout_seconds=900,
    )

    joined = " ".join(command)
    assert DEFAULT_IMAGE == (
        "ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest-amd-gpu"
    )
    assert command[:4] == ["sudo", "-n", "docker", "run"]
    assert "--device" in command
    assert "/dev:/dev" in command
    assert "--shm-size" in command
    assert "64g" in command
    assert DEFAULT_IMAGE in command
    assert "--model-name PP-FormulaNet_plus-S" in command[-1]
    assert "--inventory-only" in command[-1]
    assert "zluda" not in joined.lower()
    assert "scale" not in joined.lower()
    assert "cuda shim" not in joined.lower()


def test_build_docker_command_can_override_service_first_entrypoint(
    tmp_path: Path,
) -> None:
    command = build_docker_command(
        image=DEFAULT_IMAGE,
        input_path=tmp_path / "crop.png",
        output_dir=tmp_path / "out",
        model_name="PP-FormulaNet_plus-M",
        entrypoint_bash=True,
        inventory_only=True,
        timeout_seconds=900,
    )

    image_index = command.index(DEFAULT_IMAGE)
    entrypoint_index = command.index("--entrypoint")
    assert entrypoint_index < image_index
    assert command[entrypoint_index + 1] == "/bin/bash"


def test_inner_probe_collects_runtime_and_formula_api_without_shims() -> None:
    source = render_inner_probe()

    compile(source, "paddleocr-amd_paddleocr_amd_inner_probe.py", "exec")
    assert "is_compiled_with_rocm" in source
    assert "is_compiled_with_cuda" in source
    assert "FormulaRecognitionPipeline" in source
    assert "FormulaRecognition" in source
    assert source.index('"FormulaRecognition"') < source.index('"FormulaRecognitionPipeline"')
    assert "PP-FormulaNet_plus-M" in source
    assert "PP-FormulaNet_plus-S" in source
    assert "model_name" in source
    assert "paddleocr-amd-paddleocr-amd-probe.json" in source
    assert "zluda" not in source.lower()
    assert "SCALE" not in source
