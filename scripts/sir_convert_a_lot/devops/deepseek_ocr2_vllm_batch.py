"""Run DeepSeek-OCR-2 vLLM batch inference for formula candidate evaluation replay.

Purpose:
    Provide the governed Hemma-only DeepSeek-OCR-2/vLLM command adapter used by
    formula candidate evaluation to evaluate affected page images in one model-load batch.

Relationships:
    - Invoked by `formula_candidate_eval` through its batch command
      template.
    - Reuses the Markdown to DOCX route1/309 ROCm vLLM container, device, and cache pattern.
    - Uses the official DeepSeek-OCR-2 repository vLLM script shape for
      vLLM 0.8.5-era containers, with Hemma ROCm block-size and memory
      adjustments.
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

DEFAULT_MODEL = "deepseek-ai/DeepSeek-OCR-2"
DEFAULT_IMAGE = "rocm/vllm:rocm6.3.1_vllm_0.8.5_20250521"
DEFAULT_WORKSPACE_ROOT = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/deepseek-ocr2/deepseek-ocr2-vllm"
)
DEFAULT_DEEPSEEK_REPO_URL = "https://github.com/deepseek-ai/DeepSeek-OCR-2.git"
DEFAULT_HOST_CACHE = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
CONTAINER_CACHE = Path("/cache/huggingface")
HEMMA_VIDEO_GROUP_ID = "44"
HEMMA_RENDER_GROUP_ID = "993"
CONTAINER_INPUT_DIR = Path("/deepseek-ocr2/input")
CONTAINER_OUTPUT_DIR = Path("/deepseek-ocr2/output")
CONTAINER_REPO_DIR = Path("/deepseek-ocr-2")
CONTAINER_RUNNER_PATH = Path("/deepseek-ocr2/output/deepseek-ocr2_deepseek_ocr2_vllm_inner.py")
DEFAULT_PROMPT = "<image>\n<|grounding|>Convert the document to markdown."


def main(argv: Sequence[str] | None = None) -> int:
    """Run the DeepSeek-OCR-2/vLLM batch command."""
    args = build_parser().parse_args(argv)
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    repo_dir = Path(args.deepseek_repo_dir).resolve()
    host_cache = Path(args.host_cache).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    host_cache.mkdir(parents=True, exist_ok=True)
    ensure_deepseek_repo(repo_dir=repo_dir, repo_url=str(args.deepseek_repo_url))
    runner_path = output_dir / "deepseek-ocr2_deepseek_ocr2_vllm_inner.py"
    runner_path.write_text(render_inner_runner(), encoding="utf-8")
    metadata_path = output_dir / "deepseek-ocr2-vllm-host-metadata.json"
    command = build_docker_command(
        image=str(args.image),
        input_dir=input_dir,
        output_dir=output_dir,
        repo_dir=repo_dir,
        host_cache=host_cache,
        model=str(args.model),
        prompt=str(args.prompt),
        max_model_len=int(args.max_model_len),
        gpu_memory_utilization=str(args.gpu_memory_utilization),
        block_size=int(args.block_size),
        enforce_eager=bool(args.enforce_eager),
        max_concurrency=int(args.max_concurrency),
        num_workers=int(args.num_workers),
        crop_mode=bool(args.crop_mode),
        timeout_seconds=int(args.inner_timeout_seconds),
    )
    payload = {
        "schema_version": "deepseek-ocr2_deepseek_ocr2_vllm_host_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "hostname": platform.node(),
        "input_dir": input_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "deepseek_repo_dir": repo_dir.as_posix(),
        "host_cache": host_cache.as_posix(),
        "image": str(args.image),
        "model": str(args.model),
        "command": command,
    }
    metadata_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    metadata_path.write_text(metadata_json, encoding="utf-8")
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
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE_ROOT)
    parser.add_argument(
        "--deepseek-repo-dir",
        type=Path,
        default=DEFAULT_WORKSPACE_ROOT / "DeepSeek-OCR-2",
    )
    parser.add_argument("--deepseek-repo-url", default=DEFAULT_DEEPSEEK_REPO_URL)
    parser.add_argument("--host-cache", type=Path, default=DEFAULT_HOST_CACHE)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--gpu-memory-utilization", default="0.45")
    parser.add_argument("--block-size", type=int, default=16)
    parser.add_argument("--enforce-eager", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--crop-mode", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--inner-timeout-seconds", type=int, default=3600)
    parser.add_argument("--host-timeout-seconds", type=int, default=4200)
    return parser


def ensure_deepseek_repo(*, repo_dir: Path, repo_url: str) -> None:
    """Clone the official DeepSeek-OCR-2 repo under scratch when absent."""
    if (repo_dir / ".git").exists():
        return
    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, repo_dir.as_posix()],
        check=True,
        text=True,
        timeout=900,
    )


def build_docker_command(
    *,
    image: str,
    input_dir: Path,
    output_dir: Path,
    repo_dir: Path,
    host_cache: Path,
    model: str,
    prompt: str,
    max_model_len: int,
    gpu_memory_utilization: str,
    block_size: int,
    enforce_eager: bool,
    max_concurrency: int,
    num_workers: int,
    crop_mode: bool,
    timeout_seconds: int,
) -> list[str]:
    """Build the Docker command for the proven Hemma ROCm vLLM lane."""
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
        f"{input_dir.as_posix()}:{CONTAINER_INPUT_DIR.as_posix()}:ro",
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
        "-e",
        "VLLM_USE_TRITON_FLASH_ATTN=1",
        "-e",
        "VLLM_USE_V1=0",
        "-e",
        "PYTORCH_HIP_ALLOC_CONF=expandable_segments:True",
        image,
        "bash",
        "-lc",
        container_shell_command(
            model=model,
            prompt=prompt,
            max_model_len=max_model_len,
            gpu_memory_utilization=gpu_memory_utilization,
            block_size=block_size,
            enforce_eager=enforce_eager,
            max_concurrency=max_concurrency,
            num_workers=num_workers,
            crop_mode=crop_mode,
            timeout_seconds=timeout_seconds,
        ),
    ]


def container_shell_command(
    *,
    model: str,
    prompt: str,
    max_model_len: int,
    gpu_memory_utilization: str,
    block_size: int,
    enforce_eager: bool,
    max_concurrency: int,
    num_workers: int,
    crop_mode: bool,
    timeout_seconds: int,
) -> str:
    """Return the source-backed setup and runner command for the container."""
    runner_command = [
        "timeout",
        str(timeout_seconds),
        "python",
        CONTAINER_RUNNER_PATH.as_posix(),
        "--input-dir",
        CONTAINER_INPUT_DIR.as_posix(),
        "--output-dir",
        CONTAINER_OUTPUT_DIR.as_posix(),
        "--model",
        model,
        "--prompt",
        prompt,
        "--max-model-len",
        str(max_model_len),
        "--gpu-memory-utilization",
        gpu_memory_utilization,
        "--block-size",
        str(block_size),
        "--enforce-eager" if enforce_eager else "--no-enforce-eager",
        "--max-concurrency",
        str(max_concurrency),
        "--num-workers",
        str(num_workers),
        "--crop-mode" if crop_mode else "--no-crop-mode",
    ]
    requirements_path = CONTAINER_REPO_DIR / "requirements.txt"
    return (
        "python -m pip install -r "
        + shlex.quote(requirements_path.as_posix())
        + " && "
        + shlex.join(runner_command)
    )


def render_inner_runner() -> str:
    """Render the Python program executed inside the ROCm vLLM container."""
    return r'''"""DeepSeek-OCR-2 vLLM batch runner executed inside the ROCm vLLM container."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from PIL import ExifTags, Image

