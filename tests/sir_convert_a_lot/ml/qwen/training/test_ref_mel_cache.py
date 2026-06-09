"""Unit tests for Qwen ref-mel cache helpers.

Purpose:
    Validate bounded cache behavior and deterministic cache-key normalization
    for the patched Qwen training dataset path.

Relationships:
    - Exercises `sft_12hz_ref_mel_cache.py`.
    - Provides focused coverage for Qwen reference-mel cache `ref-mel cache`.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import torch

SFT_PATCH_ROOT = Path(__file__).resolve().parents[2] / "scripts/devops/qwen_finetuning_patches"
if SFT_PATCH_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SFT_PATCH_ROOT.as_posix())

REF_MEL_CACHE = importlib.import_module(
    "scripts.devops.qwen_finetuning_patches.sft_12hz_ref_mel_cache"
)

RefMelCache = REF_MEL_CACHE.RefMelCache
canonical_ref_audio_cache_key = REF_MEL_CACHE.canonical_ref_audio_cache_key


def test_ref_mel_cache_tracks_hits_and_misses() -> None:
    """Cache stats should reflect one miss followed by one hit."""
    cache = RefMelCache(enabled=True, max_items=4)

    assert cache.get("speaker-a") is None
    cache.put("speaker-a", torch.ones((1, 4, 8), dtype=torch.float32))

    cached = cache.get("speaker-a")
    assert isinstance(cached, torch.Tensor)

    payload = cache.payload()
    assert payload["enabled"] is True
    assert payload["cache_hits"] == 1
    assert payload["cache_misses"] == 1
    assert payload["cache_size"] == 1
    assert payload["cache_hit_rate"] == 0.5


def test_ref_mel_cache_enforces_bounded_size_with_lru_eviction() -> None:
    """The cache should evict oldest entries when max size is exceeded."""
    cache = RefMelCache(enabled=True, max_items=2)
    cache.put("speaker-a", torch.ones((1, 1, 1), dtype=torch.float32))
    cache.put("speaker-b", torch.ones((1, 1, 1), dtype=torch.float32))

    # Touch speaker-a so speaker-b becomes the eviction candidate.
    assert cache.get("speaker-a") is not None
    cache.put("speaker-c", torch.ones((1, 1, 1), dtype=torch.float32))

    assert cache.get("speaker-b") is None
    assert cache.get("speaker-a") is not None
    assert cache.get("speaker-c") is not None


def test_ref_mel_cache_disabled_mode_stays_noop() -> None:
    """Disabled cache mode should not persist entries or increment counters."""
    cache = RefMelCache(enabled=False, max_items=2)
    cache.put("speaker-a", torch.ones((1, 1, 1), dtype=torch.float32))

    assert cache.get("speaker-a") is None
    payload = cache.payload()
    assert payload["enabled"] is False
    assert payload["cache_hits"] == 0
    assert payload["cache_misses"] == 0
    assert payload["cache_size"] == 0
    assert payload["cache_hit_rate"] is None


def test_canonical_ref_audio_cache_key_normalizes_path_inputs() -> None:
    """String and list-string ref-audio values should resolve to stable keys."""
    path_key = canonical_ref_audio_cache_key("./refs/speaker-a/ref.wav")
    list_key = canonical_ref_audio_cache_key(["./refs/speaker-a/ref.wav"])

    assert isinstance(path_key, str)
    assert path_key.endswith("/refs/speaker-a/ref.wav")
    assert list_key == path_key
