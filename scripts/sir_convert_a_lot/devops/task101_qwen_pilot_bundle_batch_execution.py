"""Execution helpers for Task 101 batch finalization and assembly.

Purpose:
    Materialize stable reference audio, finalize one bounded Task 101 batch
    into curated/raw/prepared shards, validate reusable shard sets, and
    assemble final manifests from validated shards.

Relationships:
    - Consumed by `task101_qwen_pilot_bundle.py` and the direct
      `finalize-batch` command.
    - Depends on the Task 101 batch-plan contracts and progress helpers.
    - Reuses Task 103 row/finalization contracts without reusing Task 103's
      whole-family finalization loop.
"""

from __future__ import annotations

import gc
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    Task101PilotBundleBatch,
    Task101PilotBundleBatchPlan,
    render_task101_spool_row_key,
    selected_manifest_families,
    task101_pilot_bundle_batch_id,
    task101_pilot_bundle_curated_batch_path,
    task101_pilot_bundle_prepared_batch_path,
    task101_pilot_bundle_raw_batch_path,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_progress import (
    record_task101_pilot_bundle_progress_event,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    Task101PilotBundleRuntimeFingerprint,
    load_task101_pilot_bundle_runtime_fingerprint,
    task101_pilot_bundle_batch_runtime_path,
    validate_runtime_fingerprint_matches,
    write_task101_pilot_bundle_batch_runtime_fingerprint,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    AudioCodesEncoderProtocol,
    reset_audio_codes_encoder_after_failure,
    take_audio_codes_chunk_timing_for_encoder,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    CuratedRow,
    ManifestFamily,
    PreparedManifestRow,
    RawManifestRow,
    SpoolRow,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    JsonlAtomicWriter,
    iter_jsonl_objects,
    iter_spool_rows,
)

Task101BatchRowSignature = tuple[str, str, str, str, str, str, str]


@dataclass(frozen=True)
class Task101AudioCodesChunkSummary:
    """Timing summary for one Task 101 audio-code flush chunk."""

    leaf_chunk_count: int
    chunk_row_count: int
    min_effective_chunk_row_count: int | None
    max_effective_chunk_row_count: int | None
    encode_call_seconds: float
    preload_seconds: float | None
    feature_extract_seconds: float | None
    model_encode_seconds: float | None
    render_seconds: float | None
    oom_retry_count: int
    oom_retry_seconds: float
    write_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class Task101AudioCodesBatchSummary:
    """Aggregate timing summary for one Task 101 finalized batch."""

    chunk_count: int
    encoded_row_count: int
    min_effective_chunk_row_count: int | None
    max_effective_chunk_row_count: int | None
    encode_call_seconds: float
    preload_seconds: float | None
    feature_extract_seconds: float | None
    model_encode_seconds: float | None
    render_seconds: float | None
    oom_retry_count: int
    oom_retry_seconds: float
    write_seconds: float
    chunk_total_seconds: float
    batch_total_seconds: float
    non_audio_codes_seconds: float


def ensure_reference_audio_paths(
    output_root: Path,
    families: tuple[ManifestFamily, ...],
) -> dict[tuple[ManifestFamily, str], str]:
    """Ensure one deterministic `refs/` clip exists per selected family speaker."""
    selected_families = set(families)
    reference_audio_paths: dict[tuple[ManifestFamily, str], str] = {}
    for spool_row in iter_spool_rows(output_root):
        source_audio_path = output_root / spool_row.audio_24k_path
        for family in spool_row.manifest_targets:
            if family not in selected_families:
                continue
            speaker_key = (family, spool_row.speaker_id)
            if speaker_key in reference_audio_paths:
                continue
            relative_reference_path = Path("refs", family, spool_row.speaker_id, "ref.wav")
            absolute_reference_path = output_root / relative_reference_path
            absolute_reference_path.parent.mkdir(parents=True, exist_ok=True)
            if not absolute_reference_path.exists():
                shutil.copyfile(source_audio_path, absolute_reference_path)
            reference_audio_paths[speaker_key] = relative_reference_path.as_posix()
    return reference_audio_paths


