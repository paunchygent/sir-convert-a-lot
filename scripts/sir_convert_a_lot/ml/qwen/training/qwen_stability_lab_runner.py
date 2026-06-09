"""Host-side runner for the Qwen stability lab talker-core stability lab.

Purpose:
    Reuse the exact Qwen backward-lineage and fresh-start proof lane selected-row backward-lineage
    probe as a fast
    exploration vehicle, while varying bounded talker-core stabilization
    variants under one output root instead of minting a new proof package per
    hypothesis.

Relationships:
    - Used by `qwen_stability_lab.py` for the public Qwen stability lab CLI.
    - Reuses `qwen_backward_lineage_bundle.py` to materialize the exact
      failing-row mini-bundle and `qwen_backward_lineage_runner.py` to run
      the in-container probe against each stabilization variant.
"""

from __future__ import annotations

import json
import re
import shutil
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    TALKER_CORE_STABILIZATION_CHOICES,
)
from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
)
from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_downstream_convergence_assessment as downstream_convergence_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_fp32_scaled_layer15_output_assessment as fp32_scaled_output_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_layer15_output_multiply_confirmation_assessment as layer15_output_multiply_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_layer15_output_return_assessment as layer15_output_return_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_layer15_output_split_assessment as layer15_output_split_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_layer15_residual_output_assessment as layer15_residual_output_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_PILOT_BUNDLE_ROOT,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_bundle import (
    materialize_backward_lineage_bundle,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_DOWNSTREAM_CONVERGENCE_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE,
    TALKER_CORE_POST_SUB_TALKER_DISAGREEMENT_ROW_LOCAL_OUTLIER_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_runner import (
    BackwardLineageProofSettings,
    run_backward_lineage_probe,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_input_layernorm_internal_assessment import (
    build_input_layernorm_internal_assessment,
    validate_input_layernorm_internal_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_micro_family_assessment import (
    ROW_LOCAL_MICRO_FAMILY_REQUIRED_VARIANTS,
    build_row_local_micro_family_assessment,
    validate_row_local_micro_family_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_row_local_outlier_assessment import (
    build_row_local_outlier_assessment,
    validate_row_local_outlier_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    QwenStabilityLabReport,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_markdown import (
    build_report_markdown,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_sub_boundary_assessment import (
    build_sub_boundary_assessment,
    validate_hook_profile_variant_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_sub_talker_disagreement_assessment import (
    build_sub_talker_disagreement_assessment,
    validate_sub_talker_disagreement_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso

DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-stability-lab")
DEFAULT_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_SOURCE_LINES = (13, 4)
DEFAULT_TEXT_EMBEDDING_MASK_POLICY = "text_span_only"
DEFAULT_HOOK_PROFILE = "talker_core_boundary"
DEFAULT_STABILIZATION_VARIANTS = (
    "off",
    "layer16_gated_fp32",
    "layer16_gated_fp32_clamp_1e4",
)
DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/qwen-stability-lab-output-roots"
)
DEFAULT_SOURCE_BUNDLE_ROOT = DEFAULT_PILOT_BUNDLE_ROOT
_ANOMALY_OPERATOR_PATTERN = re.compile(r"([A-Za-z0-9_]+Backward0)")


@dataclass(frozen=True)
class _RunnerImageSettings:
    """Concrete image settings payload for Qwen stability lab host-side execution."""

    dockerfile_path: Path
    image: str
    build_image: bool


@dataclass(frozen=True)
class _RunnerCacheSettings:
    """Concrete HF cache settings payload for Qwen stability lab host-side execution."""

    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path


def parse_stabilization_variants(raw_value: str) -> tuple[str, ...]:
    """Parse a comma-separated stabilization variant list."""
    variants = tuple(piece.strip() for piece in raw_value.split(",") if piece.strip() != "")
    if len(variants) == 0:
        raise SystemExit(
            "Qwen stability lab stability lab requires at least one stabilization variant."
        )
    unsupported = [
        variant for variant in variants if variant not in TALKER_CORE_STABILIZATION_CHOICES
    ]
    if unsupported:
        raise SystemExit(
            "Qwen stability lab stability lab received unsupported talker-core stabilization "
            f"variants: {unsupported}."
        )
    return variants


def prepare_output_root(output_root: Path) -> tuple[Path, Path, Path]:
    """Create a clean deterministic output tree for one matrix run."""
    output_root.mkdir(parents=True, exist_ok=True)
    results_json_path = output_root / "results.json"
    results_md_path = output_root / "results.md"
    failure_path = output_root / "failure.txt"
    for generated_path in (results_json_path, results_md_path, failure_path):
        with suppress(FileNotFoundError):
            generated_path.unlink()
    shutil.rmtree(_mini_bundle_root(output_root), ignore_errors=True)
    shutil.rmtree(_variant_reports_root(output_root), ignore_errors=True)
    return results_json_path, results_md_path, failure_path


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def run_stability_lab(settings: QwenStabilityLabSettings) -> QwenStabilityLabReport:
    """Run the Qwen stability lab stability-lab matrix and return its compact report."""
    prepare_output_root(settings.output_root)
    validate_hook_profile_variant_contract(settings)
    validate_input_layernorm_internal_contract(settings)
    validate_sub_talker_disagreement_contract(settings)
    _validate_row_local_hook_contract(settings)
    downstream_convergence_assessment.validate_downstream_convergence_contract(settings)
    layer15_output_split_assessment.validate_layer15_output_split_contract(settings)
    layer15_residual_output_assessment.validate_layer15_residual_output_contract(settings)
    layer15_output_return_assessment.validate_layer15_output_return_contract(settings)
    layer15_output_multiply_assessment.validate_layer15_output_multiply_confirmation_contract(
        settings
    )
    fp32_scaled_output_assessment.validate_fp32_scaled_layer15_output_contract(settings)
    build_performed, image_id = prepare_qwen_image(
        _RunnerImageSettings(
            dockerfile_path=settings.dockerfile_path,
            image=settings.image,
            build_image=settings.build_image,
        )
    )
    hf_mount = resolve_effective_hf_cache_dir(
        _RunnerCacheSettings(
            image=settings.image,
            hf_cache_dir=settings.hf_cache_dir,
            hf_cache_home_mount=settings.hf_cache_home_mount,
        )
    )
    output_mount = resolve_effective_bind_root(
        settings.output_root,
        _output_root_home_mount(
            settings.output_root,
            home_mount_base=settings.output_root_home_mount_base,
        ),
        image=settings.image,
        sync_home_into_canonical=False,
    )
    mini_bundle = materialize_backward_lineage_bundle(
        source_bundle_root=settings.source_bundle_root,
        target_bundle_root=_mini_bundle_root(settings.output_root),
        manifest_family=settings.manifest_family,
        selected_source_lines=settings.source_lines,
    )
    variant_report_paths: dict[str, str] = {}
    probe_commands: dict[str, list[str]] = {}
    matrix_rows: list[StabilityLabMatrixRow] = []
    for variant in settings.stabilization_variants:
        probe_payload, probe_command = run_backward_lineage_probe(
            _backward_lineage_settings(settings),
            hf_mount=hf_mount,
            output_mount=output_mount,
            mini_bundle=mini_bundle,
            talker_core_stabilization_variant=variant,
        )
        variant_report_path = _variant_report_path(settings.output_root, variant)
        write_json(variant_report_path, probe_payload)
        variant_report_paths[variant] = variant_report_path.as_posix()
        probe_commands[variant] = probe_command
        matrix_rows.extend(
            _build_matrix_rows(probe_payload=probe_payload, stabilization_variant=variant)
        )
    compact_matrix_rows = tuple(matrix_rows)
    return QwenStabilityLabReport(
        generated_at=utc_now_iso(),
        image=settings.image,
        image_id=image_id,
        build_performed=build_performed,
        model_id=settings.model_id,
        source_bundle_root=settings.source_bundle_root.as_posix(),
        manifest_family=settings.manifest_family,
        source_line_numbers=settings.source_lines,
        text_embedding_mask_policy=settings.text_embedding_mask_policy,
        hook_profile=settings.hook_profile,
        stabilization_variants=settings.stabilization_variants,
        mini_bundle=asdict(mini_bundle),
        hf_cache_dir=settings.hf_cache_dir.as_posix(),
        effective_hf_cache_dir=hf_mount.effective_root.as_posix(),
        used_home_mount=hf_mount.used_home_mount,
        effective_output_root=output_mount.effective_root.as_posix(),
        used_output_root_home_mount=output_mount.used_home_mount,
        variant_report_paths=variant_report_paths,
        probe_commands=probe_commands,
        matrix_rows=compact_matrix_rows,
        sub_boundary_assessment=build_sub_boundary_assessment(
            settings=settings,
            matrix_rows=compact_matrix_rows,
        ),
        input_layernorm_internal_assessment=build_input_layernorm_internal_assessment(
            settings=settings,
            matrix_rows=compact_matrix_rows,
        ),
        sub_talker_disagreement_assessment=build_sub_talker_disagreement_assessment(
            settings=settings,
            matrix_rows=compact_matrix_rows,
        ),
        row_local_outlier_assessment=build_row_local_outlier_assessment(
            settings=settings,
            matrix_rows=compact_matrix_rows,
        ),
        row_local_micro_family_assessment=(
            build_row_local_micro_family_assessment(
                settings=settings,
                matrix_rows=compact_matrix_rows,
            )
        ),
        downstream_convergence_assessment=(
            downstream_convergence_assessment.build_downstream_convergence_assessment(
                settings=settings,
                matrix_rows=compact_matrix_rows,
            )
        ),
        layer15_output_split_assessment=(
            layer15_output_split_assessment.build_layer15_output_split_assessment(
                settings=settings,
                matrix_rows=compact_matrix_rows,
            )
        ),
        layer15_residual_output_assessment=(
            layer15_residual_output_assessment.build_layer15_residual_output_assessment(
                settings=settings,
                matrix_rows=compact_matrix_rows,
            )
        ),
        layer15_output_return_assessment=(
            layer15_output_return_assessment.build_layer15_output_return_assessment(
                settings=settings,
                matrix_rows=compact_matrix_rows,
            )
        ),
        layer15_output_multiply_confirmation_assessment=(
            layer15_output_multiply_assessment.build_layer15_output_multiply_confirmation_assessment(
                settings=settings,
                matrix_rows=compact_matrix_rows,
            )
        ),
        fp32_scaled_layer15_output_assessment=(
            fp32_scaled_output_assessment.build_fp32_scaled_layer15_output_assessment(
                settings=settings,
                matrix_rows=compact_matrix_rows,
            )
        ),
    )


def _validate_row_local_hook_contract(settings: QwenStabilityLabSettings) -> None:
    """Dispatch the shared row-local outlier/row-local micro-family hook profile to the correct
    validator.
    """
    if (
        settings.hook_profile
        == TALKER_CORE_POST_DOWNSTREAM_CONVERGENCE_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE
    ):
        validate_row_local_outlier_contract(settings)
        validate_row_local_micro_family_contract(settings)
        return
    if (
        settings.hook_profile
        != TALKER_CORE_POST_SUB_TALKER_DISAGREEMENT_ROW_LOCAL_OUTLIER_HOOK_PROFILE
    ):
        validate_row_local_outlier_contract(settings)
        validate_row_local_micro_family_contract(settings)
        return
    if settings.stabilization_variants == ROW_LOCAL_MICRO_FAMILY_REQUIRED_VARIANTS:
        validate_row_local_micro_family_contract(settings)
        return
    validate_row_local_outlier_contract(settings)


def persist_report(output_root: Path, report: QwenStabilityLabReport) -> tuple[Path, Path]:
    """Persist the compact Qwen stability lab lab artifacts under one output root."""
    results_json_path = output_root / "results.json"
    results_md_path = output_root / "results.md"
    write_json(results_json_path, asdict(report))
    write_markdown(results_md_path, build_report_markdown(report))
    return results_json_path, results_md_path


def _backward_lineage_settings(
    settings: QwenStabilityLabSettings,
) -> BackwardLineageProofSettings:
    return BackwardLineageProofSettings(
        output_root=settings.output_root,
        dockerfile_path=settings.dockerfile_path,
        image=settings.image,
        model_id=settings.model_id,
        hf_cache_dir=settings.hf_cache_dir,
        hf_cache_home_mount=settings.hf_cache_home_mount,
        output_root_home_mount_base=settings.output_root_home_mount_base,
        source_bundle_root=settings.source_bundle_root,
        manifest_family=settings.manifest_family,
        source_lines=settings.source_lines,
        text_embedding_mask_policy=settings.text_embedding_mask_policy,
        hook_profile=settings.hook_profile,
        build_image=False,
    )


def _mini_bundle_root(output_root: Path) -> Path:
    return output_root / "mini-bundle"


def _variant_reports_root(output_root: Path) -> Path:
    return output_root / "variant-reports"


def _variant_report_path(output_root: Path, variant: str) -> Path:
    return _variant_reports_root(output_root) / f"{variant}.json"


def _output_root_home_mount(output_root: Path, *, home_mount_base: Path) -> Path:
    if not output_root.is_absolute():
        return output_root
    return home_mount_base / output_root.relative_to("/")


def _build_matrix_rows(
    *,
    probe_payload: dict[str, object],
    stabilization_variant: str,
) -> tuple[StabilityLabMatrixRow, ...]:
    interaction_modes = _interaction_modes_by_loss(probe_payload)
    cases_value = probe_payload.get("cases")
    if not isinstance(cases_value, list):
        raise SystemExit("Qwen stability lab stability lab probe payload was missing `cases`.")
    rows: list[StabilityLabMatrixRow] = []
    for case in cases_value:
        if not isinstance(case, dict):
            raise SystemExit("Qwen stability lab stability lab case payload was malformed.")
        loss_kind = _required_str(case, "loss_kind")
        rows.append(
            StabilityLabMatrixRow(
                stabilization_variant=stabilization_variant,
                case_id=_required_str(case, "case_id"),
                loss_kind=loss_kind,
                source_line_numbers=_required_int_tuple(case, "source_line_numbers"),
                batch_size=_required_int(case, "batch_size"),
                interaction_mode=interaction_modes.get(loss_kind, "unknown"),
                case_has_non_finite=_case_has_non_finite(case),
                first_non_finite_hook_tensor=_optional_str(case, "first_non_finite_hook_tensor"),
                first_non_finite_talker_core_hook_tensor=_optional_str(
                    case,
                    "first_non_finite_talker_core_hook_tensor",
                ),
                gradient_rca_first_non_finite_surface=_nested_optional_str(
                    case,
                    "gradient_rca",
                    "first_non_finite_surface",
                ),
                parameter_first_non_finite_surface=_nested_optional_str(
                    case,
                    "parameter_gradient_probes",
                    "first_non_finite_surface",
                ),
                anomaly_operator=_extract_anomaly_operator(_optional_str(case, "anomaly_trace")),
            )
        )
    return tuple(rows)


def _interaction_modes_by_loss(probe_payload: dict[str, object]) -> dict[str, str]:
    branch_summaries = probe_payload.get("branch_summaries")
    if not isinstance(branch_summaries, list):
        raise SystemExit(
            "Qwen stability lab stability lab probe payload was missing `branch_summaries`."
        )
    interaction_modes: dict[str, str] = {}
    for summary in branch_summaries:
        if not isinstance(summary, dict):
            raise SystemExit(
                "Qwen stability lab stability lab branch summary payload was malformed."
            )
        interaction_modes[_required_str(summary, "loss_kind")] = _required_str(
            summary,
            "interaction_mode",
        )
    return interaction_modes


def _case_has_non_finite(case: dict[str, object]) -> bool:
    if _optional_str(case, "first_non_finite_hook_tensor") is not None:
        return True
    for nested_key in ("gradient_rca", "parameter_gradient_probes"):
        nested_surface = _nested_optional_str(case, nested_key, "first_non_finite_surface")
        if nested_surface is not None:
            return True
    return False


def _extract_anomaly_operator(anomaly_trace: str | None) -> str | None:
    if anomaly_trace is None:
        return None
    match = _ANOMALY_OPERATOR_PATTERN.search(anomaly_trace)
    return None if match is None else match.group(1)


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Qwen stability lab stability lab payload missing string `{key}`.")
    return value


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Qwen stability lab stability lab payload missing integer `{key}`.")
    return value


def _required_int_tuple(payload: dict[str, object], key: str) -> tuple[int, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        raise SystemExit(f"Qwen stability lab stability lab payload missing integer-list `{key}`.")
    return tuple(value)


def _nested_optional_str(
    payload: dict[str, object],
    nested_key: str,
    field_key: str,
) -> str | None:
    value = payload.get(nested_key)
    if not isinstance(value, dict):
        return None
    nested_value = value.get(field_key)
    return nested_value if isinstance(nested_value, str) else None
