"""Tests for the Qwen fallback proof lane offline token-span audit surface.

Purpose:
    Verify that the token-span audit can extract the canonical failing sample
    from saved proof artifacts and prove the current prefix-only leakage
    without launching another training replay.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.ml.qwen.training.token_span_audit`.
    - Complements the existing dataset and gradient RCA tests with one
      contract-level audit for text-token span.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.token_span_audit import (
    build_report_markdown,
    build_token_span_audit_result,
    load_sample_from_status,
    main,
)


def _canonical_like_token_ids() -> tuple[int, ...]:
    """Return one canonical-like collated token sequence for audit tests."""
    semantic_ids = tuple(range(2000, 2128))
    return (
        151644,
        77091,
        198,
        151671,
        151671,
        151671,
        151671,
        151672,
        *semantic_ids,
        151673,
        *((151671,) * 371),
    )


def _write_status_json(tmp_path: Path) -> Path:
    """Write one minimal detached-status payload for the audit extractor."""
    token_ids = _canonical_like_token_ids()
    sample = {
        "row_id": "train.jsonl#L101",
        "manifest_path": "train.jsonl",
        "manifest_line_number": 101,
        "speaker_id": "speaker-a",
        "text_preview": "hej världen",
        "full_text": "hej världen igen",
        "token_ids": list(token_ids),
        "unique_token_ids": sorted(set(token_ids)),
        "input_gradient_has_non_finite": True,
        "non_finite_token_positions": list(range(0, 507)),
        "non_finite_token_ids": list(token_ids[:507]),
        "parameter_row_ids_present_in_sample": sorted(set(token_ids[:137])),
    }
    payload = {
        "pilot_status": {
            "optimizer_boundary_guard": {
                "step_forensics": {
                    "microbatches": [
                        {
                            "train_iteration": 851,
                            "microbatch_index_in_optimizer_step": 1,
                            "gradient_forensics": {
                                "input_text_embedding_gradient": {
                                    "samples": [sample],
                                }
                            },
                        }
                    ]
                }
            }
        }
    }
    status_json_path = tmp_path / "status.json"
    status_json_path.write_text(json.dumps(payload), encoding="utf-8")
    return status_json_path


def test_load_sample_from_status_extracts_the_canonical_failing_sample(tmp_path: Path) -> None:
    """The extractor should find the requested train-iteration / manifest pair."""
    status_json_path = _write_status_json(tmp_path)

    sample = load_sample_from_status(
        status_json_path=status_json_path,
        manifest_line_number=101,
        train_iteration=851,
    )

    assert sample.row_id == "train.jsonl#L101"
    assert sample.manifest_line_number == 101
    assert sample.train_iteration == 851
    assert len(sample.token_ids) == 508
    assert len(sample.unique_token_ids) == 134
    assert len(sample.non_finite_token_positions) == 507


def test_build_token_span_audit_result_proves_prefix_and_eos_leakage(tmp_path: Path) -> None:
    """The audit should prove the corrected helper now matches semantic positions."""
    status_json_path = _write_status_json(tmp_path)
    sample = load_sample_from_status(
        status_json_path=status_json_path,
        manifest_line_number=101,
        train_iteration=851,
    )

    report = build_token_span_audit_result(
        source_status_json_path=status_json_path,
        sample=sample,
    )

    assert report.layout.inferred_text_ids_len == 131
    assert report.layout.inferred_codec_ids_len == 369
    assert report.current_text_span_only.start_index == 8
    assert report.current_text_span_only.end_index_exclusive == 136
    assert report.intended_semantic_text_span.start_index == 8
    assert report.intended_semantic_text_span.end_index_exclusive == 136
    assert report.leakage.leaked_positions == ()
    assert report.leakage.leaked_unique_token_ids == ()
    assert report.leakage.current_trainable_non_finite_count == 128
    assert report.leakage.intended_semantic_non_finite_count == 128
    assert report.requires_explicit_position_mask is True


def test_main_writes_json_and_markdown_artifacts(tmp_path: Path) -> None:
    """The public runner should persist deterministic JSON and Markdown artifacts."""
    status_json_path = _write_status_json(tmp_path)
    output_root = tmp_path / "audit-output"

    exit_code = main(
        [
            "--status-json",
            status_json_path.as_posix(),
            "--output-root",
            output_root.as_posix(),
        ]
    )

    assert exit_code == 0
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    assert report_json_path.is_file()
    assert report_md_path.is_file()
    payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert payload["layout"]["eos_position"] == 136
    assert payload["requires_explicit_position_mask"] is True
    markdown = report_md_path.read_text(encoding="utf-8")
    assert "Leakage should therefore stay at zero" in markdown


def test_build_report_markdown_mentions_the_recommended_correction(tmp_path: Path) -> None:
    """The audit summary should point operators to the explicit-position-mask family."""
    status_json_path = _write_status_json(tmp_path)
    sample = load_sample_from_status(
        status_json_path=status_json_path,
        manifest_line_number=101,
        train_iteration=851,
    )
    report = build_token_span_audit_result(
        source_status_json_path=status_json_path,
        sample=sample,
    )

    markdown = build_report_markdown(report)

    assert "Requires explicit position mask: `True`" in markdown
    assert "Explicit position mask builder in dataset collation" in markdown


def test_build_token_span_audit_result_reports_zero_leakage_after_the_correction(
    tmp_path: Path,
) -> None:
    """The corrected contract should report no leaked positions on the audit sample."""
    status_json_path = _write_status_json(tmp_path)
    sample = load_sample_from_status(
        status_json_path=status_json_path,
        manifest_line_number=101,
        train_iteration=851,
    )

    report = build_token_span_audit_result(
        source_status_json_path=status_json_path,
        sample=sample,
    )

    assert report.leakage.leaked_non_finite_count == 0
    assert report.leakage.leaked_token_ids == ()
