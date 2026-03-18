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
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_PILOT_BUNDLE_ROOT,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_bundle import (
    BackwardLineageMiniBundle,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab import main
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    StabilityLabMatrixRow,
    Story31SubBoundaryAssessment,
    Story31StabilityLabReport,
    Story31StabilityLabSettings,
    SubBoundaryComparisonRow,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_sub_boundary_assessment import (
    build_sub_boundary_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_runner import (
    DEFAULT_HOOK_PROFILE,
    DEFAULT_MANIFEST_FAMILY,
    DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
    DEFAULT_SOURCE_BUNDLE_ROOT,
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


def test_default_source_bundle_root_reuses_canonical_training_bundle_default() -> None:
    """Story 31 should inherit the canonical Task 101 pilot bundle default."""
    assert DEFAULT_SOURCE_BUNDLE_ROOT == DEFAULT_PILOT_BUNDLE_ROOT


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
        sub_boundary_assessment=None,
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
    assert payload["sub_boundary_assessment"] is None
    assert (tmp_path / "variant-reports" / "off.json").exists() is True
    assert (tmp_path / "variant-reports" / "layer16_gated_fp32.json").exists() is True


def test_build_sub_boundary_assessment_constrains_t230_to_one_micro_family() -> None:
    """T229 should shape T230 from the narrowed pair-vs-single sub-boundary evidence."""
    assessment = build_sub_boundary_assessment(
        settings=Story31StabilityLabSettings(
            output_root=Path("/tmp/story31"),
            dockerfile_path=Path("Dockerfile"),
            image="test-image",
            model_id="test-model",
            hf_cache_dir=Path("/tmp/hf"),
            hf_cache_home_mount=Path("/tmp/hf-home"),
            output_root_home_mount_base=DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
            source_bundle_root=Path("/tmp/bundle"),
            manifest_family=DEFAULT_MANIFEST_FAMILY,
            source_lines=(13, 4),
            text_embedding_mask_policy=DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
            hook_profile="talker_core_handoff_sub_boundary",
            stabilization_variants=(
                "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5",
            ),
            build_image=False,
        ),
        matrix_rows=(
            StabilityLabMatrixRow(
                stabilization_variant="layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5",
                case_id="pair-sub-talker-loss",
                loss_kind="sub_talker_loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                interaction_mode="both_rows",
                case_has_non_finite=True,
                first_non_finite_hook_tensor="talker_core.layer_16.input_layernorm",
                first_non_finite_talker_core_hook_tensor="talker_core.layer_16.input_layernorm",
                gradient_rca_first_non_finite_surface="input_text_embedding.grad",
                parameter_first_non_finite_surface="text_embedding.weight.grad",
                anomaly_operator=None,
            ),
            StabilityLabMatrixRow(
                stabilization_variant="layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5",
                case_id="line-13-sub-talker-loss",
                loss_kind="sub_talker_loss",
                source_line_numbers=(13,),
                batch_size=1,
                interaction_mode="both_rows",
                case_has_non_finite=True,
                first_non_finite_hook_tensor="talker_core.layer_16.input_layernorm",
                first_non_finite_talker_core_hook_tensor="talker_core.layer_16.input_layernorm",
                gradient_rca_first_non_finite_surface="input_text_embedding.grad",
                parameter_first_non_finite_surface="text_embedding.weight.grad",
                anomaly_operator=None,
            ),
            StabilityLabMatrixRow(
                stabilization_variant="layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5",
                case_id="line-4-sub-talker-loss",
                loss_kind="sub_talker_loss",
                source_line_numbers=(4,),
                batch_size=1,
                interaction_mode="both_rows",
                case_has_non_finite=True,
                first_non_finite_hook_tensor="talker_core.layer_16.input_layernorm",
                first_non_finite_talker_core_hook_tensor="talker_core.layer_16.input_layernorm",
                gradient_rca_first_non_finite_surface="input_text_embedding.grad",
                parameter_first_non_finite_surface="text_embedding.weight.grad",
                anomaly_operator=None,
            ),
        ),
    )

    assert assessment == Story31SubBoundaryAssessment(
        stabilization_variant="layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5",
        target_loss_kind="sub_talker_loss",
        target_sub_boundaries=(
            "talker_core.layer_16.mlp.down_proj",
            "talker_core.layer_16.output",
            "talker_core.layer_16.residual_handoff",
            "talker_core.layer_16.input_layernorm",
        ),
        comparison_rows=(
            SubBoundaryComparisonRow(
                case_id="pair-sub-talker-loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                role="pair",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_16.input_layernorm",
                matched_sub_boundary="talker_core.layer_16.input_layernorm",
            ),
            SubBoundaryComparisonRow(
                case_id="line-13-sub-talker-loss",
                source_line_numbers=(13,),
                batch_size=1,
                role="first_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_16.input_layernorm",
                matched_sub_boundary="talker_core.layer_16.input_layernorm",
            ),
            SubBoundaryComparisonRow(
                case_id="line-4-sub-talker-loss",
                source_line_numbers=(4,),
                batch_size=1,
                role="second_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_16.input_layernorm",
                matched_sub_boundary="talker_core.layer_16.input_layernorm",
            ),
        ),
        earliest_sub_boundary="talker_core.layer_16.input_layernorm",
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_micro_family_rule=(
            "T230 may test one pre-input-layernorm normalization-entry micro-family only."
        ),
    )
