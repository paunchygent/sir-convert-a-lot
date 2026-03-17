"""Tests for the Story 31 talker-core stability lab.

Purpose:
    Lock the compact matrix-row contract and public CLI wiring before the
    exploration lane starts consuming Hemma time.

Relationships:
    - Exercises `story31_stability_lab_runner.py` and
      `story31_stability_lab.py`.
    - Reuses fake probe payloads instead of launching the real containerized
      backward-lineage kernel.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training import story31_stability_lab_runner
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_bundle import (
    BackwardLineageMiniBundle,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab import main
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    StabilityLabMatrixRow,
    Story31StabilityLabReport,
    Story31StabilityLabSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_runner import (
    DEFAULT_HOOK_PROFILE,
    DEFAULT_MANIFEST_FAMILY,
    DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
    DEFAULT_SOURCE_LINES,
    DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
    _build_matrix_rows,
    parse_stabilization_variants,
    persist_report,
    run_stability_lab,
)


def test_parse_stabilization_variants_preserves_requested_order() -> None:
    """The stability lab should run variants in the order we ask for them."""
    assert parse_stabilization_variants("off,layer16_gated_fp32") == (
        "off",
        "layer16_gated_fp32",
    )


def test_build_matrix_rows_captures_case_signal_and_anomaly_operator() -> None:
    """Compact Story 31 rows should keep the exact failure signal needed for promotion."""
    rows = _build_matrix_rows(
        probe_payload={
            "cases": [
                {
                    "case_id": "pair-main-loss",
                    "loss_kind": "main_loss",
                    "source_line_numbers": [13, 4],
                    "batch_size": 2,
                    "first_non_finite_hook_tensor": "talker_core.layer_16.mlp.gated_product",
                    "first_non_finite_talker_core_hook_tensor": (
                        "talker_core.layer_16.mlp.gated_product"
                    ),
                    "gradient_rca": {"first_non_finite_surface": "input_text_embedding.grad"},
                    "parameter_gradient_probes": {
                        "first_non_finite_surface": "text_embedding.weight.grad"
                    },
                    "anomaly_trace": (
                        "Function 'MulBackward0' returned nan values in its 0th output."
                    ),
                }
            ],
            "branch_summaries": [
                {
                    "loss_kind": "main_loss",
                    "interaction_mode": "both_rows",
                }
            ],
        },
        stabilization_variant="layer16_gated_fp32",
    )

    assert rows == (
        StabilityLabMatrixRow(
            stabilization_variant="layer16_gated_fp32",
            case_id="pair-main-loss",
            loss_kind="main_loss",
            source_line_numbers=(13, 4),
            batch_size=2,
            interaction_mode="both_rows",
            case_has_non_finite=True,
            first_non_finite_hook_tensor="talker_core.layer_16.mlp.gated_product",
            first_non_finite_talker_core_hook_tensor="talker_core.layer_16.mlp.gated_product",
            gradient_rca_first_non_finite_surface="input_text_embedding.grad",
            parameter_first_non_finite_surface="text_embedding.weight.grad",
            anomaly_operator="MulBackward0",
        ),
    )


def test_story31_stability_lab_cli_runs_and_persists_compact_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public Story 31 command should persist one compact matrix report."""

    def fake_run_stability_lab(*_args: object, **_kwargs: object) -> Story31StabilityLabReport:
        return Story31StabilityLabReport(
            generated_at="2026-03-17T00:00:00Z",
            image="test-image",
            image_id="sha256:test",
            build_performed=False,
            model_id="test-model",
            source_bundle_root="/bundle",
            manifest_family="swedish_pilot_train",
            source_line_numbers=(13, 4),
            text_embedding_mask_policy="text_span_only",
            hook_profile="talker_core_boundary",
            stabilization_variants=("off", "layer16_gated_fp32"),
            mini_bundle={"manifest_path": "/bundle/manifests/train.jsonl"},
            hf_cache_dir="/hf",
            effective_hf_cache_dir="/hf",
            used_home_mount=False,
            effective_output_root=tmp_path.as_posix(),
            used_output_root_home_mount=False,
            variant_report_paths={"off": (tmp_path / "variant-reports" / "off.json").as_posix()},
            probe_commands={"off": ["sudo", "-n", "docker", "run"]},
            matrix_rows=(),
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab.run_stability_lab",
        fake_run_stability_lab,
    )

    result = main(["run", "--output-root", tmp_path.as_posix(), "--skip-build"])
    capsys.readouterr()

    assert result == 0
    assert (
        json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["image"] == "test-image"
    )
    assert "# Story 31 Stability Lab" in (tmp_path / "results.md").read_text(encoding="utf-8")


