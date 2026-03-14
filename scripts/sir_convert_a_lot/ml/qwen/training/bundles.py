"""Training-bundle materialization for Qwen fine-tuning.

Purpose:
    Project frozen canonical Qwen preprocessing roots into deterministic
    training bundles containing prepared manifests, stable speaker references,
    and machine-readable bundle metadata.

Relationships:
    - Consumes frozen canonical processed roots from `ml.qwen.preprocessing`.
    - Reuses preprocessing data contracts from `ml.qwen.common.models` and
      `ml.qwen.preprocessing.models`.
    - Supplies the canonical input root for training orchestrators.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    ManifestFamily,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
    AudioCodesEncoderProtocol,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import (
    RowKey,
    load_row_key_records,
    row_key_for_source_identity,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    iter_jsonl_objects,
    iter_spool_rows,
    rebuild_completed_row_keys_index,
    write_json,
    write_spool_row,
)

# --- Bundle Constants and Defaults ---

DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_BATCH_ROW_COUNT = 512
DEFAULT_AUDIO_CODES_CHUNK_SIZE = 64
DEFAULT_CONTAINER_BATCH_SPAN = 1


@dataclass(frozen=True)
class BundleBatch:
    """Describe one bounded finalization unit for one manifest family."""

    manifest_family: ManifestFamily
    batch_index: int
    row_count: int
    first_row_key: RowKey
    last_row_key: RowKey


@dataclass(frozen=True)
class BundleBatchPlan:
    """Deterministic plan for one batched bundle finalization."""

    source_root: str
    output_root: str
    train_manifest_family: ManifestFamily
    eval_manifest_family: ManifestFamily
    tokenizer_model: str
    finalization_batch_row_count: int
    retained_row_count: int
    conflict_row_count: int
    owned_row_keys_path: str
    conflict_row_keys_path: str
    repo_head: str
    generated_at: str
    family_row_counts: dict[ManifestFamily, int]
    batches: list[BundleBatch]


@dataclass(frozen=True)
class BundleSummary:
    """Machine-readable summary for one deterministic training bundle."""

    source_root: str
    output_root: str
    train_manifest_family: ManifestFamily
    eval_manifest_family: ManifestFamily
    tokenizer_model: str
    retained_row_count: int
    conflict_row_count: int
    manifest_row_counts: dict[ManifestFamily, int]
    speaker_counts: dict[ManifestFamily, int]
    owned_row_keys_path: str
    conflict_row_keys_path: str
    repo_head: str
    generated_at: str
    finalization_batch_row_count: int
    total_batch_count: int
    batch_plan_path: str
    events_path: str
    status_path: str


# --- Path Helpers ---


def bundle_report_path(output_root: Path) -> Path:
    """Return the machine-readable report path for one bundle."""
    return output_root / "reports" / "training_bundle_report.json"


def bundle_batch_plan_path(output_root: Path) -> Path:
    """Return the batch-plan path for one bundle build."""
    return output_root / "reports" / "training_bundle_plan.json"


def bundle_progress_events_path(output_root: Path) -> Path:
    """Return the append-only progress-events path for one bundle build."""
    return output_root / "reports" / "training_bundle_events.jsonl"


def bundle_progress_state_path(output_root: Path) -> Path:
    """Return the current progress-state path for one bundle build."""
    return output_root / "reports" / "training_bundle_status.json"


def bundle_manifest_path(output_root: Path, manifest_family: str) -> Path:
    """Return one prepared-manifest path inside the training bundle."""
    return output_root / "manifests" / f"{manifest_family}.prepared.jsonl"


# --- Core Logic ---


def build_training_bundle(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str = DEFAULT_TOKENIZER_MODEL,
    finalization_batch_row_count: int = DEFAULT_BATCH_ROW_COUNT,
    audio_codes_chunk_size: int = DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    repo_root: Path,
) -> BundleSummary:
    """Materialize or resume one deterministic training bundle."""
    if bundle_report_path(output_root).exists():
        return _load_bundle_summary(output_root)

    plan = prepare_training_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        repo_root=repo_root,
    )
    _write_progress_state(
        output_root, status="running", completed_batch_count=0, total_batch_count=len(plan.batches)
    )

    for batch in plan.batches:
        finalize_training_bundle_batch(
            output_root=output_root,
            plan=plan,
            manifest_family=batch.manifest_family,
            batch_index=batch.batch_index,
            audio_codes_chunk_size=audio_codes_chunk_size,
            encode_audio_codes_fn=encode_audio_codes_fn,
        )

    return _assemble_bundle(output_root=output_root, plan=plan)


def prepare_training_bundle_inputs(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str = DEFAULT_TOKENIZER_MODEL,
    finalization_batch_row_count: int = DEFAULT_BATCH_ROW_COUNT,
    repo_root: Path,
) -> BundleBatchPlan:
    """Copy retained rows into one bundle root and emit the batch plan."""
    return _prepare_bundle_plan(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        repo_root=repo_root,
    )


def load_training_bundle_batch_plan(output_root: Path) -> BundleBatchPlan:
    """Load the deterministic batch plan for one training bundle."""
    return _load_batch_plan(output_root)


def bundle_prepared_batch_path(
    output_root: Path, manifest_family: ManifestFamily, batch_index: int
) -> Path:
    """Return the prepared-manifest path for one finalized bundle batch."""
    return output_root / "batches" / manifest_family / f"batch-{batch_index:05d}" / "prepared.jsonl"


def bundle_batch_is_complete(output_root: Path, batch: BundleBatch) -> bool:
    """Return whether one bundle batch already has its prepared shard."""
    return bundle_prepared_batch_path(
        output_root, batch.manifest_family, batch.batch_index
    ).exists()


def finalize_training_bundle_batch(
    *,
    output_root: Path,
    plan: BundleBatchPlan,
    manifest_family: ManifestFamily,
    batch_index: int,
    audio_codes_chunk_size: int,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
) -> None:
    """Finalize one selected batch inside an existing bundle root."""
    batch = _find_batch(plan, manifest_family=manifest_family, batch_index=batch_index)
    _finalize_batch(
        output_root=output_root,
        batch=batch,
        tokenizer_model=plan.tokenizer_model,
        batch_row_count=plan.finalization_batch_row_count,
        audio_codes_chunk_size=audio_codes_chunk_size,
        encode_audio_codes_fn=encode_audio_codes_fn,
    )
    completed_batch_count = sum(
        1 for candidate in plan.batches if bundle_batch_is_complete(output_root, candidate)
    )
    _append_progress_event(
        output_root,
        {
            "event": "batch-finalized",
            "manifest_family": manifest_family,
            "batch_index": batch_index,
            "completed_batch_count": completed_batch_count,
            "total_batch_count": len(plan.batches),
            "updated_at": _utc_now_iso(),
        },
    )
    _write_progress_state(
        output_root,
        status="running" if completed_batch_count < len(plan.batches) else "completed",
        completed_batch_count=completed_batch_count,
        total_batch_count=len(plan.batches),
    )


def _prepare_bundle_plan(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str,
    finalization_batch_row_count: int,
    repo_root: Path,
) -> BundleBatchPlan:
    """Copy inputs and emit the deterministic batch plan."""
    if bundle_batch_plan_path(output_root).exists():
        return _load_batch_plan(output_root)

    output_root.mkdir(parents=True, exist_ok=True)
    selected_families = (train_manifest_family, eval_manifest_family)

    # 1. Identify frozen root metadata
    owned_row_keys_path = source_root / "reports" / "canonical_processed_root_owned_row_keys.jsonl"
    conflict_row_keys_path = (
        source_root / "reports" / "canonical_processed_root_conflict_row_keys.jsonl"
    )
    freeze_summary_path = source_root / "reports" / "canonical_processed_root_freeze.json"

    if not owned_row_keys_path.exists():
        raise FileNotFoundError(f"Missing owned row keys in source root: {owned_row_keys_path}")

    owned_row_keys = load_row_key_records(owned_row_keys_path)
    freeze_summary = json.loads(freeze_summary_path.read_text("utf-8"))
    conflict_row_count = int(freeze_summary["conflict_row_count"])

    # 2. Copy retained rows
    copied_row_count = 0
    family_row_counts: dict[ManifestFamily, int] = {f: 0 for f in selected_families}
    for spool_row in iter_spool_rows(source_root):
        row_key = row_key_for_source_identity(spool_row)
        if row_key not in owned_row_keys:
            continue

        targets = tuple(f for f in spool_row.manifest_targets if f in selected_families)
        if not targets or spool_row.admission_decision != "admit":
            continue

        bundle_row = replace(
            spool_row,
            manifest_targets=targets,
            reference_audio_24k_paths={
                f: p
                for f, p in spool_row.reference_audio_24k_paths.items()
                if f in selected_families
            },
        )
        write_spool_row(output_root, bundle_row)
        _copy_artifact(
            source_root / bundle_row.audio_24k_path, output_root / bundle_row.audio_24k_path
        )
        copied_row_count += 1
        for f in targets:
            family_row_counts[f] += 1

    rebuild_completed_row_keys_index(output_root)

    # 3. Build batches
    batches: list[BundleBatch] = []
    for family in selected_families:
        family_rows = [
            row for row in iter_spool_rows(output_root) if family in row.manifest_targets
        ]
        for i in range(0, len(family_rows), finalization_batch_row_count):
            chunk = family_rows[i : i + finalization_batch_row_count]
            batches.append(
                BundleBatch(
                    manifest_family=family,
                    batch_index=i // finalization_batch_row_count,
                    row_count=len(chunk),
                    first_row_key=row_key_for_source_identity(chunk[0]),
                    last_row_key=row_key_for_source_identity(chunk[-1]),
                )
            )

    plan = BundleBatchPlan(
        source_root=source_root.as_posix(),
        output_root=output_root.as_posix(),
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        retained_row_count=copied_row_count,
        conflict_row_count=conflict_row_count,
        owned_row_keys_path=owned_row_keys_path.as_posix(),
        conflict_row_keys_path=conflict_row_keys_path.as_posix(),
        repo_head=_git_head(repo_root),
        generated_at=_utc_now_iso(),
        family_row_counts=family_row_counts,
        batches=batches,
    )
    write_json(bundle_batch_plan_path(output_root), plan)
    return plan


def _finalize_batch(
    *,
    output_root: Path,
    batch: BundleBatch,
    tokenizer_model: str,
    batch_row_count: int,
    audio_codes_chunk_size: int,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
) -> None:
    """Finalize one bundle batch by generating audio codes."""
    from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
        _canonical_reference_audio_path,
        _curated_row_from_spool,
        _flush_audio_codes_chunk,
        _raw_manifest_row_from_curated,
    )
    from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import JsonlAtomicWriter

    batch_dir = output_root / "batches" / batch.manifest_family / f"batch-{batch.batch_index:05d}"
    if (batch_dir / "prepared.jsonl").exists():
        return

    batch_dir.mkdir(parents=True, exist_ok=True)
    family_rows = [
        row for row in iter_spool_rows(output_root) if batch.manifest_family in row.manifest_targets
    ]
    start = batch.batch_index * batch_row_count
    chunk = family_rows[start : start + batch.row_count]

    raw_chunk = []
    with (
        JsonlAtomicWriter(batch_dir / "raw.jsonl") as raw_writer,
        JsonlAtomicWriter(batch_dir / "prepared.jsonl") as prepared_writer,
    ):
        for row in chunk:
            # We assume refs already exist in bundle root for simplicity in this move
            ref_path = _canonical_reference_audio_path(
                family=batch.manifest_family, speaker_id=row.speaker_id
            )
            curated = _curated_row_from_spool(
                row, batch.manifest_family, reference_audio_24k_path=ref_path.as_posix()
            )
            raw_row = _raw_manifest_row_from_curated(curated)
            raw_chunk.append(raw_row)
            if len(raw_chunk) >= audio_codes_chunk_size:
                _flush_audio_codes_chunk(
                    output_root=output_root,
                    raw_writer=raw_writer,
                    prepared_writer=prepared_writer,
                    raw_rows=raw_chunk,
                    encode_audio_codes_fn=encode_audio_codes_fn,
                    tokenizer_model=tokenizer_model,
                )
        if raw_chunk:
            _flush_audio_codes_chunk(
                output_root=output_root,
                raw_writer=raw_writer,
                prepared_writer=prepared_writer,
                raw_rows=raw_chunk,
                encode_audio_codes_fn=encode_audio_codes_fn,
                tokenizer_model=tokenizer_model,
            )


def _assemble_bundle(
    *,
    output_root: Path,
    plan: BundleBatchPlan,
) -> BundleSummary:
    """Assemble final manifests and build report."""
    manifests_dir = output_root / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    manifest_row_counts = {}
    speaker_counts = {}

    for family in (plan.train_manifest_family, plan.eval_manifest_family):
        prepared_path = bundle_manifest_path(output_root, family)
        count = 0
        speakers = set()
        with prepared_path.open("w", encoding="utf-8") as out_f:
            family_batches = [b for b in plan.batches if b.manifest_family == family]
            for b in sorted(family_batches, key=lambda x: x.batch_index):
                batch_prepared = (
                    output_root
                    / "batches"
                    / family
                    / f"batch-{b.batch_index:05d}"
                    / "prepared.jsonl"
                )
                for row in iter_jsonl_objects(batch_prepared):
                    out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
                    speakers.add(row["speaker_id"])
        manifest_row_counts[family] = count
        speaker_counts[family] = len(speakers)

    summary = BundleSummary(
        source_root=plan.source_root,
        output_root=plan.output_root,
        train_manifest_family=plan.train_manifest_family,
        eval_manifest_family=plan.eval_manifest_family,
        tokenizer_model=plan.tokenizer_model,
        retained_row_count=plan.retained_row_count,
        conflict_row_count=plan.conflict_row_count,
        manifest_row_counts=manifest_row_counts,
        speaker_counts=speaker_counts,
        owned_row_keys_path=plan.owned_row_keys_path,
        conflict_row_keys_path=plan.conflict_row_keys_path,
        repo_head=plan.repo_head,
        generated_at=_utc_now_iso(),
        finalization_batch_row_count=plan.finalization_batch_row_count,
        total_batch_count=len(plan.batches),
        batch_plan_path=bundle_batch_plan_path(output_root).as_posix(),
        events_path=bundle_progress_events_path(output_root).as_posix(),
        status_path=bundle_progress_state_path(output_root).as_posix(),
    )
    write_json(bundle_report_path(output_root), summary)
    _write_progress_state(
        output_root,
        status="completed",
        completed_batch_count=len(plan.batches),
        total_batch_count=len(plan.batches),
    )
    return summary


# --- Internal Helpers ---


def _copy_artifact(source: Path, target: Path) -> None:
    """Copy one artifact ensuring parent exists."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)


