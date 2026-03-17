"""Tests for the Story 31 deterministic parity probe.

Purpose:
    Lock the public CLI wiring and checkpoint-classification behavior before
    the mechanism lane starts relying on this surface to choose between `T227`
    remediation and a return to `T219`.

Relationships:
    - Exercises `story31_parity_probe.py` and `story31_parity_probe_runner.py`.
    - Reuses fake path reports instead of loading the real Qwen runtime.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe import (
    _parse_manifest_lines,
    main,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_contracts import (
    DEFAULT_STORY31_PARITY_PROBE_SETTINGS,
    Story31ParityPathReport,
    Story31ParityProbeReport,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_runner import (
    persist_report,
    run_story31_parity_probe,
)


def test_parse_manifest_lines_requires_exactly_four_values() -> None:
    """The parity probe should refuse partial or oversized microbatch windows."""
    with pytest.raises(SystemExit):
        _parse_manifest_lines("1,2,3")

    assert _parse_manifest_lines("6367,6966,4958,623") == (6367, 6966, 4958, 623)


def test_story31_parity_probe_cli_runs_and_persists_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public parity-probe command should persist compact report artifacts."""

    fake_report = _make_report(
        output_root=tmp_path,
        current_path=_make_path_report(),
        intended_path=_make_path_report(),
        first_divergence_classification="no_meaningful_divergence_found",
        first_divergence_checkpoint=None,
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_runner.run_story31_parity_probe",
        lambda _settings: fake_report,
    )

    result = main(["run", "--output-root", tmp_path.as_posix()])
    capsys.readouterr()

    assert result == 0
    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload["first_divergence_classification"] == "no_meaningful_divergence_found"
    assert (tmp_path / "current-path.json").exists() is True
    assert (tmp_path / "intended-path.json").exists() is True
    assert "# Story 31 Parity Probe" in (tmp_path / "results.md").read_text(encoding="utf-8")


def test_run_story31_parity_probe_classifies_pre_forward_divergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mismatch before model forward should invalidate the parity contract."""

    current_path = _make_path_report()
    intended_path = _make_path_report(
        selected_rows=(
            {
                "dataset_index": 0,
                "manifest_line_number": 9999,
            },
        )
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_runner.run_parity_path",
        lambda _settings, path_label: (
            current_path if path_label == "current_patched_path" else intended_path
        ),
    )

    report = run_story31_parity_probe(
        DEFAULT_STORY31_PARITY_PROBE_SETTINGS.__class__(output_root=tmp_path)
    )
    persist_report(tmp_path, report)

    assert report.first_divergence_classification == "invalid_parity_input_contract"
    assert report.first_divergence_checkpoint == "selected_rows"
    assert report.recommended_next_step == "repair_t226_parity_inputs_before_inference"


def test_run_story31_parity_probe_classifies_boundary_only_divergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A first mismatch only at the non-finite boundary should stay boundary-scoped."""

    shared_path = _make_path_report()
    boundary_path = _make_path_report(
        backward_pre_clip={
            "trigger_reason": "pre_clip_non_finite_gradients",
            "first_non_finite_stage": "pre_clip",
            "first_non_finite_surface": "text_embedding.weight.grad",
            "pre_clip_gradient_probes": {
                "first_non_finite_surface": "text_embedding.weight.grad",
            },
        },
        execution_outcome={"status": "optimizer_boundary_failure"},
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_runner.run_parity_path",
        lambda _settings, path_label: (
            boundary_path if path_label == "current_patched_path" else shared_path
        ),
    )

    report = run_story31_parity_probe(
        DEFAULT_STORY31_PARITY_PROBE_SETTINGS.__class__(output_root=tmp_path)
    )

    assert report.first_divergence_classification == "divergence_at_non_finite_boundary"
    assert report.first_divergence_checkpoint == "backward_pre_clip"
    assert (
        report.recommended_next_step == "record_boundary_only_divergence_then_decide_t227_vs_t219"
    )


def _make_report(
    *,
    output_root: Path,
    current_path: Story31ParityPathReport,
    intended_path: Story31ParityPathReport,
    first_divergence_classification: str,
    first_divergence_checkpoint: str | None,
) -> Story31ParityProbeReport:
    return Story31ParityProbeReport(
        generated_at="2026-03-17T22:00:00Z",
        output_root=output_root.as_posix(),
        source_bundle_root="/bundle",
        image="test-image",
        model_id="test-model",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        manifest_lines=(6367, 6966, 4958, 623),
        batch_size=1,
        gradient_accumulation_steps=4,
        text_embedding_assembly_mode="full_channel_masked",
        text_embedding_mask_policy="text_span_only",
        max_steps=1,
        current_path_report_path=(output_root / "current-path.json").as_posix(),
        intended_path_report_path=(output_root / "intended-path.json").as_posix(),
        current_path=current_path,
        intended_path=intended_path,
        checkpoint_comparisons=(),
        first_divergence_checkpoint=first_divergence_checkpoint,
        first_divergence_classification=first_divergence_classification,
        recommended_next_step="return_to_t219_if_no_higher_priority_runtime_bug_is_found",
        summary="test summary",
    )


def _make_path_report(
    *,
    selected_rows: tuple[dict[str, object], ...] = (
        {
            "dataset_index": 0,
            "manifest_line_number": 6367,
        },
    ),
    backward_pre_clip: dict[str, object] | None = None,
    execution_outcome: dict[str, object] | None = None,
) -> Story31ParityPathReport:
    return Story31ParityPathReport(
        path_label="current_patched_path",
        execution_mode="current_train_step_window",
        output_model_path="/tmp/output",
        runtime_posture={"batch_size": 1},
        selected_rows=selected_rows,
        per_item_dataset_output=({"speaker_id": 0},),
        collated_batch_tensors=({"input_ids": {"sha256": "a"}},),
        forward_entry_surfaces=({"train_iteration": 1, "surfaces": {}},),
        loss_decomposition=({"train_iteration": 1, "surfaces": {}},),
        backward_pre_clip=backward_pre_clip,
        clip_boundary=None,
        optimizer_preconditions=None,
        step_forensics=None,
        execution_outcome={"status": "completed_optimizer_step"}
        if execution_outcome is None
        else execution_outcome,
    )
