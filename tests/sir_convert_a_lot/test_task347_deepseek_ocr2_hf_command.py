"""Tests for the DeepSeek-OCR-2 Hugging Face command adapter.

Purpose:
    Prove the Hemma-only DeepSeek-OCR-2 HF command adapter exposes the proven
    eager-attention runtime default without executing model inference locally.

Relationships:
    Exercises the Task 347 command builder used by Task 350's Task 346
    candidate replay integration.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops import task347_deepseek_ocr2_hf_command


def test_hf_command_default_attention_is_eager() -> None:
    parser = task347_deepseek_ocr2_hf_command.build_parser()

    args = parser.parse_args(["--input", "page.png", "--output-dir", "out"])

    assert args.attn_implementation == "eager"


def test_hf_docker_command_forwards_attention_to_inner_runner(tmp_path: Path) -> None:
    command = task347_deepseek_ocr2_hf_command.build_docker_command(
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
    assert "--input /task347/input.png" in command_text
    assert "--output-dir /task347/output" in command_text
