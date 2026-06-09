"""Run a Hemma-only DeepSeek-OCR-2 Hugging Face control inference.

Purpose:
    Provide a minimal control lane for Task 347 that runs the official
    DeepSeek-OCR-2 `AutoModel.infer` path against one rendered page image.

Relationships:
    - Complements the Task 347 vLLM adapter by separating model/input quality
      from vLLM/ROCm decode behavior.
    - Uses the same Hemma ROCm Docker/cache conventions as the vLLM probe.
    - Writes plain artifacts under the caller-provided verification directory.
"""

from __future__ import annotations

import argparse
import json
import platform
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.devops.task347_deepseek_ocr2_vllm_batch import (
    CONTAINER_CACHE,
    DEFAULT_DEEPSEEK_REPO_URL,
    DEFAULT_HOST_CACHE,
    DEFAULT_IMAGE,
    DEFAULT_MODEL,
    DEFAULT_PROMPT,
    DEFAULT_WORKSPACE_ROOT,
    HEMMA_RENDER_GROUP_ID,
    HEMMA_VIDEO_GROUP_ID,
    ensure_deepseek_repo,
)

CONTAINER_INPUT_PATH = Path("/task347/input.png")
CONTAINER_OUTPUT_DIR = Path("/task347/output")
CONTAINER_REPO_DIR = Path("/deepseek-ocr-2")
CONTAINER_RUNNER_PATH = Path("/task347/output/task347_deepseek_ocr2_hf_inner.py")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Hugging Face control command."""
    args = build_parser().parse_args(argv)
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    repo_dir = Path(args.deepseek_repo_dir).resolve()
    host_cache = Path(args.host_cache).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    host_cache.mkdir(parents=True, exist_ok=True)
    ensure_deepseek_repo(repo_dir=repo_dir, repo_url=str(args.deepseek_repo_url))
    (output_dir / "task347_deepseek_ocr2_hf_inner.py").write_text(
        render_inner_runner(),
        encoding="utf-8",
    )
    command = build_docker_command(
        image=str(args.image),
        input_path=input_path,
        output_dir=output_dir,
        repo_dir=repo_dir,
        host_cache=host_cache,
        model=str(args.model),
        prompt=str(args.prompt),
        attn_implementation=str(args.attn_implementation),
        timeout_seconds=int(args.inner_timeout_seconds),
    )
    metadata = {
        "schema_version": "task347_deepseek_ocr2_hf_host_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "hostname": platform.node(),
        "input_path": input_path.as_posix(),
        "output_dir": output_dir.as_posix(),
        "image": str(args.image),
        "model": str(args.model),
        "attn_implementation": str(args.attn_implementation),
        "command": command,
    }
    (output_dir / "task347-hf-host-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        command,
        check=False,
        text=True,
        timeout=float(args.host_timeout_seconds),
    )
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument(
        "--deepseek-repo-dir",
        type=Path,
        default=DEFAULT_WORKSPACE_ROOT / "DeepSeek-OCR-2",
    )
    parser.add_argument("--deepseek-repo-url", default=DEFAULT_DEEPSEEK_REPO_URL)
    parser.add_argument("--host-cache", type=Path, default=DEFAULT_HOST_CACHE)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT + " ")
    parser.add_argument("--attn-implementation", default="eager")
    parser.add_argument("--inner-timeout-seconds", type=int, default=3600)
    parser.add_argument("--host-timeout-seconds", type=int, default=4200)
    return parser


def build_docker_command(
    *,
    image: str,
    input_path: Path,
    output_dir: Path,
    repo_dir: Path,
    host_cache: Path,
    model: str,
    prompt: str,
    attn_implementation: str,
    timeout_seconds: int,
) -> list[str]:
    """Build the Docker command for the Hemma ROCm HF control lane."""
    runner_command = [
        "timeout",
        str(timeout_seconds),
        "python",
        CONTAINER_RUNNER_PATH.as_posix(),
        "--input",
        CONTAINER_INPUT_PATH.as_posix(),
        "--output-dir",
        CONTAINER_OUTPUT_DIR.as_posix(),
        "--model",
        model,
        "--prompt",
        prompt,
        "--attn-implementation",
        attn_implementation,
    ]
    return [
        "sudo",
        "-n",
        "docker",
        "run",
        "--rm",
        "--ipc=host",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
        "--group-add",
        HEMMA_VIDEO_GROUP_ID,
        "--group-add",
        HEMMA_RENDER_GROUP_ID,
        "-v",
        f"{input_path.as_posix()}:{CONTAINER_INPUT_PATH.as_posix()}:ro",
        "-v",
        f"{output_dir.as_posix()}:{CONTAINER_OUTPUT_DIR.as_posix()}",
        "-v",
        f"{repo_dir.as_posix()}:{CONTAINER_REPO_DIR.as_posix()}:ro",
        "-v",
        f"{host_cache.as_posix()}:{CONTAINER_CACHE.as_posix()}",
        "-e",
        f"HF_HOME={CONTAINER_CACHE.as_posix()}",
        "-e",
        f"HF_HUB_CACHE={CONTAINER_CACHE.as_posix()}/hub",
        "-e",
        f"TRANSFORMERS_CACHE={CONTAINER_CACHE.as_posix()}",
        image,
        "bash",
        "-lc",
        "python -m pip install -r "
        + shlex.quote((CONTAINER_REPO_DIR / "requirements.txt").as_posix())
        + " && "
        + shlex.join(runner_command),
    ]


def render_inner_runner() -> str:
    """Render the Python program executed inside the ROCm container."""
    return r'''"""DeepSeek-OCR-2 Hugging Face control runner."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer

os.environ.setdefault("HF_HOME", "/cache/huggingface")
os.environ.setdefault("HF_HUB_CACHE", "/cache/huggingface/hub")
os.environ.setdefault("TRANSFORMERS_CACHE", "/cache/huggingface")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--attn-implementation", required=True)
    args = parser.parse_args()
    started = time.monotonic()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        args.model,
        _attn_implementation=args.attn_implementation,
        trust_remote_code=True,
        use_safetensors=True,
    )
    model = model.eval().cuda().to(torch.bfloat16)
    result = model.infer(
        tokenizer,
        prompt=args.prompt,
        image_file=args.input.as_posix(),
        output_path=args.output_dir.as_posix(),
        base_size=1024,
        image_size=768,
        crop_mode=True,
        save_results=True,
    )
    output_path = args.output_dir / "result.md"
    output_path.write_text(str(result), encoding="utf-8")
    metadata = {
        "schema_version": "task347_deepseek_ocr2_hf_inner_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_ms": max(0, int((time.monotonic() - started) * 1000)),
        "model": args.model,
        "attn_implementation": args.attn_implementation,
        "result_chars": len(str(result)),
    }
    (args.output_dir / "task347-hf-inner-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


if __name__ == "__main__":
    raise SystemExit(main())