os.environ.setdefault("HF_HOME", "/cache/huggingface")
os.environ.setdefault("HF_HUB_CACHE", "/cache/huggingface/hub")
os.environ.setdefault("TRANSFORMERS_CACHE", "/cache/huggingface")
os.environ.setdefault("VLLM_USE_V1", "0")
sys.path.insert(0, "/deepseek-ocr-2/DeepSeek-OCR2-master/DeepSeek-OCR2-vllm")

from deepseek_ocr2 import (  # noqa: E402
    DeepseekOCR2ForCausalLM,
    DeepseekOCR2MultiModalProcessor,
)
from process.image_process import DeepseekOCR2Processor  # noqa: E402
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402
from vllm.model_executor.models.registry import ModelRegistry  # noqa: E402


def install_deepseek_vllm_08_processor_adapter() -> None:
    """Adapt DeepSeek's vLLM processor override to vLLM's 0.8 hash contract."""
    method = DeepseekOCR2MultiModalProcessor._cached_apply_hf_processor
    if "return_mm_hashes" in inspect.signature(method).parameters:
        return

    def _cached_apply_hf_processor(
        self,
        prompt,
        mm_data_items,
        hf_processor_mm_kwargs,
        *,
        return_mm_hashes: bool,
    ):
        if mm_data_items.get_count("image", strict=False) > 2:
            (
                prompt_ids,
                mm_kwargs,
                is_update_applied,
            ) = self._apply_hf_processor_main(
                prompt=prompt,
                mm_items=mm_data_items,
                hf_processor_mm_kwargs=hf_processor_mm_kwargs,
                enable_hf_prompt_update=True,
            )
            mm_hashes = (
                self._hash_mm_items(mm_data_items, hf_processor_mm_kwargs)
                if return_mm_hashes
                else None
            )
            return prompt_ids, mm_kwargs, mm_hashes, is_update_applied

        return super(
            DeepseekOCR2MultiModalProcessor,
            self,
        )._cached_apply_hf_processor(
            prompt=prompt,
            mm_data_items=mm_data_items,
            hf_processor_mm_kwargs=hf_processor_mm_kwargs,
            return_mm_hashes=return_mm_hashes,
        )

    DeepseekOCR2MultiModalProcessor._cached_apply_hf_processor = (
        _cached_apply_hf_processor
    )


