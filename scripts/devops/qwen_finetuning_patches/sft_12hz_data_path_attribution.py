"""Worker-truth data-path attribution helpers for the patched Qwen trainer.

Purpose:
    Collect authoritative ref-input and dataset-path activity counters for
    bounded proof runs where the trainer deliberately stays single-process.

Relationships:
    - Used by `dataset.py` to record persisted-ref loads, runtime ref-mel
      extraction, `__getitem__`, and `collate_fn` timings.
    - Used by `sft_12hz_setup.py` and the detached training surfaces to fail
      closed when proof mode is requested without authoritative conditions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DataPathAttributionCollector:
    """Mutable worker-truth counters for one bounded proof run."""

    proof_mode_enabled: bool
    authoritative: bool
    persisted_ref_mel_load_count: int = 0
    persisted_ref_mel_load_seconds: float = 0.0
    runtime_ref_mel_extraction_count: int = 0
    runtime_ref_mel_extraction_seconds: float = 0.0
    getitem_call_count: int = 0
    getitem_total_seconds: float = 0.0
    collate_call_count: int = 0
    collate_total_seconds: float = 0.0

    def record_persisted_ref_mel_load(self, duration_seconds: float) -> None:
        """Record one persisted ref-mel load event."""
        self.persisted_ref_mel_load_count += 1
        self.persisted_ref_mel_load_seconds += duration_seconds

    def record_runtime_ref_mel_extraction(self, duration_seconds: float) -> None:
        """Record one runtime ref-mel extraction event."""
        self.runtime_ref_mel_extraction_count += 1
        self.runtime_ref_mel_extraction_seconds += duration_seconds

    def record_getitem(self, duration_seconds: float) -> None:
        """Record one `__getitem__` call duration."""
        self.getitem_call_count += 1
        self.getitem_total_seconds += duration_seconds

    def record_collate(self, duration_seconds: float) -> None:
        """Record one `collate_fn` call duration."""
        self.collate_call_count += 1
        self.collate_total_seconds += duration_seconds

    def payload(self) -> dict[str, bool | float | int]:
        """Return a JSON-safe payload for report and status artifacts."""
        return {
            "proof_mode_enabled": self.proof_mode_enabled,
            "authoritative": self.authoritative,
            "persisted_ref_mel_load_count": self.persisted_ref_mel_load_count,
            "persisted_ref_mel_load_seconds": self.persisted_ref_mel_load_seconds,
            "runtime_ref_mel_extraction_count": self.runtime_ref_mel_extraction_count,
            "runtime_ref_mel_extraction_seconds": self.runtime_ref_mel_extraction_seconds,
            "getitem_call_count": self.getitem_call_count,
            "getitem_total_seconds": self.getitem_total_seconds,
            "collate_call_count": self.collate_call_count,
            "collate_total_seconds": self.collate_total_seconds,
        }


def build_data_path_attribution_collector(
    *,
    proof_mode_enabled: bool,
    dataloader_num_workers: int,
) -> DataPathAttributionCollector | None:
    """Create one collector when proof mode is enabled and authoritative."""
    if not proof_mode_enabled:
        return None
    if dataloader_num_workers != 0:
        raise ValueError(
            "Data-path proof mode requires `--dataloader_num_workers=0` so worker-side "
            "counters remain authoritative."
        )
    return DataPathAttributionCollector(
        proof_mode_enabled=True,
        authoritative=True,
    )
