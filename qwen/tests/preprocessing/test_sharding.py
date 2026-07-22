"""Sharding and work-allocation tests for Qwen preprocessing.

Purpose:
    Verify that the remaining preprocessing universe can be cut into immutable
    shards and issued as processing units through the append-only assignment
    ledger.

Relationships:
    - Tests `ml.qwen.preprocessing.sharding`.
    - Uses fixtures from `tests.preprocessing.test_support`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import (
    load_row_key_records,
    write_row_key_records,
)


def test_write_and_load_row_key_records(tmp_path: Path) -> None:
    """Row-key records should round-trip through JSONL artifacts."""
    path = tmp_path / "row_keys.jsonl"
    row_keys = [
        ("ds1", "split1", "row1"),
        ("ds1", "split1", "row2"),
    ]

    write_row_key_records(path, row_keys)
    loaded = load_row_key_records(path)

    assert len(loaded) == 2
    assert ("ds1", "split1", "row1") in loaded
    assert ("ds1", "split1", "row2") in loaded