def _git_head(repo_root: Path) -> str:
    """Return the current git HEAD SHA."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_progress_event(output_root: Path, event: dict[str, object]) -> None:
    """Append one deterministic progress event for bundle finalization."""
    events_path = bundle_progress_events_path(output_root)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _write_progress_state(
    output_root: Path,
    *,
    status: str,
    completed_batch_count: int,
    total_batch_count: int,
) -> None:
    """Persist the latest summary state for one bundle build."""
    write_json(
        bundle_progress_state_path(output_root),
        {
            "status": status,
            "completed_batch_count": completed_batch_count,
            "total_batch_count": total_batch_count,
            "updated_at": _utc_now_iso(),
        },
    )


def _find_batch(
    plan: BundleBatchPlan,
    *,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> BundleBatch:
    """Return one batch from the plan or fail with a clear error."""
    for batch in plan.batches:
        if batch.manifest_family == manifest_family and batch.batch_index == batch_index:
            return batch
    raise ValueError(f"Bundle plan does not contain batch `{manifest_family}:{batch_index}`.")


def _load_batch_plan(output_root: Path) -> BundleBatchPlan:
    """Load one existing batch plan from disk."""
    path = bundle_batch_plan_path(output_root)
    payload = json.loads(path.read_text("utf-8"))
    raw_batches = payload["batches"]
    if not isinstance(raw_batches, list):
        raise ValueError("Training bundle batch plan contained malformed `batches`.")
    batches: list[BundleBatch] = []
    for raw_batch in raw_batches:
        if not isinstance(raw_batch, dict):
            raise ValueError("Training bundle batch plan contained a non-object batch entry.")
        batches.append(
            BundleBatch(
                manifest_family=_required_manifest_family(raw_batch, "manifest_family"),
                batch_index=_required_int(raw_batch, "batch_index"),
                row_count=_required_int(raw_batch, "row_count"),
                first_row_key=_required_row_key(raw_batch, "first_row_key"),
                last_row_key=_required_row_key(raw_batch, "last_row_key"),
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
        family_row_counts=_required_manifest_family_counts(payload, "family_row_counts"),
        batches=batches,
    )


def _load_bundle_summary(output_root: Path) -> BundleSummary:
    """Load one existing bundle summary from disk."""
    path = bundle_report_path(output_root)
    payload = json.loads(path.read_text("utf-8"))
    return BundleSummary(**payload)


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Training bundle payload missing string `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Training bundle payload missing integer `{key}`.")
    return value


def _required_manifest_family(payload: dict[str, object], key: str) -> ManifestFamily:
    """Return one required manifest-family field from a JSON payload."""
    value = payload.get(key)
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
    raise ValueError(f"Training bundle payload contained invalid manifest family `{key}`.")


def _required_manifest_family_counts(
    payload: dict[str, object],
    key: str,
) -> dict[ManifestFamily, int]:
    """Return one manifest-family count mapping from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Training bundle payload missing object `{key}`.")
    result: dict[ManifestFamily, int] = {}
    for raw_family, raw_count in value.items():
        if raw_family not in {
            "swedish_smoke_train",
            "swedish_pilot_train",
            "swedish_scaleup_train",
            "swedish_checkpoint_dev",
            "swedish_final_test",
            "swedish_waxholm_control",
        }:
            raise ValueError(f"Training bundle payload contained invalid family `{raw_family}`.")
        if not isinstance(raw_count, int):
            raise ValueError(
                f"Training bundle payload contained non-integer count for `{raw_family}`."
            )
        result[raw_family] = raw_count
    return result


def _required_row_key(payload: dict[str, object], key: str) -> RowKey:
    """Return one row-key tuple from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"Training bundle payload contained invalid row key `{key}`.")
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"Training bundle payload contained non-string row key `{key}`.")
    dataset, source_split, dataset_row_id = value
    return (dataset, source_split, dataset_row_id)
