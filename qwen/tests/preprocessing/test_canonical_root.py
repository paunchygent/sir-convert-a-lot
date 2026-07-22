"""Canonical processed-root dedupe tests for Qwen preprocessing.

Purpose:
    Verify that multiple run roots can be merged into one immutable deduplicated
    processed root without mutating original artifacts.

Relationships:
    - Tests `ml.qwen.preprocessing.canonical_root.build_canonical_processed_root`.
    - Uses fixtures from `tests.preprocessing.test_support`.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.preprocessing.canonical_root import (
    build_canonical_processed_root,
    canonical_processed_root_report_path,
)

from tests.preprocessing.test_support import (
    inventory_row_fixture,
    source_record_fixture,
    spool_row_fixture,
)


def test_build_canonical_processed_root_merges_unique_rows(tmp_path: Path) -> None:
    """Canonical processed-root build should merge unique rows across roots."""
    run_root_1 = tmp_path / "run-1"
    run_root_2 = tmp_path / "run-2"
    output_root = tmp_path / "canonical"

    source_1 = source_record_fixture(dataset_row_id="row-1")
    source_2 = source_record_fixture(dataset_row_id="row-2")

    # Setup run root 1
    (run_root_1 / "spool/rows/test-dataset/smoke/speaker-speaker-001").mkdir(parents=True)
    (run_root_1 / "spool/rows/test-dataset/smoke/speaker-speaker-001/row-1.json").write_text(
        json.dumps(spool_row_fixture(inventory_row_fixture(source_1)).__dict__, default=str)
    )
    (run_root_1 / "audio_24k/row-1.wav").parent.mkdir(parents=True)
    (run_root_1 / "audio_24k/row-1.wav").write_text("audio-1")

    # Setup run root 2
    (run_root_2 / "spool/rows/test-dataset/smoke/speaker-speaker-001").mkdir(parents=True)
    (run_root_2 / "spool/rows/test-dataset/smoke/speaker-speaker-001/row-2.json").write_text(
        json.dumps(spool_row_fixture(inventory_row_fixture(source_2)).__dict__, default=str)
    )
    (run_root_2 / "audio_24k/row-2.wav").parent.mkdir(parents=True)
    (run_root_2 / "audio_24k/row-2.wav").write_text("audio-2")

    summary = build_canonical_processed_root(
        output_root=output_root,
        run_roots=[run_root_1, run_root_2],
    )

    assert summary.retained_row_count == 2
    assert (output_root / "spool/rows/test_dataset/smoke/speaker-001/row-1.json").is_file()
    assert (output_root / "spool/rows/test_dataset/smoke/speaker-001/row-2.json").is_file()
    assert canonical_processed_root_report_path(output_root).is_file()