def resolve_task101_pilot_bundle_batch(
    plan: Task101PilotBundleBatchPlan,
    *,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> Task101PilotBundleBatch:
    """Resolve one batch by family/index from the current plan."""
    for batch in plan.batches:
        if batch.manifest_family == manifest_family and batch.batch_index == batch_index:
            return batch
    raise ValueError(
        "Task 101 pilot bundle batch plan does not include "
        f"`{manifest_family}` batch `{batch_index}`."
    )


def finalize_task101_pilot_bundle_batch(
    *,
    output_root: Path,
    plan: Task101PilotBundleBatchPlan,
    manifest_family: ManifestFamily,
    batch_index: int,
    audio_codes_chunk_size: int,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    runtime_fingerprint: Task101PilotBundleRuntimeFingerprint | None = None,
) -> Task101PilotBundleBatch:
    """Finalize one bounded Task 101 family batch into deterministic shards."""
    if audio_codes_chunk_size <= 0:
        raise ValueError("`audio_codes_chunk_size` must be positive.")
    batch_started_at = time.perf_counter()
    batch = resolve_task101_pilot_bundle_batch(
        plan,
        manifest_family=manifest_family,
        batch_index=batch_index,
    )
    if task101_pilot_bundle_batch_is_complete(
        output_root,
        batch,
        expected_runtime_fingerprint=runtime_fingerprint,
    ):
        record_task101_pilot_bundle_progress_event(
            output_root=output_root,
            plan=plan,
            event="batch_skipped_existing",
            batch=batch,
            detail="validated_batch_shard_exists",
        )
        return batch
    record_task101_pilot_bundle_progress_event(
        output_root=output_root,
        plan=plan,
        event="batch_started",
        batch=batch,
        detail=f"audio_codes_chunk_size={audio_codes_chunk_size}",
    )
    reference_audio_paths = ensure_reference_audio_paths(output_root, (manifest_family,))
    target_rows = _spool_rows_for_batch(output_root, batch)
    curated_path = task101_pilot_bundle_curated_batch_path(
        output_root,
        manifest_family,
        batch_index,
    )
    raw_path = task101_pilot_bundle_raw_batch_path(output_root, manifest_family, batch_index)
    prepared_path = task101_pilot_bundle_prepared_batch_path(
        output_root,
        manifest_family,
        batch_index,
    )
    raw_chunk: list[RawManifestRow] = []
    chunk_summaries: list[Task101AudioCodesChunkSummary] = []
    with (
        JsonlAtomicWriter(curated_path) as curated_writer,
        JsonlAtomicWriter(raw_path) as raw_writer,
        JsonlAtomicWriter(prepared_path) as prepared_writer,
    ):
        for spool_row in target_rows:
            curated_row = _curated_row_from_spool(
                spool_row,
                manifest_family,
                reference_audio_24k_path=reference_audio_paths[
                    (manifest_family, spool_row.speaker_id)
                ],
            )
            curated_writer.write_row(curated_row)
            raw_chunk.append(_raw_manifest_row_from_curated(curated_row))
            if len(raw_chunk) >= audio_codes_chunk_size:
                chunk_summaries.append(
                    _flush_audio_codes_chunk(
                        output_root=output_root,
                        raw_writer=raw_writer,
                        prepared_writer=prepared_writer,
                        raw_rows=raw_chunk,
                        encode_audio_codes_fn=encode_audio_codes_fn,
                        tokenizer_model=plan.tokenizer_model,
                    )
                )
        if raw_chunk:
            chunk_summaries.append(
                _flush_audio_codes_chunk(
                    output_root=output_root,
                    raw_writer=raw_writer,
                    prepared_writer=prepared_writer,
                    raw_rows=raw_chunk,
                    encode_audio_codes_fn=encode_audio_codes_fn,
                    tokenizer_model=plan.tokenizer_model,
                )
            )
    batch_timing_summary = _summarize_audio_codes_batch_timings(
        chunk_summaries,
        batch_total_seconds=time.perf_counter() - batch_started_at,
    )
    validate_task101_pilot_bundle_batch_outputs(output_root, batch)
    if runtime_fingerprint is not None:
        write_task101_pilot_bundle_batch_runtime_fingerprint(
            output_root,
            manifest_family,
            batch_index,
            runtime_fingerprint,
        )
    record_task101_pilot_bundle_progress_event(
        output_root=output_root,
        plan=plan,
        event="batch_completed",
        batch=batch,
        detail=f"prepared_row_count={batch.row_count}",
        extra_fields=_batch_timing_summary_payload(batch_timing_summary),
    )
    return batch


def task101_pilot_bundle_batch_is_complete(
    output_root: Path,
    batch: Task101PilotBundleBatch,
    *,
    expected_runtime_fingerprint: Task101PilotBundleRuntimeFingerprint | None = None,
) -> bool:
    """Return whether one batch shard set is valid and ready to reuse."""
    try:
        validate_task101_pilot_bundle_batch_outputs(
            output_root,
            batch,
            expected_runtime_fingerprint=expected_runtime_fingerprint,
        )
    except (FileNotFoundError, ValueError):
        return False
    return True


def validate_task101_pilot_bundle_batch_outputs(
    output_root: Path,
    batch: Task101PilotBundleBatch,
    *,
    expected_runtime_fingerprint: Task101PilotBundleRuntimeFingerprint | None = None,
) -> None:
    """Validate one batch shard set before reuse or final assembly."""
    curated_rows = list(
        iter_jsonl_objects(
            task101_pilot_bundle_curated_batch_path(
                output_root,
                batch.manifest_family,
                batch.batch_index,
            )
        )
    )
    raw_rows = list(
        iter_jsonl_objects(
            task101_pilot_bundle_raw_batch_path(
                output_root,
                batch.manifest_family,
                batch.batch_index,
            )
        )
    )
    prepared_rows = list(
        iter_jsonl_objects(
            task101_pilot_bundle_prepared_batch_path(
                output_root,
                batch.manifest_family,
                batch.batch_index,
            )
        )
    )
    if len(curated_rows) != batch.row_count:
        raise ValueError(
            "Task 101 batch curated shard count mismatch for "
            f"{task101_pilot_bundle_batch_id(batch)}."
        )
    if len(raw_rows) != batch.row_count:
        raise ValueError(
            f"Task 101 batch raw shard count mismatch for {task101_pilot_bundle_batch_id(batch)}."
        )
    if len(prepared_rows) != batch.row_count:
        raise ValueError(
            "Task 101 batch prepared shard count mismatch for "
            f"{task101_pilot_bundle_batch_id(batch)}."
        )
    if curated_rows:
        first_row_key = _render_curated_payload_row_key(curated_rows[0])
        last_row_key = _render_curated_payload_row_key(curated_rows[-1])
        if first_row_key != batch.first_row_key:
            raise ValueError(
                "Task 101 batch first-row drift detected for "
                f"{task101_pilot_bundle_batch_id(batch)}."
            )
        if last_row_key != batch.last_row_key:
            raise ValueError(
                "Task 101 batch last-row drift detected for "
                f"{task101_pilot_bundle_batch_id(batch)}."
            )
    curated_signatures = [_render_curated_payload_signature(payload) for payload in curated_rows]
    raw_signatures = [_render_manifest_payload_signature(payload) for payload in raw_rows]
    prepared_signatures = [_render_prepared_payload_signature(payload) for payload in prepared_rows]
    if raw_signatures != curated_signatures:
        raise ValueError(
            "Task 101 batch raw shard row drift detected for "
            f"{task101_pilot_bundle_batch_id(batch)}."
        )
    if prepared_signatures != curated_signatures:
        raise ValueError(
            "Task 101 batch prepared shard row drift detected for "
            f"{task101_pilot_bundle_batch_id(batch)}."
        )
    for prepared_row in prepared_rows:
        _validate_prepared_manifest_payload_paths(output_root, prepared_row)
    if expected_runtime_fingerprint is not None:
        observed_runtime_fingerprint = load_task101_pilot_bundle_runtime_fingerprint(
            task101_pilot_bundle_batch_runtime_path(
                output_root,
                batch.manifest_family,
                batch.batch_index,
            )
        )
        validate_runtime_fingerprint_matches(
            observed_runtime_fingerprint,
            expected_runtime_fingerprint,
        )


def assemble_task101_pilot_bundle_from_batches(
    *,
    output_root: Path,
    plan: Task101PilotBundleBatchPlan,
) -> None:
    """Assemble final curated/raw/prepared manifests from validated batch shards."""
    record_task101_pilot_bundle_progress_event(
        output_root=output_root,
        plan=plan,
        event="assemble_started",
        detail="assembling_validated_batch_shards",
    )
    for manifest_family in selected_manifest_families(plan):
        family_batches = [
            batch for batch in plan.batches if batch.manifest_family == manifest_family
        ]
        if not family_batches:
            raise ValueError(
                f"Task 101 pilot bundle batch plan is missing batches for `{manifest_family}`."
            )
        expected_row_count = plan.family_row_counts[manifest_family]
        curated_row_count = 0
        raw_row_count = 0
        prepared_row_count = 0
        with (
            JsonlAtomicWriter(
                output_root / "curated" / f"{manifest_family}.jsonl"
            ) as curated_writer,
            JsonlAtomicWriter(
                output_root / "manifests" / f"{manifest_family}.raw.jsonl"
            ) as raw_writer,
            JsonlAtomicWriter(
                output_root / "manifests" / f"{manifest_family}.prepared.jsonl"
            ) as prepared_writer,
        ):
            for batch in family_batches:
                validate_task101_pilot_bundle_batch_outputs(output_root, batch)
                for curated_row in iter_jsonl_objects(
                    task101_pilot_bundle_curated_batch_path(
                        output_root,
                        manifest_family,
                        batch.batch_index,
                    )
                ):
                    curated_writer.write_row(curated_row)
                    curated_row_count += 1
                for raw_row in iter_jsonl_objects(
                    task101_pilot_bundle_raw_batch_path(
                        output_root,
                        manifest_family,
                        batch.batch_index,
                    )
                ):
                    raw_writer.write_row(raw_row)
                    raw_row_count += 1
                for prepared_row in iter_jsonl_objects(
                    task101_pilot_bundle_prepared_batch_path(
                        output_root,
                        manifest_family,
                        batch.batch_index,
                    )
                ):
                    prepared_writer.write_row(prepared_row)
                    prepared_row_count += 1
        if curated_row_count != expected_row_count:
            raise ValueError(f"Task 101 curated assembly count mismatch for `{manifest_family}`.")
        if raw_row_count != expected_row_count:
            raise ValueError(f"Task 101 raw assembly count mismatch for `{manifest_family}`.")
        if prepared_row_count != expected_row_count:
            raise ValueError(f"Task 101 prepared assembly count mismatch for `{manifest_family}`.")
    record_task101_pilot_bundle_progress_event(
        output_root=output_root,
        plan=plan,
        event="assemble_completed",
        detail="final_manifests_ready",
    )


def _spool_rows_for_batch(output_root: Path, batch: Task101PilotBundleBatch) -> list[SpoolRow]:
    """Collect the spool rows that belong to one deterministic batch window."""
    rendered_rows: list[SpoolRow] = []
    current_family_index = 0
    for spool_row in iter_spool_rows(output_root):
        if batch.manifest_family not in spool_row.manifest_targets:
            continue
        if current_family_index >= batch.row_end_exclusive:
            break
        if current_family_index >= batch.row_start_index:
            rendered_rows.append(spool_row)
        current_family_index += 1
    if len(rendered_rows) != batch.row_count:
        raise ValueError(
            f"Task 101 batch row-count drift detected for {task101_pilot_bundle_batch_id(batch)}."
        )
    if rendered_rows and render_task101_spool_row_key(rendered_rows[0]) != batch.first_row_key:
        raise ValueError(
            f"Task 101 batch first-row mismatch for {task101_pilot_bundle_batch_id(batch)}."
        )
    if rendered_rows and render_task101_spool_row_key(rendered_rows[-1]) != batch.last_row_key:
        raise ValueError(
            f"Task 101 batch last-row mismatch for {task101_pilot_bundle_batch_id(batch)}."
        )
    return rendered_rows


def _render_curated_payload_row_key(payload: dict[str, object]) -> str:
    """Render one curated-row payload key for batch validation."""
    dataset = _required_string(payload, "dataset")
    source_split = _required_string(payload, "source_split")
    dataset_row_id = _required_string(payload, "dataset_row_id")
    return f"{dataset}/{source_split}/{dataset_row_id}"


def _render_curated_payload_signature(payload: dict[str, object]) -> Task101BatchRowSignature:
    """Render one comparable curated-row signature for shard validation."""
    return (
        _required_string(payload, "dataset"),
        _required_string(payload, "source_split"),
        _required_string(payload, "speaker_id"),
        _required_string(payload, "audio_24k_path"),
        _required_string(payload, "text_normalized"),
        _required_string(payload, "reference_audio_24k_path"),
        _required_string(payload, "quality_tier"),
    )


def _render_manifest_payload_signature(payload: dict[str, object]) -> Task101BatchRowSignature:
    """Render one comparable raw-manifest row signature for shard validation."""
    return (
        _required_string(payload, "dataset"),
        _required_string(payload, "source_split"),
        _required_string(payload, "speaker_id"),
        _required_string(payload, "audio"),
        _required_string(payload, "text"),
        _required_string(payload, "ref_audio"),
        _required_string(payload, "quality_tier"),
    )


def _render_prepared_payload_signature(payload: dict[str, object]) -> Task101BatchRowSignature:
    """Render one comparable prepared-manifest row signature for shard validation."""
    audio_codes = payload.get("audio_codes")
    if not isinstance(audio_codes, list):
        raise ValueError("Malformed `audio_codes` in prepared manifest payload.")
    return _render_manifest_payload_signature(payload)


def _curated_row_from_spool(
    spool_row: SpoolRow,
    manifest_target: ManifestFamily,
    *,
    reference_audio_24k_path: str,
) -> CuratedRow:
    """Project one retained spool row into one family-specific curated row."""
    return CuratedRow(
        dataset=spool_row.dataset,
        source_split=spool_row.source_split,
        dataset_row_id=spool_row.dataset_row_id,
        speaker_id=spool_row.speaker_id,
        speaker_name=spool_row.speaker_name,
        speaker_from_id=spool_row.speaker_from_id,
        source_audio_path=spool_row.source_audio_path,
        audio_24k_path=spool_row.audio_24k_path,
        duration_seconds=spool_row.duration_seconds,
        text_normalized=spool_row.text_normalized,
        reference_audio_24k_path=reference_audio_24k_path,
        asr_model=spool_row.asr_model,
        asr_revision=spool_row.asr_revision,
        asr_transcript=spool_row.asr_transcript,
        asr_wer=spool_row.asr_wer,
        quality_tier=spool_row.quality_tier,
        speaker_quality_gate=spool_row.speaker_quality_gate,
        dedup_applied=spool_row.dedup_applied,
        admission_decision=spool_row.admission_decision,
        manifest_target=manifest_target,
    )


def _raw_manifest_row_from_curated(curated_row: CuratedRow) -> RawManifestRow:
    """Project one curated row into one raw Qwen manifest row."""
    return RawManifestRow(
        audio=curated_row.audio_24k_path,
        text=curated_row.text_normalized,
        ref_audio=curated_row.reference_audio_24k_path,
        speaker_id=curated_row.speaker_id,
        dataset=curated_row.dataset,
        source_split=curated_row.source_split,
        quality_tier=curated_row.quality_tier,
    )


def _flush_audio_codes_chunk(
    *,
    output_root: Path,
    raw_writer: JsonlAtomicWriter,
    prepared_writer: JsonlAtomicWriter,
    raw_rows: list[RawManifestRow],
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    tokenizer_model: str,
) -> Task101AudioCodesChunkSummary:
    """Encode one bounded raw chunk and append batch-local raw/prepared rows."""
    if not raw_rows:
        return Task101AudioCodesChunkSummary(
            leaf_chunk_count=0,
            chunk_row_count=0,
            min_effective_chunk_row_count=None,
            max_effective_chunk_row_count=None,
            encode_call_seconds=0.0,
            preload_seconds=None,
            feature_extract_seconds=None,
            model_encode_seconds=None,
            render_seconds=None,
            oom_retry_count=0,
            oom_retry_seconds=0.0,
            write_seconds=0.0,
            total_seconds=0.0,
        )
    encode_started_at = time.perf_counter()
    try:
        return _encode_and_write_audio_codes_chunk(
            output_root=output_root,
            raw_writer=raw_writer,
            prepared_writer=prepared_writer,
            raw_rows=raw_rows,
            encode_audio_codes_fn=encode_audio_codes_fn,
            tokenizer_model=tokenizer_model,
        )
    except RuntimeError as exc:
        failed_attempt_seconds = time.perf_counter() - encode_started_at
        if not _is_audio_codes_out_of_memory_error(exc) or len(raw_rows) <= 1:
            raise
        reset_audio_codes_encoder_after_failure(encode_audio_codes_fn)
        _release_audio_codes_gpu_memory()
        split_index = max(1, len(raw_rows) // 2)
        leading_rows = list(raw_rows[:split_index])
        trailing_rows = list(raw_rows[split_index:])
        leading_summary = _flush_audio_codes_chunk(
            output_root=output_root,
            raw_writer=raw_writer,
            prepared_writer=prepared_writer,
            raw_rows=leading_rows,
            encode_audio_codes_fn=encode_audio_codes_fn,
            tokenizer_model=tokenizer_model,
        )
        trailing_summary = _flush_audio_codes_chunk(
            output_root=output_root,
            raw_writer=raw_writer,
            prepared_writer=prepared_writer,
            raw_rows=trailing_rows,
            encode_audio_codes_fn=encode_audio_codes_fn,
            tokenizer_model=tokenizer_model,
        )
        raw_rows.clear()
        return _combine_audio_codes_chunk_summaries(
            [leading_summary, trailing_summary],
            extra_oom_retry_count=1,
            extra_oom_retry_seconds=failed_attempt_seconds,
        )


def _encode_and_write_audio_codes_chunk(
    *,
    output_root: Path,
    raw_writer: JsonlAtomicWriter,
    prepared_writer: JsonlAtomicWriter,
    raw_rows: list[RawManifestRow],
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    tokenizer_model: str,
) -> Task101AudioCodesChunkSummary:
    """Encode and write one chunk when no recursive backoff is needed."""
    encode_started_at = time.perf_counter()
    audio_codes_list = encode_audio_codes_fn(
        tokenizer_model=tokenizer_model,
        audio_paths=[output_root / raw_row["audio"] for raw_row in raw_rows],
    )
    encode_call_seconds = time.perf_counter() - encode_started_at
    encoder_timing = take_audio_codes_chunk_timing_for_encoder(encode_audio_codes_fn)
    prepared_count = 0
    write_started_at = time.perf_counter()
    for raw_row, audio_codes in zip(raw_rows, audio_codes_list, strict=True):
        raw_writer.write_row(raw_row)
        prepared_writer.write_row(
            PreparedManifestRow(
                audio=raw_row["audio"],
                text=raw_row["text"],
                ref_audio=raw_row["ref_audio"],
                speaker_id=raw_row["speaker_id"],
                dataset=raw_row["dataset"],
                source_split=raw_row["source_split"],
                quality_tier=raw_row["quality_tier"],
                audio_codes=audio_codes,
            )
        )
        prepared_count += 1
    write_seconds = time.perf_counter() - write_started_at
    chunk_row_count = prepared_count
    raw_rows.clear()
    return Task101AudioCodesChunkSummary(
        leaf_chunk_count=1,
        chunk_row_count=chunk_row_count,
        min_effective_chunk_row_count=chunk_row_count,
        max_effective_chunk_row_count=chunk_row_count,
        encode_call_seconds=encode_call_seconds,
        preload_seconds=None if encoder_timing is None else encoder_timing.preload_seconds,
        feature_extract_seconds=(
            None if encoder_timing is None else encoder_timing.feature_extract_seconds
        ),
        model_encode_seconds=(
            None if encoder_timing is None else encoder_timing.model_encode_seconds
        ),
        render_seconds=None if encoder_timing is None else encoder_timing.render_seconds,
        oom_retry_count=0,
        oom_retry_seconds=0.0,
        write_seconds=write_seconds,
        total_seconds=encode_call_seconds + write_seconds,
    )


def _summarize_audio_codes_batch_timings(
    chunk_summaries: list[Task101AudioCodesChunkSummary],
    *,
    batch_total_seconds: float,
) -> Task101AudioCodesBatchSummary:
    """Aggregate one finalized batch's audio-code timings into machine-readable totals."""
    chunk_total_seconds = float(sum(chunk.total_seconds for chunk in chunk_summaries))
    min_effective_chunk_row_counts = [
        chunk.min_effective_chunk_row_count
        for chunk in chunk_summaries
        if chunk.min_effective_chunk_row_count is not None
    ]
    max_effective_chunk_row_counts = [
        chunk.max_effective_chunk_row_count
        for chunk in chunk_summaries
        if chunk.max_effective_chunk_row_count is not None
    ]
    return Task101AudioCodesBatchSummary(
        chunk_count=sum(chunk.leaf_chunk_count for chunk in chunk_summaries),
        encoded_row_count=sum(chunk.chunk_row_count for chunk in chunk_summaries),
        min_effective_chunk_row_count=(
            None if not min_effective_chunk_row_counts else min(min_effective_chunk_row_counts)
        ),
        max_effective_chunk_row_count=(
            None if not max_effective_chunk_row_counts else max(max_effective_chunk_row_counts)
        ),
        encode_call_seconds=float(sum(chunk.encode_call_seconds for chunk in chunk_summaries)),
        preload_seconds=_sum_optional_chunk_values(
            [chunk.preload_seconds for chunk in chunk_summaries]
        ),
        feature_extract_seconds=_sum_optional_chunk_values(
            [chunk.feature_extract_seconds for chunk in chunk_summaries]
        ),
        model_encode_seconds=_sum_optional_chunk_values(
            [chunk.model_encode_seconds for chunk in chunk_summaries]
        ),
        render_seconds=_sum_optional_chunk_values(
            [chunk.render_seconds for chunk in chunk_summaries]
        ),
        oom_retry_count=sum(chunk.oom_retry_count for chunk in chunk_summaries),
        oom_retry_seconds=float(sum(chunk.oom_retry_seconds for chunk in chunk_summaries)),
        write_seconds=float(sum(chunk.write_seconds for chunk in chunk_summaries)),
        chunk_total_seconds=chunk_total_seconds,
        batch_total_seconds=batch_total_seconds,
        non_audio_codes_seconds=max(batch_total_seconds - chunk_total_seconds, 0.0),
    )


def _batch_timing_summary_payload(
    summary: Task101AudioCodesBatchSummary,
) -> dict[str, object]:
    """Render one batch-level audio-code timing summary for progress-event payloads."""
    return {
        "audio_codes_batch_total_seconds": summary.batch_total_seconds,
        "audio_codes_chunk_count": summary.chunk_count,
        "audio_codes_chunk_total_seconds": summary.chunk_total_seconds,
        "audio_codes_encode_call_seconds": summary.encode_call_seconds,
        "audio_codes_encoded_row_count": summary.encoded_row_count,
        "audio_codes_feature_extract_seconds": summary.feature_extract_seconds,
        "audio_codes_max_effective_chunk_row_count": summary.max_effective_chunk_row_count,
        "audio_codes_min_effective_chunk_row_count": summary.min_effective_chunk_row_count,
        "audio_codes_model_encode_seconds": summary.model_encode_seconds,
        "audio_codes_non_audio_seconds": summary.non_audio_codes_seconds,
        "audio_codes_oom_retry_count": summary.oom_retry_count,
        "audio_codes_oom_retry_seconds": summary.oom_retry_seconds,
        "audio_codes_preload_seconds": summary.preload_seconds,
        "audio_codes_render_seconds": summary.render_seconds,
        "audio_codes_write_seconds": summary.write_seconds,
    }


def _combine_audio_codes_chunk_summaries(
    chunk_summaries: list[Task101AudioCodesChunkSummary],
    *,
    extra_oom_retry_count: int = 0,
    extra_oom_retry_seconds: float = 0.0,
) -> Task101AudioCodesChunkSummary:
    """Combine one or more chunk summaries into one aggregate summary."""
    min_effective_chunk_row_counts = [
        chunk.min_effective_chunk_row_count
        for chunk in chunk_summaries
        if chunk.min_effective_chunk_row_count is not None
    ]
    max_effective_chunk_row_counts = [
        chunk.max_effective_chunk_row_count
        for chunk in chunk_summaries
        if chunk.max_effective_chunk_row_count is not None
    ]
    return Task101AudioCodesChunkSummary(
        leaf_chunk_count=sum(chunk.leaf_chunk_count for chunk in chunk_summaries),
        chunk_row_count=sum(chunk.chunk_row_count for chunk in chunk_summaries),
        min_effective_chunk_row_count=(
            None if not min_effective_chunk_row_counts else min(min_effective_chunk_row_counts)
        ),
        max_effective_chunk_row_count=(
            None if not max_effective_chunk_row_counts else max(max_effective_chunk_row_counts)
        ),
        encode_call_seconds=float(sum(chunk.encode_call_seconds for chunk in chunk_summaries)),
        preload_seconds=_sum_optional_chunk_values(
            [chunk.preload_seconds for chunk in chunk_summaries]
        ),
        feature_extract_seconds=_sum_optional_chunk_values(
            [chunk.feature_extract_seconds for chunk in chunk_summaries]
        ),
        model_encode_seconds=_sum_optional_chunk_values(
            [chunk.model_encode_seconds for chunk in chunk_summaries]
        ),
        render_seconds=_sum_optional_chunk_values(
            [chunk.render_seconds for chunk in chunk_summaries]
        ),
        oom_retry_count=(
            sum(chunk.oom_retry_count for chunk in chunk_summaries) + extra_oom_retry_count
        ),
        oom_retry_seconds=(
            float(sum(chunk.oom_retry_seconds for chunk in chunk_summaries))
            + extra_oom_retry_seconds
        ),
        write_seconds=float(sum(chunk.write_seconds for chunk in chunk_summaries)),
        total_seconds=(
            float(sum(chunk.total_seconds for chunk in chunk_summaries)) + extra_oom_retry_seconds
        ),
    )


def _sum_optional_chunk_values(values: list[float | None]) -> float | None:
    """Sum one optional timing list when at least one value is present."""
    rendered_values = [value for value in values if value is not None]
    if not rendered_values:
        return None
    return float(sum(rendered_values))


def _is_audio_codes_out_of_memory_error(exc: RuntimeError) -> bool:
    """Return whether the raised runtime error is an audio-code OOM failure."""
    message = str(exc).lower()
    if "out of memory" in message:
        return True
    try:
        import torch
    except ImportError:
        return False
    return isinstance(exc, torch.OutOfMemoryError)


def _release_audio_codes_gpu_memory() -> None:
    """Best-effort GPU memory release after one chunk-level OOM retry trigger."""
    gc.collect()
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _validate_prepared_manifest_payload_paths(
    output_root: Path,
    payload: dict[str, object],
) -> None:
    """Fail closed when one prepared row escapes or misses bundle-local artifacts."""
    audio_relative_path = _required_string(payload, "audio")
    ref_audio_relative_path = _required_string(payload, "ref_audio")
    audio_path = _bundle_local_artifact_path(output_root, audio_relative_path)
    ref_audio_path = _bundle_local_artifact_path(output_root, ref_audio_relative_path)
    if not audio_path.exists():
        raise ValueError(f"Task 101 batch prepared row is missing audio `{audio_path}`.")
    if not ref_audio_path.exists():
        raise ValueError(f"Task 101 batch prepared row is missing ref audio `{ref_audio_path}`.")


def _bundle_local_artifact_path(output_root: Path, relative_path_text: str) -> Path:
    """Resolve one bundle-local artifact path and reject root escape."""
    relative_path = Path(relative_path_text)
    if relative_path.is_absolute():
        raise ValueError("Task 101 bundle artifacts must use bundle-local relative paths.")
    candidate_path = output_root / relative_path
    try:
        candidate_path.resolve(strict=False).relative_to(output_root.resolve())
    except ValueError as exc:
        raise ValueError("Task 101 bundle artifact paths must not escape the bundle root.") from exc
    return candidate_path


def _required_string(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    return value