def test_run_stability_lab_reuses_one_bundle_and_writes_variant_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Story 31 runner should emit one compact matrix report across variants."""

    class _MountResolution:
        def __init__(self, effective_root: Path) -> None:
            self.canonical_root = effective_root
            self.effective_root = effective_root
            self.used_home_mount = False

    monkeypatch.setattr(
        story31_stability_lab_runner,
        "prepare_qwen_image",
        lambda _settings: (False, "sha256:test"),
    )
    monkeypatch.setattr(
        story31_stability_lab_runner,
        "resolve_effective_hf_cache_dir",
        lambda _settings: _MountResolution(tmp_path / "hf"),
    )
    monkeypatch.setattr(
        story31_stability_lab_runner,
        "resolve_effective_bind_root",
        lambda *args, **kwargs: _MountResolution(tmp_path / "output-mount"),
    )
    monkeypatch.setattr(
        story31_stability_lab_runner,
        "materialize_backward_lineage_bundle",
        lambda **kwargs: BackwardLineageMiniBundle(
            source_bundle_root="/bundle",
            bundle_root="/bundle/mini",
            manifest_path="/bundle/manifests/train.jsonl",
            manifest_family="swedish_pilot_train",
            selected_source_lines=(13, 4),
            selected_rows=(),
        ),
    )
    monkeypatch.setattr(
        story31_stability_lab_runner,
        "run_backward_lineage_probe",
        lambda *_args, talker_core_stabilization_variant, **_kwargs: (
            {
                "cases": [
                    {
                        "case_id": "pair-main-loss",
                        "loss_kind": "main_loss",
                        "source_line_numbers": [13, 4],
                        "batch_size": 2,
                        "first_non_finite_hook_tensor": (
                            None
                            if talker_core_stabilization_variant == "layer16_gated_fp32"
                            else "input_embeddings"
                        ),
                        "first_non_finite_talker_core_hook_tensor": None,
                        "gradient_rca": {"first_non_finite_surface": None},
                        "parameter_gradient_probes": {"first_non_finite_surface": None},
                        "anomaly_trace": None,
                    }
                ],
                "branch_summaries": [
                    {
                        "loss_kind": "main_loss",
                        "interaction_mode": "both_rows",
                    }
                ],
            },
            ["sudo", "-n", "docker", "run", talker_core_stabilization_variant],
        ),
    )

    report = run_stability_lab(
        Story31StabilityLabSettings(
            output_root=tmp_path,
            dockerfile_path=Path("Dockerfile"),
            image="test-image",
            model_id="test-model",
            hf_cache_dir=tmp_path / "hf",
            hf_cache_home_mount=tmp_path / "hf-home",
            output_root_home_mount_base=DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
            source_bundle_root=tmp_path / "bundle",
            manifest_family=DEFAULT_MANIFEST_FAMILY,
            source_lines=DEFAULT_SOURCE_LINES,
            text_embedding_mask_policy=DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
            hook_profile=DEFAULT_HOOK_PROFILE,
            stabilization_variants=("off", "layer16_gated_fp32"),
            build_image=False,
        )
    )
    persist_report(tmp_path, report)

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))

    assert payload["stabilization_variants"] == ["off", "layer16_gated_fp32"]
    assert len(payload["matrix_rows"]) == 2
    assert (tmp_path / "variant-reports" / "off.json").exists() is True
    assert (tmp_path / "variant-reports" / "layer16_gated_fp32.json").exists() is True
