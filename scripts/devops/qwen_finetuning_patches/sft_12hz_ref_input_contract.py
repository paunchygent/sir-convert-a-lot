"""Lightweight persisted ref-input contract constants for Qwen Qwen pilot training.

Purpose:
    Expose the canonical persisted reference-input metadata constants without
    importing the heavier audio, numpy, or torch helpers used by extraction and
    loading code.

Relationships:
    - Imported by `sft_12hz_ref_inputs.py` as the authoritative contract source.
    - Imported by operator-safe CLI surfaces that need contract validation
      without depending on the full training extras at import time.
"""

from __future__ import annotations

PRECOMPUTED_REF_INPUT_KIND = "ref_mel"
PRECOMPUTED_REF_INPUT_VERSION = "qwen_reference_mel_v1"
PRECOMPUTED_REF_INPUT_SOURCE_FIELD = "ref_audio"
