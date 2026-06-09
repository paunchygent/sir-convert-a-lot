"""Tests for the Task 347 DeepSeek-OCR-2 vLLM batch command adapter.

Purpose:
    Prove command construction for the Hemma-only vLLM adapter without running
    model inference outside Hemma.

Relationships:
    Exercises `scripts.sir_convert_a_lot.devops.task347_deepseek_ocr2_vllm_batch`
    as the DeepSeek batch command invoked by Task 346.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.task347_deepseek_ocr2_vllm_batch import (
    CONTAINER_CACHE,
    CONTAINER_INPUT_DIR,
    CONTAINER_OUTPUT_DIR,
    DEFAULT_IMAGE,
    build_docker_command,
    render_inner_runner,
)


def test_build_docker_command_uses_proven_rocm_vllm_lane(tmp_path: Path) -> None:
    command = build_docker_command(
        image=DEFAULT_IMAGE,
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        repo_dir=tmp_path / "repo",
        host_cache=tmp_path / "hf",
        model="deepseek-ai/DeepSeek-OCR-2",
        prompt="<image>\n<|grounding|>Convert the document to markdown.",
        max_model_len=8192,
        gpu_memory_utilization="0.70",
        block_size=16,
        enforce_eager=False,
        max_concurrency=1,
        num_workers=2,
        crop_mode=True,
        timeout_seconds=3600,
    )

    assert command[:4] == ["sudo", "-n", "docker", "run"]
    assert DEFAULT_IMAGE in command
    assert DEFAULT_IMAGE == "rocm/vllm:rocm6.3.1_vllm_0.8.5_20250521"
    assert "--device" in command
    assert "/dev/kfd" in command
    assert f"HF_HOME={CONTAINER_CACHE.as_posix()}" in command
    assert "VLLM_USE_V1=0" in command
    assert "PYTORCH_HIP_ALLOC_CONF=expandable_segments:True" in command
    assert f"{(tmp_path / 'input').as_posix()}:{CONTAINER_INPUT_DIR.as_posix()}:ro" in command
    assert f"{(tmp_path / 'output').as_posix()}:{CONTAINER_OUTPUT_DIR.as_posix()}" in command
    assert any("deepseek-ai/DeepSeek-OCR-2" in part for part in command)
    assert any("<image>" in part for part in command)
    assert any("--crop-mode" in part for part in command)
    assert any("--block-size 16" in part for part in command)
    assert any("--no-enforce-eager" in part for part in command)
    assert any("pip install -r /deepseek-ocr-2/requirements.txt" in part for part in command)


def test_inner_runner_uses_official_deepseek_vllm_model_registration() -> None:
    source = render_inner_runner()

    compile(source, "task347_deepseek_ocr2_vllm_inner.py", "exec")
    assert "ModelRegistry.register_model" in source
    assert "DeepseekOCR2ForCausalLM" in source
    assert "DeepseekOCR2Processor" in source
    assert "NoRepeatNGramLogitsProcessor" in source
    assert "LLM(" in source
    assert "disable_mm_preprocessor_cache=True" in source
    assert "enforce_eager=args.enforce_eager" in source
    assert "ngram_size=20" in source
    assert "window_size=50" in source
    assert "include_stop_str_in_output=True" in source
    assert "tokenize_with_images" in source


def test_inner_runner_adapts_deepseek_processor_to_vllm_08_hash_contract() -> None:
    source = render_inner_runner()

    assert "DeepseekOCR2MultiModalProcessor" in source
    assert "return_mm_hashes" in source
    assert "install_deepseek_vllm_08_processor_adapter()" in source
    assert "mm_hashes" in source
