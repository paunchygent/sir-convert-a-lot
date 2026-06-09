"""Tests for the Task 347 PaddleOCR formula command adapter.

Purpose:
    Prove the command parser contract without running PaddleOCR inference
    outside Hemma.

Relationships:
    Exercises `scripts.sir_convert_a_lot.devops.task347_paddle_formula_command`
    as the Paddle template command used by Task 346.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.devops.task347_paddle_formula_command import build_parser


def test_parser_requires_input_output_and_model_with_gpu_default() -> None:
    args = build_parser().parse_args(
        [
            "--input",
            "crop.png",
            "--output-dir",
            "out",
            "--model-name",
            "PP-FormulaNet_plus-S",
        ]
    )

    assert args.input.name == "crop.png"
    assert args.output_dir.name == "out"
    assert args.model_name == "PP-FormulaNet_plus-S"
    assert args.device == "gpu"
