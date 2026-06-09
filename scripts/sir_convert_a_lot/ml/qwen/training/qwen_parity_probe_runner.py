"""Host-side runner for the Qwen stability lab deterministic parity probe.

Purpose:
    Execute the exact `the diagnostic lane` failure-family comparison under one local output
    root, then classify whether the first divergence is an invalid parity
    setup, a finite pre-boundary mismatch, a non-finite-boundary mismatch, or
    no meaningful divergence at all.

Relationships:
    - Used by `qwen_parity_probe.py` for the public CLI surface.
    - Delegates per-path execution to `qwen_parity_probe_runtime.py`.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_parity_probe_contracts import (
    DEFAULT_PATH_LABEL_CURRENT,
    DEFAULT_PATH_LABEL_INTENDED,
    QwenParityCheckpointComparison,
    QwenParityPathReport,
    QwenParityProbeReport,
    QwenParityProbeSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_parity_probe_runtime import (
    run_parity_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso

_CHECKPOINT_ORDER = (
    "selected_rows",
    "per_item_dataset_output",
    "collated_batch_tensors",
    "runtime_posture",
    "forward_entry_surfaces",
    "loss_decomposition",
    "backward_pre_clip",
    "clip_boundary",
    "optimizer_preconditions",
)
_PRE_FORWARD_CHECKPOINTS = {
    "selected_rows",
    "per_item_dataset_output",
    "collated_batch_tensors",
    "runtime_posture",
}


def prepare_output_root(output_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    """Create a clean deterministic output tree for one parity run."""
    output_root.mkdir(parents=True, exist_ok=True)
    results_json_path = output_root / "results.json"
    results_md_path = output_root / "results.md"
    failure_path = output_root / "failure.txt"
    current_path_json = output_root / "current-path.json"
    intended_path_json = output_root / "intended-path.json"
    shutil.rmtree(output_root / DEFAULT_PATH_LABEL_CURRENT, ignore_errors=True)
    shutil.rmtree(output_root / DEFAULT_PATH_LABEL_INTENDED, ignore_errors=True)
    for generated_path in (
        results_json_path,
        results_md_path,
        failure_path,
        current_path_json,
        intended_path_json,
    ):
        if generated_path.exists():
            generated_path.unlink()
    return results_json_path, results_md_path, failure_path, current_path_json, intended_path_json


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


def run_qwen_parity_probe(settings: QwenParityProbeSettings) -> QwenParityProbeReport:
    """Run the deterministic Qwen stability lab parity probe and classify its result."""
    output_root = settings.output_root
    _, _, failure_path, _, _ = prepare_output_root(output_root)
    try:
        current_path = run_parity_path(settings, path_label=DEFAULT_PATH_LABEL_CURRENT)
        intended_path = run_parity_path(settings, path_label=DEFAULT_PATH_LABEL_INTENDED)
    except Exception as error:
        write_markdown(failure_path, f"# Qwen stability lab Parity Probe Failure\n\n`{error!r}`")
        raise
    comparisons = _checkpoint_comparisons(current_path=current_path, intended_path=intended_path)
    first_divergence_checkpoint = next(
        (comparison.checkpoint_name for comparison in comparisons if comparison.matches is False),
        None,
    )
    classification = _classify_divergence(
        first_divergence_checkpoint=first_divergence_checkpoint,
        comparisons=comparisons,
    )
    return QwenParityProbeReport(
        generated_at=utc_now_iso(),
        output_root=output_root.as_posix(),
        source_bundle_root=settings.source_bundle_root.as_posix(),
        image=settings.image,
        model_id=settings.model_id,
        train_manifest_family=settings.train_manifest_family,
        eval_manifest_family=settings.eval_manifest_family,
        manifest_lines=settings.manifest_lines,
        batch_size=settings.batch_size,
        gradient_accumulation_steps=settings.gradient_accumulation_steps,
        text_embedding_assembly_mode=settings.text_embedding_assembly_mode,
        text_embedding_mask_policy=settings.text_embedding_mask_policy,
        max_steps=settings.max_steps,
        current_path_report_path=(output_root / "current-path.json").as_posix(),
        intended_path_report_path=(output_root / "intended-path.json").as_posix(),
        current_path=current_path,
        intended_path=intended_path,
        checkpoint_comparisons=tuple(comparisons),
        first_divergence_checkpoint=first_divergence_checkpoint,
        first_divergence_classification=classification,
        recommended_next_step=_recommended_next_step(classification),
        summary=_summary_text(
            classification=classification,
            first_divergence_checkpoint=first_divergence_checkpoint,
        ),
    )


def persist_report(
    output_root: Path,
    report: QwenParityProbeReport,
) -> tuple[Path, Path, Path, Path]:
    """Persist the path artifacts plus the compact parity summary report."""
    results_json_path = output_root / "results.json"
    results_md_path = output_root / "results.md"
    current_path_json = output_root / "current-path.json"
    intended_path_json = output_root / "intended-path.json"
    write_json(current_path_json, asdict(report.current_path))
    write_json(intended_path_json, asdict(report.intended_path))
    write_json(results_json_path, asdict(report))
    write_markdown(results_md_path, build_report_markdown(report))
    return results_json_path, results_md_path, current_path_json, intended_path_json


def build_report_markdown(report: QwenParityProbeReport) -> str:
    """Render one concise markdown summary for the Qwen stability lab parity report."""
    lines = [
        "# Qwen stability lab Parity Probe",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Source bundle root: `{report.source_bundle_root}`",
        f"- Train manifest family: `{report.train_manifest_family}`",
        f"- Eval manifest family: `{report.eval_manifest_family}`",
        f"- Manifest lines: `{report.manifest_lines}`",
        f"- Batch size: `{report.batch_size}`",
        f"- Gradient accumulation steps: `{report.gradient_accumulation_steps}`",
        f"- Text embedding assembly mode: `{report.text_embedding_assembly_mode}`",
        f"- Text embedding mask policy: `{report.text_embedding_mask_policy}`",
        f"- Classification: `{report.first_divergence_classification}`",
        f"- First divergence checkpoint: `{report.first_divergence_checkpoint or 'none'}`",
        f"- Recommended next step: `{report.recommended_next_step}`",
        "",
        "## Checkpoint Comparison",
        "",
        "| Checkpoint | Matches | Current Non-finite | Intended Non-finite |",
        "| --- | --- | --- | --- |",
    ]
    for comparison in report.checkpoint_comparisons:
        lines.append(
            "| "
            f"{comparison.checkpoint_name} | "
            f"{comparison.matches} | "
            f"{comparison.current_has_non_finite} | "
            f"{comparison.intended_has_non_finite} |"
        )
    lines.extend(
        [
            "",
            "## Path Outcomes",
            "",
            f"- Current path status: `{report.current_path.execution_outcome.get('status')}`",
            f"- Intended path status: `{report.intended_path.execution_outcome.get('status')}`",
            f"- Summary: {report.summary}",
        ]
    )
    return "\n".join(lines)


def _checkpoint_comparisons(
    *,
    current_path: QwenParityPathReport,
    intended_path: QwenParityPathReport,
) -> list[QwenParityCheckpointComparison]:
    comparisons: list[QwenParityCheckpointComparison] = []
    for checkpoint_name in _CHECKPOINT_ORDER:
        current_payload = getattr(current_path, checkpoint_name)
        intended_payload = getattr(intended_path, checkpoint_name)
        comparisons.append(
            QwenParityCheckpointComparison(
                checkpoint_name=checkpoint_name,
                matches=_canonical_payload(current_payload) == _canonical_payload(intended_payload),
                current_has_non_finite=_payload_has_non_finite(current_payload),
                intended_has_non_finite=_payload_has_non_finite(intended_payload),
            )
        )
    return comparisons


def _classify_divergence(
    *,
    first_divergence_checkpoint: str | None,
    comparisons: list[QwenParityCheckpointComparison],
) -> str:
    if first_divergence_checkpoint is None:
        return "no_meaningful_divergence_found"
    if first_divergence_checkpoint in _PRE_FORWARD_CHECKPOINTS:
        return "invalid_parity_input_contract"
    first_divergence = next(
        comparison
        for comparison in comparisons
        if comparison.checkpoint_name == first_divergence_checkpoint
    )
    if first_divergence.current_has_non_finite or first_divergence.intended_has_non_finite:
        return "divergence_at_non_finite_boundary"
    return "divergence_before_non_finite_boundary"


def _recommended_next_step(classification: str) -> str:
    if classification == "invalid_parity_input_contract":
        return "repair_t226_parity_inputs_before_inference"
    if classification == "divergence_before_non_finite_boundary":
        return "promote_to_t227_remediation"
    if classification == "divergence_at_non_finite_boundary":
        return "record_boundary_only_divergence_then_decide_t227_vs_t219"
    return "return_to_t219_if_no_higher_priority_runtime_bug_is_found"


def _summary_text(
    *,
    classification: str,
    first_divergence_checkpoint: str | None,
) -> str:
    if classification == "invalid_parity_input_contract":
        return (
            "The two paths already disagree before model-forward parity, so this run cannot be "
            "used for mechanism inference."
        )
    if classification == "divergence_before_non_finite_boundary":
        return (
            "The first mismatch appears while compared checkpoints are still finite, which is "
            "sufficient to escalate into trainer/runtime parity remediation."
        )
    if classification == "divergence_at_non_finite_boundary":
        return (
            "No earlier mismatch was observed; the first divergence appears only when the window "
            f"reaches `{first_divergence_checkpoint}`."
        )
    return (
        "No meaningful checkpoint divergence was found before or at the compared non-finite "
        "window, so the parity slice does not yet justify a trainer/runtime fix by itself."
    )


def _canonical_payload(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _payload_has_non_finite(payload: object) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.startswith("first_non_finite") and isinstance(value, str):
                return True
            if key.endswith("has_non_finite") and value is True:
                return True
            if key.endswith("is_finite") and value is False:
                return True
            if _payload_has_non_finite(value):
                return True
        return False
    if isinstance(payload, list):
        return any(_payload_has_non_finite(item) for item in payload)
    if isinstance(payload, tuple):
        return any(_payload_has_non_finite(item) for item in payload)
    return False
