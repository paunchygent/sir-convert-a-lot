"""Smoke probe executed inside the Task 100 Qwen fine-tuning image.

Purpose:
    Validate that the dedicated Qwen training image can import the patched
    fine-tuning surfaces, resolve a Hugging Face Hub model id without assuming
    a local checkout, and expose the dependency/runtime versions needed by the
    Task 100 training lane.

Relationships:
    - Executed by `run_task100_hemma_qwen_finetune_smoke.py` inside the
      dedicated training image.
    - Imports the patched `sft_12hz.py` entrypoint from
      `scripts/devops/qwen_finetuning_patches/`.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path

import sft_12hz
import torch
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel


def _package_version(distribution_name: str) -> str | None:
    """Return one installed package version, or `None` when it is absent."""
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _build_dependency_versions() -> dict[str, str | None]:
    """Return the Task 100 dependency versions visible inside the image."""
    return {
        "qwen-tts": _package_version("qwen-tts"),
        "accelerate": _package_version("accelerate"),
        "transformers": _package_version("transformers"),
        "huggingface-hub": _package_version("huggingface-hub"),
        "safetensors": _package_version("safetensors"),
        "librosa": _package_version("librosa"),
        "soundfile": _package_version("soundfile"),
        "sentencepiece": _package_version("sentencepiece"),
        "tensorboard": _package_version("tensorboard"),
        "torch": _package_version("torch"),
        "torchaudio": _package_version("torchaudio"),
        "onnxruntime": _package_version("onnxruntime"),
        "sox": _package_version("sox"),
        "flash-attn": _package_version("flash-attn"),
    }


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the in-container smoke probe."""
    parser = argparse.ArgumentParser(
        description="Run the Task 100 Qwen training image smoke probe."
    )
    parser.add_argument(
        "--model-id",
        default="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        help="Model id or local model path used to verify artifact resolution.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the smoke probe and print one JSON payload to stdout."""
    args = _parse_args()
    if not torch.cuda.is_available():
        raise SystemExit(
            "Task 100 smoke probe expected `torch.cuda.is_available()` "
            "to be true inside the container."
        )
    if torch.version.hip is None:
        raise SystemExit("Task 100 smoke probe expected a ROCm-enabled torch build.")

    resolved_model_path = sft_12hz._resolve_model_export_source_path(str(args.model_id))
    config_dict = sft_12hz._load_config_dict(str(args.model_id))
    flash_attn_importable = importlib.util.find_spec("flash_attn") is not None
    flash_attn_model_load_ok = False
    if flash_attn_importable:
        model = Qwen3TTSModel.from_pretrained(
            str(args.model_id),
            dtype=torch.bfloat16,
            attn_implementation="flash_attention_2",
        )
        del model
        flash_attn_model_load_ok = True

    payload = {
        "model_id": str(args.model_id),
        "resolved_model_path": str(Path(resolved_model_path)),
        "resolved_config_path": str(Path(resolved_model_path) / "config.json"),
        "tts_model_type": config_dict.get("tts_model_type"),
        "torch_version": str(torch.__version__),
        "torchaudio_version": _package_version("torchaudio"),
        "torch_cuda_available": True,
        "torch_cuda_device_count": int(torch.cuda.device_count()),
        "torch_hip_version": str(torch.version.hip),
        "flash_attn_importable": flash_attn_importable,
        "flash_attn_version": _package_version("flash-attn"),
        "flash_attn_model_load_ok": flash_attn_model_load_ok,
        "dependency_versions": _build_dependency_versions(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
