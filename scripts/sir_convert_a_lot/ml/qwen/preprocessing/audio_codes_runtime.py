"""Runtime settings for Qwen audio-code generation.

Purpose:
    Define the explicit runtime contract used when loading the Qwen tokenizer
    model for bounded audio-code generation so Hemma callers can request a
    governed ROCm-backed posture instead of silently falling back to CPU.

Relationships:
    - Imported by `ml.qwen.preprocessing.finalization` to configure the warm
      tokenizer loader.
    - Embedded in preprocessing settings so finalization can request the
      governed tokenizer posture explicitly.
    - Reused by Qwen bundle runtime helpers so bundle provenance can record
      the effective audio-code runtime contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

AudioCodesDtype = Literal["float16", "bfloat16", "float32"]
AudioCodesAttentionImplementation = Literal["eager", "sdpa", "flash_attention_2"]

DEFAULT_GOVERNED_DEVICE_MAP = "cuda:0"
DEFAULT_GOVERNED_DTYPE: AudioCodesDtype = "bfloat16"
DEFAULT_GOVERNED_ATTN_IMPLEMENTATION: AudioCodesAttentionImplementation = "flash_attention_2"


@dataclass(frozen=True)
class AudioCodesRuntimeSettings:
    """Explicit runtime settings for one warm Qwen audio-code tokenizer."""

    device_map: str | None = None
    dtype: AudioCodesDtype | None = None
    attn_implementation: AudioCodesAttentionImplementation | None = None
    require_gpu: bool = False


def governed_qwen_audio_codes_runtime_settings() -> AudioCodesRuntimeSettings:
    """Return the canonical governed ROCm-backed audio-code runtime posture."""
    return AudioCodesRuntimeSettings(
        device_map=DEFAULT_GOVERNED_DEVICE_MAP,
        dtype=DEFAULT_GOVERNED_DTYPE,
        attn_implementation=DEFAULT_GOVERNED_ATTN_IMPLEMENTATION,
        require_gpu=True,
    )


def render_audio_codes_runtime_settings(
    settings: AudioCodesRuntimeSettings,
) -> dict[str, object]:
    """Render one runtime-settings payload for deterministic reports/fingerprints."""
    return asdict(settings)
