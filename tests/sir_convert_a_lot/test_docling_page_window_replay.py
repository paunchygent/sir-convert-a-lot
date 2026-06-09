"""Tests for Docling page-window replay page-window replay diagnostics.

Purpose:
    Prove the diagnostic replay planner and subprocess timeout boundary used
    to localize slow Docling page windows without waiting for full production
    wall-clock duration.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.docling_page_window_replay`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.sir_convert_a_lot.devops.docling_page_window_replay import (
    persist_markdown_evidence,
)
from scripts.sir_convert_a_lot.devops.docling_page_window_replay_runtime import (
    ReplayWindow,
    RunSettings,
    build_child_command,
    build_locator_windows,
    parse_page_window,
    run_child_process,
    write_markdown_report,
)
from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    NormalizeMode,
    OcrMode,
    Priority,
    TableMode,
)


def test_locator_windows_cover_full_pages_and_adjacent_pairs() -> None:
    windows = build_locator_windows(ReplayWindow(start_page=13, end_page=16))

    assert windows == (
        ReplayWindow(start_page=13, end_page=16),
        ReplayWindow(start_page=13, end_page=13),
        ReplayWindow(start_page=14, end_page=14),
        ReplayWindow(start_page=15, end_page=15),
        ReplayWindow(start_page=16, end_page=16),
        ReplayWindow(start_page=13, end_page=14),
        ReplayWindow(start_page=14, end_page=15),
        ReplayWindow(start_page=15, end_page=16),
    )


def test_parse_page_window_rejects_backward_ranges() -> None:
    try:
        parse_page_window("16-13")
    except ValueError as exc:
        assert "invalid page window" in str(exc)
    else:
        raise AssertionError("backward page window should fail")


def test_child_process_timeout_kills_long_running_replay(tmp_path: Path) -> None:
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "import time",
                "Path(sys.argv[1]).write_text('started', encoding='utf-8')",
                "time.sleep(10)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    marker = tmp_path / "started.txt"

    outcome = run_child_process(
        [sys.executable, sleeper.as_posix(), marker.as_posix()],
        timeout_seconds=1.0,
        terminate_grace_seconds=0.5,
    )

    assert marker.read_text(encoding="utf-8") == "started"
    assert outcome.timed_out is True
    assert outcome.return_code is not None
    assert outcome.elapsed_ms < 5000


def test_persist_markdown_evidence_writes_child_markdown(tmp_path: Path) -> None:
    output_json = tmp_path / "p000013-000016.child.json"

    markdown_path = persist_markdown_evidence(
        args=argparse.Namespace(output_json=output_json.as_posix()),
        markdown="# Page window\n\nConverted content.\n",
    )

    assert markdown_path == tmp_path / "p000013-000016.child.md"
    assert markdown_path.read_text(encoding="utf-8") == "# Page window\n\nConverted content.\n"


def test_markdown_report_uses_formula_sidecar_for_timed_out_generation(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "report.md"

    write_markdown_report(
        path=report_path,
        payload={
            "source_sha256": "abc123",
            "source_pdf": "/tmp/input.pdf",
            "records": [
                {
                    "label": "p000014",
                    "status": "timed_out",
                    "child": {"elapsed_ms": 75321, "return_code": -15},
                    "child_payload": {},
                    "formula_diagnostics_events": [
                        {
                            "event": "transformers_predict_batch_started",
                            "max_new_tokens_max": 2048,
                        }
                    ],
                    "stack_dump_tail": "generate",
                }
            ],
        },
    )

    rendered = report_path.read_text(encoding="utf-8")
    assert "started:1" in rendered
    assert "2048" in rendered


def test_child_command_forwards_formula_preset_replay_flags(tmp_path: Path) -> None:
    settings = RunSettings(
        source_pdf=tmp_path / "input.pdf",
        output_root=tmp_path,
        windows=(ReplayWindow(start_page=14, end_page=14),),
        attempt_timeout_seconds=30.0,
        docling_document_timeout_seconds=25,
        stack_dump_after_seconds=10.0,
        terminate_grace_seconds=2.0,
        max_total_seconds=35.0,
        backend_strategy=BackendStrategy.AUTO,
        ocr_mode=OcrMode.AUTO,
        table_mode=TableMode.ACCURATE,
        normalize_mode=NormalizeMode.STRICT,
        acceleration_policy=AccelerationPolicy.GPU_REQUIRED,
        priority=Priority.NORMAL,
        ocr_engine=None,
        ocr_languages=(),
        easyocr_model_storage_directory=None,
        fail_on_timeout=False,
        formula_preset_only="granite_docling",
        single_formula_items=True,
    )

    command = build_child_command(
        settings=settings,
        window=settings.windows[0],
        result_path=tmp_path / "result.json",
        stack_path=tmp_path / "stack.txt",
        formula_events_path=tmp_path / "formula.jsonl",
    )

    assert "--formula-preset-only" in command
    assert "granite_docling" in command
    assert "--single-formula-items" in command