install_deepseek_vllm_08_processor_adapter()
ModelRegistry.register_model("DeepseekOCR2ForCausalLM", DeepseekOCR2ForCausalLM)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--gpu-memory-utilization", default="0.70")
    parser.add_argument("--block-size", type=int, default=16)
    parser.add_argument("--enforce-eager", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--crop-mode", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    started = time.monotonic()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = sorted(path for path in args.input_dir.iterdir() if is_supported_image(path))
    llm = LLM(
        model=args.model,
        hf_overrides={"architectures": ["DeepseekOCR2ForCausalLM"]},
        block_size=args.block_size,
        disable_mm_preprocessor_cache=True,
        enforce_eager=args.enforce_eager,
        trust_remote_code=True,
        max_model_len=args.max_model_len,
        swap_space=0,
        max_num_seqs=args.max_concurrency,
        tensor_parallel_size=1,
        gpu_memory_utilization=float(args.gpu_memory_utilization),
    )
    processor = DeepseekOCR2Processor()
    with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        batch_inputs = list(
            executor.map(
                lambda path: process_single_image(
                    path=path,
                    prompt=args.prompt,
                    processor=processor,
                    crop_mode=args.crop_mode,
                ),
                image_paths,
            )
        )
    logits_processors = [
        NoRepeatNGramLogitsProcessor(
            ngram_size=20,
            window_size=50,
            whitelist_token_ids={128821, 128822},
        )
    ]
    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=8192,
        logits_processors=logits_processors,
        skip_special_tokens=False,
        include_stop_str_in_output=True,
    )
    outputs = llm.generate(batch_inputs, sampling_params=sampling_params)
    output_records = []
    for output, image_path in zip(outputs, image_paths, strict=True):
        content = cleanup_content(output.outputs[0].text)
        output_path = args.output_dir / f"{image_path.stem}.md"
        output_path.write_text(content, encoding="utf-8")
        output_records.append(
            {
                "input": image_path.as_posix(),
                "output": output_path.as_posix(),
                "chars": len(content),
                "finish_reason": output.outputs[0].finish_reason,
            }
        )
    metadata = {
        "schema_version": "deepseek-ocr2_deepseek_ocr2_vllm_inner_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_ms": max(0, int((time.monotonic() - started) * 1000)),
        "model": args.model,
        "prompt": args.prompt,
        "input_count": len(image_paths),
        "outputs": output_records,
    }
    (args.output_dir / "deepseek-ocr2-vllm-inner-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def process_single_image(
    *,
    path: Path,
    prompt: str,
    processor: object,
    crop_mode: bool,
) -> dict[str, object]:
    image = correct_image_orientation(Image.open(path)).convert("RGB")
    return {
        "prompt": prompt,
        "multi_modal_data": {
            "image": processor.tokenize_with_images(
                images=[image],
                bos=True,
                eos=True,
                cropping=crop_mode,
            )
        },
    }


def correct_image_orientation(image: Image.Image) -> Image.Image:
    try:
        exif = image._getexif()
        if exif is None:
            return image
        orientation_key = next(
            key for key, value in ExifTags.TAGS.items() if value == "Orientation"
        )
        orientation = exif.get(orientation_key, 1)
        if orientation == 3:
            return image.rotate(180, expand=True)
        if orientation == 6:
            return image.rotate(270, expand=True)
        if orientation == 8:
            return image.rotate(90, expand=True)
    except Exception:
        return image
    return image


def cleanup_content(text: str) -> str:
    formula_pattern = r"\\\[(.*?)\\\]"
    text = re.sub(formula_pattern, clean_formula_match, text)
    pattern = r"(<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>)"
    for match in re.findall(pattern, text, re.DOTALL):
        text = text.replace(match[0], "")
    return text.replace("\n\n\n\n", "\n\n").replace("\n\n\n", "\n\n")


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg"}


def clean_formula_match(match: re.Match[str]) -> str:
    formula = re.sub(r"\\quad\s*\([^)]*\)", "", match.group(1)).strip()
    return r"\[" + formula + r"\]"


if __name__ == "__main__":
    raise SystemExit(main())
'''


if __name__ == "__main__":
    raise SystemExit(main())
