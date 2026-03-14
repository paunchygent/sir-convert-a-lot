"""Training-bundle orchestration for Qwen fine-tuning.

Purpose:
    Own the canonical public bundle-materialization workflow that projects a
    frozen preprocessing root into a deterministic training bundle with stable
    manifests, canonical reference assets, and persisted precomputed reference
    inputs.

Relationships:
    - Consumes frozen canonical processed roots from `ml.qwen.preprocessing`.
    - Reuses bundle data contracts from `ml.qwen.training.bundle_contracts`.
    - Delegates state parsing/persistence and precomputed ref-input handling to
      focused helper modules in the same training package.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import AudioCodesEncoderProtocol
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import SpoolRow
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import (
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
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_contracts import (
    BundleBatch,
    BundleBatchPlan,
    BundleSummary,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_precomputed_ref_inputs import (
    load_precomputed_reference_input_summary,
    materialize_precomputed_reference_inputs,
    precomputed_ref_input_relative_path,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_state import (
    append_progress_event,
    find_batch,
    git_head,
    load_batch_plan,
    load_bundle_summary,
    utc_now_iso,
    write_progress_state,
)

DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_BATCH_ROW_COUNT = 512
DEFAULT_AUDIO_CODES_CHUNK_SIZE = 64
DEFAULT_CONTAINER_BATCH_SPAN = 1


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


def bundle_prepared_batch_path(
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> Path:
    """Return the prepared-manifest path for one finalized bundle batch."""
    return output_root / "batches" / manifest_family / f"batch-{batch_index:05d}" / "prepared.jsonl"


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
        return load_training_bundle_summary(output_root)

    plan = prepare_training_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        repo_root=repo_root,
    )
    write_progress_state(
        output_root,
        status_path=bundle_progress_state_path(output_root),
        status="running",
        completed_batch_count=0,
        total_batch_count=len(plan.batches),
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


def assemble_training_bundle(output_root: Path) -> BundleSummary:
    """Assemble one existing bundle root into final manifests and summary metadata."""
    plan = load_training_bundle_batch_plan(output_root)
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
    return load_batch_plan(bundle_batch_plan_path(output_root))


def load_training_bundle_summary(output_root: Path) -> BundleSummary:
    """Load the deterministic bundle summary for one training bundle."""
    return load_bundle_summary(bundle_report_path(output_root))


def load_optional_training_bundle_summary(output_root: Path) -> BundleSummary | None:
    """Load the bundle summary when the canonical report exists for one bundle."""
    report_path = bundle_report_path(output_root)
    if not report_path.exists():
        return None
    return load_bundle_summary(report_path)


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
    batch = find_batch(plan, manifest_family=manifest_family, batch_index=batch_index)
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
    append_progress_event(
        output_root,
        events_path=bundle_progress_events_path(output_root),
        event={
            "event": "batch-finalized",
            "manifest_family": manifest_family,
            "batch_index": batch_index,
            "completed_batch_count": completed_batch_count,
            "total_batch_count": len(plan.batches),
            "updated_at": utc_now_iso(),
        },
    )
    write_progress_state(
        output_root,
        status_path=bundle_progress_state_path(output_root),
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
    """Copy retained rows, canonical refs, and emit the deterministic batch plan."""
    plan_path = bundle_batch_plan_path(output_root)
    if plan_path.exists():
        return load_batch_plan(plan_path)

    output_root.mkdir(parents=True, exist_ok=True)
    selected_families = (train_manifest_family, eval_manifest_family)
    owned_row_keys_path = source_root / "reports" / "canonical_processed_root_owned_row_keys.jsonl"
    conflict_row_keys_path = (
        source_root / "reports" / "canonical_processed_root_conflict_row_keys.jsonl"
    )
    freeze_summary_path = source_root / "reports" / "canonical_processed_root_freeze.json"
    if not owned_row_keys_path.exists():
        raise FileNotFoundError(f"Missing owned row keys in source root: {owned_row_keys_path}")

    owned_row_keys = load_row_key_records(owned_row_keys_path)
    freeze_summary = json.loads(freeze_summary_path.read_text(encoding="utf-8"))
    if not isinstance(freeze_summary, dict):
        raise ValueError("Canonical processed-root freeze summary was malformed.")
    conflict_row_count = int(freeze_summary["conflict_row_count"])

    copied_row_count = 0
    family_row_counts: dict[ManifestFamily, int] = {family: 0 for family in selected_families}
    for spool_row in iter_spool_rows(source_root):
        row_key = row_key_for_source_identity(spool_row)
        if row_key not in owned_row_keys:
            continue
        targets = tuple(
            family for family in spool_row.manifest_targets if family in selected_families
        )
        if not targets or spool_row.admission_decision != "admit":
            continue
        canonical_reference_paths = {
            family: _canonical_reference_audio_path(
                family=family, speaker_id=spool_row.speaker_id
            ).as_posix()
            for family in targets
        }
        bundle_row = replace(
            spool_row,
            manifest_targets=targets,
            reference_audio_24k_paths=canonical_reference_paths,
        )
        write_spool_row(output_root, bundle_row)
        _copy_artifact(
            source_root / spool_row.audio_24k_path, output_root / bundle_row.audio_24k_path
        )
        for family in targets:
            _copy_artifact(
                _source_reference_audio_path(
                    source_root=source_root,
                    spool_row=spool_row,
                    family=family,
                ),
                output_root / canonical_reference_paths[family],
            )
            family_row_counts[family] += 1
        copied_row_count += 1

    rebuild_completed_row_keys_index(output_root)
    materialize_precomputed_reference_inputs(output_root, manifest_families=selected_families)

    batches: list[BundleBatch] = []
    for family in selected_families:
        family_rows = [
            row for row in iter_spool_rows(output_root) if family in row.manifest_targets
        ]
        for index in range(0, len(family_rows), finalization_batch_row_count):
            chunk = family_rows[index : index + finalization_batch_row_count]
            batches.append(
                BundleBatch(
                    manifest_family=family,
                    batch_index=index // finalization_batch_row_count,
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
        repo_head=git_head(repo_root),
        generated_at=utc_now_iso(),
        family_row_counts=family_row_counts,
        batches=batches,
    )
    write_json(plan_path, plan)
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
    """Finalize one bundle batch by generating audio codes and manifest rows."""
    from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
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
    precomputed_summary = load_precomputed_reference_input_summary(output_root)
    with (
        JsonlAtomicWriter(batch_dir / "raw.jsonl") as raw_writer,
        JsonlAtomicWriter(batch_dir / "prepared.jsonl") as prepared_writer,
    ):
        for row in chunk:
            ref_audio_path = row.reference_audio_24k_paths[batch.manifest_family]
            curated = _curated_row_from_spool(
                row,
                batch.manifest_family,
                reference_audio_24k_path=ref_audio_path,
            )
            raw_row = _raw_manifest_row_from_curated(curated)
            raw_row["precomputed_ref_input_path"] = precomputed_ref_input_relative_path(
                manifest_family=batch.manifest_family,
                speaker_id=row.speaker_id,
            ).as_posix()
            raw_row["precomputed_ref_input_kind"] = precomputed_summary.kind
            raw_row["precomputed_ref_input_version"] = precomputed_summary.version
            raw_row["precomputed_ref_input_source_audio"] = ref_audio_path
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


def _assemble_bundle(*, output_root: Path, plan: BundleBatchPlan) -> BundleSummary:
    """Assemble final manifests and persist the bundle report."""
    manifests_dir = output_root / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    manifest_row_counts: dict[ManifestFamily, int] = {}
    speaker_counts: dict[ManifestFamily, int] = {}
    for family in (plan.train_manifest_family, plan.eval_manifest_family):
        prepared_path = bundle_manifest_path(output_root, family)
        speaker_ids: set[str] = set()
        row_count = 0
        with prepared_path.open("w", encoding="utf-8") as handle:
            family_batches = [batch for batch in plan.batches if batch.manifest_family == family]
            for batch in sorted(family_batches, key=lambda candidate: candidate.batch_index):
                batch_prepared_path = bundle_prepared_batch_path(
                    output_root, family, batch.batch_index
                )
                for row in iter_jsonl_objects(batch_prepared_path):
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    row_count += 1
                    speaker_ids.add(str(row["speaker_id"]))
        manifest_row_counts[family] = row_count
        speaker_counts[family] = len(speaker_ids)

    precomputed_summary = load_precomputed_reference_input_summary(output_root)
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
        generated_at=utc_now_iso(),
        finalization_batch_row_count=plan.finalization_batch_row_count,
        total_batch_count=len(plan.batches),
        batch_plan_path=bundle_batch_plan_path(output_root).as_posix(),
        events_path=bundle_progress_events_path(output_root).as_posix(),
        status_path=bundle_progress_state_path(output_root).as_posix(),
        precomputed_reference_input=precomputed_summary,
    )
    write_json(bundle_report_path(output_root), summary)
    write_progress_state(
        output_root,
        status_path=bundle_progress_state_path(output_root),
        status="completed",
        completed_batch_count=len(plan.batches),
        total_batch_count=len(plan.batches),
    )
    return summary


def _copy_artifact(source: Path, target: Path) -> None:
    """Copy one bundle-owned artifact ensuring parent directories exist."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)


def _source_reference_audio_path(
    *,
    source_root: Path,
    spool_row: SpoolRow,
    family: ManifestFamily,
) -> Path:
    """Resolve the source reference clip for one family, falling back to row audio when absent."""
    relative_path = spool_row.reference_audio_24k_paths.get(family)
    if isinstance(relative_path, str):
        return source_root / relative_path
    return source_root / spool_row.audio_24k_path


def _canonical_reference_audio_path(*, family: ManifestFamily, speaker_id: str) -> Path:
    """Return the canonical relative reference-audio path for one family speaker."""
    return Path("refs", family, speaker_id, "ref.wav")
