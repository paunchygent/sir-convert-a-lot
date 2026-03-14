"""Model-export helpers for the patched Qwen fine-tuning trainer.

Purpose:
    Keep model-config resolution and checkpoint export logic separate from the
    training facade so `sft_12hz.py` stays small while preserving the base-model
    export contract.

Relationships:
    - Imported by the extracted training loop module.
    - Reused by the public `sft_12hz.py` facade via re-export.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import torch
from accelerate import Accelerator
from huggingface_hub import hf_hub_download, snapshot_download
from safetensors.torch import save_file

EXPORT_METADATA_PATTERNS = (
    "*.json",
    "*.model",
    "*.py",
    "*.tiktoken",
    "*.txt",
)


def load_config_dict(model_path: str) -> dict[str, object]:
    """Load the model config JSON as one normalized dictionary."""
    config_path = resolve_model_config_path(model_path)
    with config_path.open("r", encoding="utf-8") as handle:
        config_dict_raw = json.load(handle)
    if not isinstance(config_dict_raw, dict):
        raise ValueError("Expected config.json to contain a JSON object.")
    return {str(key): value for key, value in config_dict_raw.items()}


def resolve_model_config_path(model_path: str) -> Path:
    """Resolve the config path for a local or hub-backed model id."""
    local_model_path = Path(model_path)
    if local_model_path.is_dir():
        return local_model_path / "config.json"
    return Path(hf_hub_download(repo_id=model_path, filename="config.json"))


def resolve_model_export_source_path(model_path: str) -> Path:
    """Resolve the source directory used for metadata export."""
    local_model_path = Path(model_path)
    if local_model_path.is_dir():
        return local_model_path
    snapshot_path = snapshot_download(
        repo_id=model_path,
        allow_patterns=list(EXPORT_METADATA_PATTERNS),
    )
    return Path(snapshot_path)


def save_checkpoint(
    *,
    accelerator: Accelerator,
    model: torch.nn.Module,
    model_path: str,
    output_dir: Path,
) -> str:
    """Export one checkpoint directory from the current training state."""
    resolved_model_path = resolve_model_export_source_path(model_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(resolved_model_path, output_dir, dirs_exist_ok=True)

    config_dict = load_config_dict(model_path)
    config_dict["tts_model_type"] = "base"

    output_config_path = output_dir / "config.json"
    with output_config_path.open("w", encoding="utf-8") as handle:
        json.dump(config_dict, handle, indent=2, ensure_ascii=False)

    unwrapped_model = accelerator.unwrap_model(model)
    state_dict = {
        key: value.detach().to("cpu") for key, value in unwrapped_model.state_dict().items()
    }
    save_file(state_dict, (output_dir / "model.safetensors").as_posix())
    return output_dir.as_posix()
