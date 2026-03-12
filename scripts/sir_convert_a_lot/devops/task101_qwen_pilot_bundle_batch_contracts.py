"""Contracts and deterministic layout helpers for Task 101 batch finalization.

Purpose:
    Define the Task 101 batch-plan data model, on-disk artifact paths, and
    deterministic plan materialization/loading helpers.

Relationships:
    - Used by Task 101 bundle orchestration, batch execution, and progress
      tracking.
    - Reads copied Task 101 spool rows to derive stable per-family batch
      windows without running Qwen tokenizer work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    ManifestFamily,
    SpoolRow,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_spool_rows,
    write_json,
)

DEFAULT_FINALIZATION_BATCH_ROW_COUNT = 128
_BATCH_FILE_STEM_WIDTH = 5


@dataclass(frozen=True)
class Task101PilotBundleBatch:
    """One deterministic family-specific Task 101 finalization batch."""

    manifest_family: ManifestFamily
    batch_index: int
    row_start_index: int
    row_end_exclusive: int
    row_count: int
    first_row_key: str
    last_row_key: str


@dataclass(frozen=True)
class Task101PilotBundleBatchPlan:
    """Machine-readable batch plan for one Task 101 pilot-bundle root."""

    source_root: str
    output_root: str
    train_manifest_family: ManifestFamily
    eval_manifest_family: ManifestFamily
    tokenizer_model: str
    finalization_batch_row_count: int
    retained_row_count: int
    conflict_row_count: int
    family_row_counts: dict[ManifestFamily, int]
    owned_row_keys_path: str
    conflict_row_keys_path: str
    repo_head: str
    generated_at: str
    batches: list[Task101PilotBundleBatch]


def task101_pilot_bundle_batch_plan_path(output_root: Path) -> Path:
    """Return the canonical Task 101 batch-plan path."""
    return output_root / "reports" / "task101_pilot_bundle_plan.json"


def task101_pilot_bundle_progress_events_path(output_root: Path) -> Path:
    """Return the append-only Task 101 progress-events log path."""
    return output_root / "reports" / "task101_pilot_bundle_events.jsonl"


def task101_pilot_bundle_progress_state_path(output_root: Path) -> Path:
    """Return the derived Task 101 status path."""
    return output_root / "reports" / "task101_pilot_bundle_status.json"


def task101_pilot_bundle_curated_batch_path(
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> Path:
    """Return one batch-local curated-manifest shard path."""
    return (
        output_root
        / "curated"
        / "batches"
        / manifest_family
        / f"batch-{batch_index:0{_BATCH_FILE_STEM_WIDTH}d}.jsonl"
    )


def task101_pilot_bundle_raw_batch_path(
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> Path:
    """Return one batch-local raw-manifest shard path."""
    return (
        output_root
        / "manifests"
        / "batches"
        / manifest_family
        / f"batch-{batch_index:0{_BATCH_FILE_STEM_WIDTH}d}.raw.jsonl"
    )


def task101_pilot_bundle_prepared_batch_path(
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> Path:
    """Return one batch-local prepared-manifest shard path."""
    return (
        output_root
        / "manifests"
        / "batches"
        / manifest_family
        / f"batch-{batch_index:0{_BATCH_FILE_STEM_WIDTH}d}.prepared.jsonl"
    )


def selected_manifest_families(
    plan: Task101PilotBundleBatchPlan,
) -> tuple[ManifestFamily, ManifestFamily]:
    """Return the canonical train/eval family order for one batch plan."""
    return (plan.train_manifest_family, plan.eval_manifest_family)


def task101_pilot_bundle_batch_id(batch: Task101PilotBundleBatch) -> str:
    """Render a stable batch identifier for logs and progress files."""
    return f"{batch.manifest_family}:batch-{batch.batch_index:0{_BATCH_FILE_STEM_WIDTH}d}"


def render_task101_spool_row_key(spool_row: SpoolRow) -> str:
    """Render the canonical log-friendly row key for one Task 101 spool row."""
    return f"{spool_row.dataset}/{spool_row.source_split}/{spool_row.dataset_row_id}"


def build_task101_pilot_bundle_batch_plan(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str,
    finalization_batch_row_count: int,
    retained_row_count: int,
    conflict_row_count: int,
    owned_row_keys_path: Path,
    conflict_row_keys_path: Path,
    repo_head: str,
    generated_at: str,
) -> Task101PilotBundleBatchPlan:
    """Build and persist the deterministic Task 101 finalization batch plan."""
    if finalization_batch_row_count <= 0:
        raise ValueError("`finalization_batch_row_count` must be positive.")
    families = (train_manifest_family, eval_manifest_family)
    family_row_keys: dict[ManifestFamily, list[str]] = {family: [] for family in families}
    for spool_row in iter_spool_rows(output_root):
        for family in families:
            if family in spool_row.manifest_targets:
                family_row_keys[family].append(render_task101_spool_row_key(spool_row))
    batches: list[Task101PilotBundleBatch] = []
    family_row_counts: dict[ManifestFamily, int] = {}
    for family in families:
        row_keys = family_row_keys[family]
        family_row_counts[family] = len(row_keys)
        for batch_index, row_start_index in enumerate(
            range(0, len(row_keys), finalization_batch_row_count)
        ):
            batch_row_keys = row_keys[
                row_start_index : row_start_index + finalization_batch_row_count
            ]
            batches.append(
                Task101PilotBundleBatch(
                    manifest_family=family,
                    batch_index=batch_index,
                    row_start_index=row_start_index,
                    row_end_exclusive=row_start_index + len(batch_row_keys),
                    row_count=len(batch_row_keys),
                    first_row_key=batch_row_keys[0],
                    last_row_key=batch_row_keys[-1],
                )
            )
    plan = Task101PilotBundleBatchPlan(
        source_root=source_root.as_posix(),
        output_root=output_root.as_posix(),
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        retained_row_count=retained_row_count,
        conflict_row_count=conflict_row_count,
        family_row_counts=family_row_counts,
        owned_row_keys_path=owned_row_keys_path.as_posix(),
        conflict_row_keys_path=conflict_row_keys_path.as_posix(),
        repo_head=repo_head,
        generated_at=generated_at,
        batches=batches,
    )
    write_json(task101_pilot_bundle_batch_plan_path(output_root), plan)
    return plan


def load_task101_pilot_bundle_batch_plan(output_root: Path) -> Task101PilotBundleBatchPlan:
    """Load the machine-readable batch plan from one Task 101 bundle root."""
    payload = json.loads(task101_pilot_bundle_batch_plan_path(output_root).read_text("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Task 101 pilot bundle batch plan must be one JSON object.")
    raw_batches = payload.get("batches")
    if not isinstance(raw_batches, list):
        raise ValueError("Task 101 pilot bundle batch plan `batches` must be a list.")
    rendered_batches: list[Task101PilotBundleBatch] = []
    for raw_batch in raw_batches:
        if not isinstance(raw_batch, dict):
            raise ValueError("Task 101 pilot bundle batch entries must be JSON objects.")
        rendered_batches.append(
            Task101PilotBundleBatch(
                manifest_family=_required_manifest_family(raw_batch, "manifest_family"),
                batch_index=_required_int(raw_batch, "batch_index"),
                row_start_index=_required_int(raw_batch, "row_start_index"),
                row_end_exclusive=_required_int(raw_batch, "row_end_exclusive"),
                row_count=_required_int(raw_batch, "row_count"),
                first_row_key=_required_string(raw_batch, "first_row_key"),
                last_row_key=_required_string(raw_batch, "last_row_key"),
            )
        )
    family_row_counts_payload = payload.get("family_row_counts")
    if not isinstance(family_row_counts_payload, dict):
        raise ValueError("Task 101 pilot bundle batch plan `family_row_counts` is malformed.")
    family_row_counts: dict[ManifestFamily, int] = {}
    for family_name, row_count in family_row_counts_payload.items():
        if not isinstance(family_name, str):
            raise ValueError("Task 101 pilot bundle family row-count keys must be strings.")
        family_row_counts[_required_manifest_family({"family": family_name}, "family")] = int(
            row_count
        )
    return Task101PilotBundleBatchPlan(
        source_root=_required_string(payload, "source_root"),
        output_root=_required_string(payload, "output_root"),
        train_manifest_family=_required_manifest_family(payload, "train_manifest_family"),
        eval_manifest_family=_required_manifest_family(payload, "eval_manifest_family"),
        tokenizer_model=_required_string(payload, "tokenizer_model"),
        finalization_batch_row_count=_required_int(payload, "finalization_batch_row_count"),
        retained_row_count=_required_int(payload, "retained_row_count"),
        conflict_row_count=_required_int(payload, "conflict_row_count"),
        family_row_counts=family_row_counts,
        owned_row_keys_path=_required_string(payload, "owned_row_keys_path"),
        conflict_row_keys_path=_required_string(payload, "conflict_row_keys_path"),
        repo_head=_required_string(payload, "repo_head"),
        generated_at=_required_string(payload, "generated_at"),
        batches=rendered_batches,
    )


def _required_manifest_family(payload: dict[str, object], key: str) -> ManifestFamily:
    """Return one validated manifest-family string from a JSON payload."""
    value = _required_string(payload, key)
    if value == "swedish_smoke_train":
        return "swedish_smoke_train"
    if value == "swedish_pilot_train":
        return "swedish_pilot_train"
    if value == "swedish_scaleup_train":
        return "swedish_scaleup_train"
    if value == "swedish_checkpoint_dev":
        return "swedish_checkpoint_dev"
    if value == "swedish_final_test":
        return "swedish_final_test"
    if value == "swedish_waxholm_control":
        return "swedish_waxholm_control"
    raise ValueError(f"Malformed `{key}` manifest-family value: {value!r}.")


def _required_string(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    return value
