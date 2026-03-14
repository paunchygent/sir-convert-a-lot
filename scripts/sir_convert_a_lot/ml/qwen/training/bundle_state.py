"""State and parsing helpers for Qwen training bundles.

Purpose:
    Own progress-state persistence, UTC/git utilities, and deterministic JSON
    parsing for training-bundle plans and reports.

Relationships:
    - Imported by `ml.qwen.training.bundles` for canonical bundle orchestration.
    - Consumes bundle data contracts from `ml.qwen.training.bundle_contracts`.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import RowKey
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import write_json
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_contracts import (
    BundleBatch,
    BundleBatchPlan,
    BundlePrecomputedReferenceInputSummary,
    BundleSummary,
)


def git_head(repo_root: Path) -> str:
    """Return the current git HEAD SHA for one repository root."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bundle_build_log_path(output_root: Path) -> Path:
    """Return the canonical host-side build log path for one bundle root."""
    return output_root / "reports" / "build.log"


def bundle_build_exit_path(output_root: Path) -> Path:
    """Return the canonical host-side build exit marker path for one bundle root."""
    return output_root / "reports" / "build.exit"


def bundle_batch_log_path(
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> Path:
    """Return the canonical streaming log path for one governed batch."""
    return output_root / "reports" / "batches" / manifest_family / f"batch-{batch_index:05d}.log"


def append_log_line(path: Path, line: str) -> None:
    """Append one operator-facing log line and flush it immediately."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip("\n") + "\n")


def append_progress_event(
    output_root: Path,
    *,
    events_path: Path,
    event: dict[str, object],
) -> None:
    """Append one deterministic progress event for bundle finalization."""
    del output_root
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def write_progress_state(
    output_root: Path,
    *,
    status_path: Path,
    status: str,
    completed_batch_count: int,
    total_batch_count: int,
    current_phase: str | None = None,
    current_manifest_family: ManifestFamily | None = None,
    current_batch_index: int | None = None,
    current_batch_log_path: str | None = None,
    current_batch_started_at: str | None = None,
    last_completed_manifest_family: ManifestFamily | None = None,
    last_completed_batch_index: int | None = None,
    last_completed_at: str | None = None,
) -> None:
    """Persist the latest summary state for one bundle build."""
    del output_root
    write_json(
        status_path,
        {
            "status": status,
            "completed_batch_count": completed_batch_count,
            "total_batch_count": total_batch_count,
            "current_phase": current_phase,
            "current_manifest_family": current_manifest_family,
            "current_batch_index": current_batch_index,
            "current_batch_log_path": current_batch_log_path,
            "current_batch_started_at": current_batch_started_at,
            "last_completed_manifest_family": last_completed_manifest_family,
            "last_completed_batch_index": last_completed_batch_index,
            "last_completed_at": last_completed_at,
            "updated_at": utc_now_iso(),
        },
    )


def load_batch_plan(path: Path) -> BundleBatchPlan:
    """Load one deterministic bundle batch plan from disk."""
    payload = _load_required_object(path)
    batches_payload = payload.get("batches")
    if not isinstance(batches_payload, list):
        raise ValueError("Training bundle batch plan contained malformed `batches`.")
    batches: list[BundleBatch] = []
    for batch_payload in batches_payload:
        if not isinstance(batch_payload, dict):
            raise ValueError("Training bundle batch plan contained a non-object batch entry.")
        batches.append(
            BundleBatch(
                manifest_family=_required_manifest_family(batch_payload, "manifest_family"),
                batch_index=_required_int(batch_payload, "batch_index"),
                row_count=_required_int(batch_payload, "row_count"),
                first_row_key=_required_row_key(batch_payload, "first_row_key"),
                last_row_key=_required_row_key(batch_payload, "last_row_key"),
            )
        )
    return BundleBatchPlan(
        source_root=_required_str(payload, "source_root"),
        output_root=_required_str(payload, "output_root"),
        train_manifest_family=_required_manifest_family(payload, "train_manifest_family"),
        eval_manifest_family=_required_manifest_family(payload, "eval_manifest_family"),
        tokenizer_model=_required_str(payload, "tokenizer_model"),
        finalization_batch_row_count=_required_int(payload, "finalization_batch_row_count"),
        retained_row_count=_required_int(payload, "retained_row_count"),
        conflict_row_count=_required_int(payload, "conflict_row_count"),
        owned_row_keys_path=_required_str(payload, "owned_row_keys_path"),
        conflict_row_keys_path=_required_str(payload, "conflict_row_keys_path"),
        repo_head=_required_str(payload, "repo_head"),
        generated_at=_required_str(payload, "generated_at"),
        family_row_counts=_required_family_counts(payload, "family_row_counts"),
        batches=batches,
    )


def load_bundle_summary(path: Path) -> BundleSummary:
    """Load one existing bundle summary from disk."""
    payload = _load_required_object(path)
    precomputed_payload = _required_object(payload, "precomputed_reference_input")
    return BundleSummary(
        source_root=_required_str(payload, "source_root"),
        output_root=_required_str(payload, "output_root"),
        train_manifest_family=_required_manifest_family(payload, "train_manifest_family"),
        eval_manifest_family=_required_manifest_family(payload, "eval_manifest_family"),
        tokenizer_model=_required_str(payload, "tokenizer_model"),
        retained_row_count=_required_int(payload, "retained_row_count"),
        conflict_row_count=_required_int(payload, "conflict_row_count"),
        manifest_row_counts=_required_family_counts(payload, "manifest_row_counts"),
        speaker_counts=_required_family_counts(payload, "speaker_counts"),
        owned_row_keys_path=_required_str(payload, "owned_row_keys_path"),
        conflict_row_keys_path=_required_str(payload, "conflict_row_keys_path"),
        repo_head=_required_str(payload, "repo_head"),
        generated_at=_required_str(payload, "generated_at"),
        finalization_batch_row_count=_required_int(payload, "finalization_batch_row_count"),
        total_batch_count=_required_int(payload, "total_batch_count"),
        batch_plan_path=_required_str(payload, "batch_plan_path"),
        events_path=_required_str(payload, "events_path"),
        status_path=_required_str(payload, "status_path"),
        precomputed_reference_input=BundlePrecomputedReferenceInputSummary(
            kind=_required_str(precomputed_payload, "kind"),
            version=_required_str(precomputed_payload, "version"),
            source_field=_required_str(precomputed_payload, "source_field"),
            artifact_root=_required_str(precomputed_payload, "artifact_root"),
            artifact_count=_required_int(precomputed_payload, "artifact_count"),
        ),
    )


def find_batch(
    plan: BundleBatchPlan,
    *,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> BundleBatch:
    """Return the selected batch or raise a deterministic error."""
    for batch in plan.batches:
        if batch.manifest_family == manifest_family and batch.batch_index == batch_index:
            return batch
    raise ValueError(
        "Bundle batch plan did not contain the requested batch: "
        f"family={manifest_family} batch_index={batch_index}"
    )


def _load_required_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Training bundle payload in `{path}` was not a JSON object.")
    return payload


def _required_object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Training bundle payload missing object `{key}`.")
    return value


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Training bundle payload missing string `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Training bundle payload missing integer `{key}`.")
    return value


def _required_manifest_family(payload: dict[str, object], key: str) -> ManifestFamily:
    raw_value = payload.get(key)
    if raw_value == "swedish_pilot_train":
        return "swedish_pilot_train"
    if raw_value == "swedish_checkpoint_dev":
        return "swedish_checkpoint_dev"
    raise ValueError(f"Training bundle payload contained invalid manifest family `{key}`.")


def _required_family_counts(payload: dict[str, object], key: str) -> dict[ManifestFamily, int]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Training bundle payload missing object `{key}`.")
    counts: dict[ManifestFamily, int] = {}
    for raw_family, raw_count in value.items():
        if raw_family == "swedish_pilot_train":
            manifest_family: ManifestFamily = "swedish_pilot_train"
        elif raw_family == "swedish_checkpoint_dev":
            manifest_family = "swedish_checkpoint_dev"
        else:
            raise ValueError(f"Training bundle payload contained invalid family `{raw_family}`.")
        if not isinstance(raw_count, int):
            raise ValueError(
                f"Training bundle payload contained non-integer count for `{raw_family}`."
            )
        counts[manifest_family] = raw_count
    return counts


def _required_row_key(payload: dict[str, object], key: str) -> RowKey:
    value = payload.get(key)
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"Training bundle payload contained invalid row key `{key}`.")
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"Training bundle payload contained non-string row key `{key}`.")
    dataset, source_split, dataset_row_id = value
    return (dataset, source_split, dataset_row_id)
