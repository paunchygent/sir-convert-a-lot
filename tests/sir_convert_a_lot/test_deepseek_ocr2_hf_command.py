"""Tests for the DeepSeek-OCR-2 Hugging Face command adapter.

Purpose:
    Prove the Hemma-only DeepSeek-OCR-2 HF command adapter exposes the proven
    eager-attention runtime default without executing model inference locally.

Relationships:
    Exercises the specialist OCR command adapter command builder used by formula OCR adapter's
    formula
    candidate evaluation
    candidate replay integration.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops import deepseek_ocr2_hf_command


def test_hf_command_default_attention_is_eager() -> None:
    parser = deepseek_ocr2_hf_command.build_parser()

    args = parser.parse_args(["--input", "page.png", "--output-dir", "out"])

    assert args.attn_implementation == "eager"


def test_hf_docker_command_forwards_attention_to_inner_runner(tmp_path: Path) -> None:
    command = deepseek_ocr2_hf_command.build_docker_command(
        image="rocm/vllm:test",
        input_path=tmp_path / "page.png",
        output_dir=tmp_path / "out",
        repo_dir=tmp_path / "DeepSeek-OCR-2",
        host_cache=tmp_path / "cache",
        model="deepseek-ai/DeepSeek-OCR-2",
        prompt="<image>\n<|grounding|>Convert the document to markdown. ",
        attn_implementation="eager",
        timeout_seconds=900,
    )

    command_text = " ".join(command)

    assert "--attn-implementation eager" in command_text
    assert "--input /deepseek-ocr2/input.png" in command_text
    assert "--output-dir /deepseek-ocr2/output" in command_text
