"""Ref-mel cache helpers for the patched Qwen trainer dataset path.

Purpose:
    Provide a bounded in-memory cache for reference mel tensors so repeated
    rows that share canonical `ref_audio` anchors do not recompute mels in the
    dataset hot path.

Relationships:
    - Imported by `dataset.py` for per-row cache reuse.
    - Imported by `sft_12hz.py` to expose cache settings and summary metrics.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import torch

DEFAULT_REF_MEL_CACHE_ENABLED = True
DEFAULT_REF_MEL_CACHE_MAX_ITEMS = 2048


@dataclass(frozen=True)
class RefMelCacheStats:
    """Machine-readable cache counters for one training run."""

    enabled: bool
    max_items: int
    cache_hits: int
    cache_misses: int
    cache_size: int
    cache_hit_rate: float | None


class RefMelCache:
    """Bounded LRU cache keyed by canonical ref-audio identity."""

    def __init__(self, *, enabled: bool, max_items: int) -> None:
        if max_items <= 0:
            raise ValueError("`ref_mel_cache_max_items` must be positive.")
        self._enabled = enabled
        self._max_items = max_items
        self._entries: OrderedDict[str, torch.Tensor] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

    def get(self, cache_key: str) -> torch.Tensor | None:
        """Return one cached tensor and update hit/miss counters."""
        if not self._enabled:
            return None
        cached = self._entries.get(cache_key)
        if cached is None:
            self._cache_misses += 1
            return None
        self._entries.move_to_end(cache_key, last=True)
        self._cache_hits += 1
        return cached

    def put(self, cache_key: str, ref_mel: torch.Tensor) -> None:
        """Store one tensor while enforcing the bounded cache size."""
        if not self._enabled:
            return
        self._entries[cache_key] = ref_mel
        self._entries.move_to_end(cache_key, last=True)
        while len(self._entries) > self._max_items:
            self._entries.popitem(last=False)

    def stats(self) -> RefMelCacheStats:
        """Return the current cache statistics payload."""
        total = self._cache_hits + self._cache_misses
        hit_rate = None if total == 0 else float(self._cache_hits) / float(total)
        return RefMelCacheStats(
            enabled=self._enabled,
            max_items=self._max_items,
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
            cache_size=len(self._entries),
            cache_hit_rate=hit_rate,
        )

    def payload(self) -> dict[str, bool | float | int | None]:
        """Return cache stats as a JSON-safe dictionary."""
        stats = self.stats()
        return {
            "enabled": stats.enabled,
            "max_items": stats.max_items,
            "cache_hits": stats.cache_hits,
            "cache_misses": stats.cache_misses,
            "cache_size": stats.cache_size,
            "cache_hit_rate": stats.cache_hit_rate,
        }


def canonical_ref_audio_cache_key(ref_audio: object) -> str | None:
    """Return one stable cache key from a manifest `ref_audio` value."""
    if isinstance(ref_audio, str):
        return _canonicalize_path_key(ref_audio)
    if isinstance(ref_audio, list) and len(ref_audio) > 0:
        first_entry = ref_audio[0]
        if isinstance(first_entry, str):
            return _canonicalize_path_key(first_entry)
    return None


def _canonicalize_path_key(path_value: str) -> str | None:
    """Normalize one path-like value into a deterministic cache key."""
    normalized = path_value.strip()
    if normalized == "":
        return None
    return Path(normalized).expanduser().resolve(strict=False).as_posix()
