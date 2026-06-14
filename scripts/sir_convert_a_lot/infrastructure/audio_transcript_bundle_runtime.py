"""Transcript-bundle execution and canonical JSON packaging.

Purpose:
    Execute admitted audio transcript-bundle jobs through the internal STT
    sidecar boundary, validate diarized segment output, and package the first
    canonical transcript JSON artifact without exposing sidecar secrets or
    backend-native model details.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for
      `audio -> transcript_bundle` jobs.
    - Uses `domain.audio_transcription_policy` for sidecar readiness decisions.
    - Emits progress updates consumed by `infrastructure.runtime_job_runner_v2`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_policy import (
    evaluate_stt_sidecar_readiness,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_alignment import (
    align_chunk_segments,
    parse_diarization_windows,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_artifacts import (
    write_requested_transcript_formatter_artifacts,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_checkpoints import (
    AcceptedAudioChunkCheckpoint,
    AudioTranscriptCheckpointStore,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_chunking import (
    AudioChunkWindow,
    plan_audio_chunks,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_merge import (
    build_checkpointed_sidecar_response,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_payloads import (
    build_transcript_payload,
    invalid_sidecar_response,
    required_float,
    required_mapping,
    required_sequence,
    required_string,
    string_list,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_phase_timing import (
    current_transcription_pipeline_percent,
    emit_audio_phase_checkpoint,
    record_phase_timing,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_progress import (
    AUDIO_PIPELINE_PERCENT_ALIGNING,
    AUDIO_PIPELINE_PERCENT_PACKAGING,
    emit_chunk_progress,
    emit_diarizing_progress,
    emit_phase_progress,
    emit_planned_progress,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    AudioProgressUpdateV2,
    AudioTranscriptBundleExecutionResult,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_sidecar_requests import (
    build_chunk_request,
    build_diarization_request,
    build_sidecar_request,
    cleanup_staged_sidecar_source,
    source_media_sha256,
    stage_sidecar_source,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcription_sidecar_client import (
    AudioTranscriptionSidecarClient,
)
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_AUDIO_ALIGNMENT_MS,
    TIMING_KEY_AUDIO_DIARIZATION_MS,
    TIMING_KEY_AUDIO_PACKAGING_MS,
    TIMING_KEY_AUDIO_PROBE_NORMALIZE_MS,
    TIMING_KEY_AUDIO_TRANSCRIPTION_MS,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfConversionCanceledV2,
)


def execute_audio_transcript_bundle_job(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
    sidecar: AudioTranscriptionSidecarClient,
    progress_callback: Callable[[AudioProgressUpdateV2], None] | None,
    is_cancel_requested: Callable[[], bool] | None,
) -> AudioTranscriptBundleExecutionResult:
    """Execute one admitted audio job and persist canonical transcript JSON."""

    checkpoint_store = AudioTranscriptCheckpointStore(artifact_path=job.artifact_path)
    phase_timings_ms: dict[str, int] = {}
    source_hash = source_media_sha256(job)
    sidecar_input_dir = config.audio_transcription_sidecar_input_dir
    emit_phase_progress(
        progress_callback=progress_callback,
        stage="probing_media",
        phase_timings_ms=phase_timings_ms,
        audio_pipeline_percent_complete=0.0,
    )
    try:
        staged_source_path = stage_sidecar_source(job=job, input_dir=sidecar_input_dir)
        probe_started = time.perf_counter()
        try:
            health = sidecar.health()
            capabilities = sidecar.capabilities()
            readiness = evaluate_stt_sidecar_readiness(
                health_payload=health,
                capability_payload=capabilities,
            )
            if not readiness.ready:
                error_code = readiness.error_code or AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE
                raise ServiceError(
                    status_code=503,
                    code=error_code.value,
                    message="Audio transcription sidecar is not ready.",
                    retryable=True,
                    details=dict(readiness.details),
                )

            _raise_if_canceled(is_cancel_requested, sidecar=sidecar, request_handle=job.job_id)
            sidecar_request = build_sidecar_request(job=job, source_path=staged_source_path)

            probe_response = sidecar.probe_media(sidecar_request)
            media = required_mapping(probe_response, "media")
            duration_seconds = required_float(media, "duration_seconds")
            normalized_audio_sha256 = required_string(media, "normalized_audio_sha256")
            normalized_audio_handle_obj = media.get("normalized_audio_handle")
            normalized_audio_handle = (
                normalized_audio_handle_obj
                if isinstance(normalized_audio_handle_obj, str)
                and normalized_audio_handle_obj.strip() != ""
                else None
            )
            plan = plan_audio_chunks(total_media_seconds=duration_seconds)
        except PdfConversionCanceledV2:
            raise
        except Exception:
            record_phase_timing(
                phase_timings_ms=phase_timings_ms,
                key=TIMING_KEY_AUDIO_PROBE_NORMALIZE_MS,
                started_at=probe_started,
            )
            emit_phase_progress(
                progress_callback=progress_callback,
                stage="probing_media",
                phase_timings_ms=phase_timings_ms,
                audio_pipeline_percent_complete=0.0,
            )
            raise
        record_phase_timing(
            phase_timings_ms=phase_timings_ms,
            key=TIMING_KEY_AUDIO_PROBE_NORMALIZE_MS,
            started_at=probe_started,
        )
        emit_diarizing_progress(
            progress_callback=progress_callback,
            plan=plan,
            phase_timings_ms=phase_timings_ms,
        )
        _raise_if_canceled(is_cancel_requested, sidecar=sidecar, request_handle=job.job_id)

        diarization_started = time.perf_counter()
        try:
            diarization_response = sidecar.diarize(
                build_diarization_request(
                    base_request=sidecar_request,
                    normalized_audio_handle=normalized_audio_handle,
                    normalized_audio_sha256=normalized_audio_sha256,
                )
            )
            diarization_windows = parse_diarization_windows(diarization_response)
        except Exception:
            record_phase_timing(
                phase_timings_ms=phase_timings_ms,
                key=TIMING_KEY_AUDIO_DIARIZATION_MS,
                started_at=diarization_started,
            )
            emit_diarizing_progress(
                progress_callback=progress_callback,
                plan=plan,
                phase_timings_ms=phase_timings_ms,
            )
            raise
        record_phase_timing(
            phase_timings_ms=phase_timings_ms,
            key=TIMING_KEY_AUDIO_DIARIZATION_MS,
            started_at=diarization_started,
        )
        emit_planned_progress(
            progress_callback=progress_callback,
            plan=plan,
            phase_timings_ms=phase_timings_ms,
        )
        _raise_if_canceled(is_cancel_requested, sidecar=sidecar, request_handle=job.job_id)

        last_processed_seconds = 0.0
        last_chunk_index = 0

        def emit_current_transcribing_progress() -> None:
            pipeline_percent = current_transcription_pipeline_percent(
                total_media_seconds=plan.total_media_seconds,
                processed_media_seconds=last_processed_seconds,
            )
            emit_audio_phase_checkpoint(
                progress_callback=progress_callback,
                stage="transcribing",
                phase_timings_ms=phase_timings_ms,
                audio_pipeline_percent_complete=pipeline_percent,
                total_media_seconds=plan.total_media_seconds,
                processed_media_seconds=last_processed_seconds,
                current_chunk_index=last_chunk_index,
                total_chunks=plan.total_chunks,
            )

        checkpoints = checkpoint_store.load()
        for chunk in plan.chunks:
            if _checkpoint_matches(
                checkpoint=checkpoints.get(chunk.chunk_index),
                chunk=chunk,
                source_media_sha256=source_hash,
                normalized_audio_sha256=normalized_audio_sha256,
                processing_profile=plan.processing_profile,
            ):
                emit_chunk_progress(
                    progress_callback=progress_callback,
                    plan=plan,
                    chunk=chunk,
                    phase_timings_ms=phase_timings_ms,
                )
                last_processed_seconds = min(plan.total_media_seconds, chunk.end_seconds)
                last_chunk_index = min(chunk.chunk_index, plan.total_chunks - 1)
                continue
            _raise_if_canceled(is_cancel_requested, sidecar=sidecar, request_handle=job.job_id)
            transcription_started = time.perf_counter()
            try:
                chunk_response = sidecar.transcribe_chunk(
                    build_chunk_request(
                        base_request=sidecar_request,
                        chunk=chunk,
                        normalized_audio_handle=normalized_audio_handle,
                        normalized_audio_sha256=normalized_audio_sha256,
                    )
                )
            except Exception:
                record_phase_timing(
                    phase_timings_ms=phase_timings_ms,
                    key=TIMING_KEY_AUDIO_TRANSCRIPTION_MS,
                    started_at=transcription_started,
                )
                emit_current_transcribing_progress()
                raise
            record_phase_timing(
                phase_timings_ms=phase_timings_ms,
                key=TIMING_KEY_AUDIO_TRANSCRIPTION_MS,
                started_at=transcription_started,
            )

            alignment_started = time.perf_counter()
            try:
                aligned_segments, segment_ids, window_ids = align_chunk_segments(
                    segments=required_sequence(chunk_response, "segments"),
                    diarization_windows=diarization_windows,
                )
            except Exception:
                record_phase_timing(
                    phase_timings_ms=phase_timings_ms,
                    key=TIMING_KEY_AUDIO_ALIGNMENT_MS,
                    started_at=alignment_started,
                )
                emit_current_transcribing_progress()
                raise
            record_phase_timing(
                phase_timings_ms=phase_timings_ms,
                key=TIMING_KEY_AUDIO_ALIGNMENT_MS,
                started_at=alignment_started,
            )
            checkpoints[chunk.chunk_index] = AcceptedAudioChunkCheckpoint(
                source_media_sha256=source_hash,
                normalized_audio_sha256=normalized_audio_sha256,
                chunk=chunk,
                processing_profile=plan.processing_profile,
                transcript_segments=aligned_segments,
                accepted_transcription_segment_ids=segment_ids,
                accepted_diarization_window_ids=window_ids,
                alignment_validated=True,
            )
            checkpoint_store.save_all(checkpoints)
            emit_chunk_progress(
                progress_callback=progress_callback,
                plan=plan,
                chunk=chunk,
                phase_timings_ms=phase_timings_ms,
            )
            last_processed_seconds = min(plan.total_media_seconds, chunk.end_seconds)
            last_chunk_index = min(chunk.chunk_index, plan.total_chunks - 1)
            _raise_if_canceled(is_cancel_requested, sidecar=sidecar, request_handle=job.job_id)
        response = build_checkpointed_sidecar_response(
            plan=plan,
            probe_response=probe_response,
            diarization_response=diarization_response,
            checkpoints=checkpoints,
        )
        emit_audio_phase_checkpoint(
            progress_callback=progress_callback,
            stage="aligning_segments",
            phase_timings_ms=phase_timings_ms,
            audio_pipeline_percent_complete=AUDIO_PIPELINE_PERCENT_ALIGNING,
            total_media_seconds=plan.total_media_seconds,
            processed_media_seconds=plan.total_media_seconds,
            current_chunk_index=max(0, plan.total_chunks - 1),
            total_chunks=plan.total_chunks,
        )

        packaging_started = time.perf_counter()
        try:
            artifact_payload = build_transcript_payload(
                job=job,
                response=response,
                readiness_profiles=readiness.profile_labels,
            )
            artifact_bytes = json.dumps(
                artifact_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            _finalize_sidecar(sidecar=sidecar, request_handle=job.job_id, suppress_errors=False)
            job.artifact_path.write_bytes(artifact_bytes)
            write_requested_transcript_formatter_artifacts(
                job=job,
                canonical_json_bytes=artifact_bytes,
            )
        except Exception:
            record_phase_timing(
                phase_timings_ms=phase_timings_ms,
                key=TIMING_KEY_AUDIO_PACKAGING_MS,
                started_at=packaging_started,
            )
            emit_audio_phase_checkpoint(
                progress_callback=progress_callback,
                stage="packaging",
                phase_timings_ms=phase_timings_ms,
                audio_pipeline_percent_complete=AUDIO_PIPELINE_PERCENT_PACKAGING,
                total_media_seconds=plan.total_media_seconds,
                processed_media_seconds=plan.total_media_seconds,
                current_chunk_index=max(0, plan.total_chunks - 1),
                total_chunks=plan.total_chunks,
            )
            raise
        record_phase_timing(
            phase_timings_ms=phase_timings_ms,
            key=TIMING_KEY_AUDIO_PACKAGING_MS,
            started_at=packaging_started,
        )
        media = required_mapping(response, "media")
        duration_seconds = required_float(media, "duration_seconds")
        chunks = required_sequence(media, "chunks")
        emit_phase_progress(
            progress_callback=progress_callback,
            stage="packaging",
            phase_timings_ms=phase_timings_ms,
            audio_pipeline_percent_complete=AUDIO_PIPELINE_PERCENT_PACKAGING,
            audio_total_media_seconds=duration_seconds,
            audio_processed_media_seconds=duration_seconds,
            audio_percent_complete=100.0,
            audio_current_chunk_index=max(0, len(chunks) - 1),
            audio_total_chunks=len(chunks),
        )
        checkpoint_store.purge()
        runtime_metadata = artifact_payload["metadata"]
        if not isinstance(runtime_metadata, Mapping):
            raise invalid_sidecar_response(AudioTranscriptionErrorCode.TRANSCRIPTION_FAILED)
        runtime_obj = runtime_metadata.get("runtime")
        acceleration_used = "rocm"
        if isinstance(runtime_obj, Mapping):
            acceleration_obj = runtime_obj.get("acceleration_used")
            if isinstance(acceleration_obj, str) and acceleration_obj.strip() != "":
                acceleration_used = acceleration_obj
        warnings = string_list(response.get("warnings"))
        return AudioTranscriptBundleExecutionResult(
            artifact_bytes=artifact_bytes,
            backend_used="stt_sidecar",
            acceleration_used=acceleration_used,
            warnings=warnings,
            phase_timings_ms=dict(phase_timings_ms),
        )
    except PdfConversionCanceledV2:
        checkpoint_store.purge()
        raise
    except ServiceError as exc:
        if not exc.retryable:
            checkpoint_store.purge()
        _finalize_sidecar(sidecar=sidecar, request_handle=job.job_id, suppress_errors=True)
        raise
    finally:
        cleanup_staged_sidecar_source(job=job, input_dir=sidecar_input_dir)


def _checkpoint_matches(
    *,
    checkpoint: AcceptedAudioChunkCheckpoint | None,
    chunk: AudioChunkWindow,
    source_media_sha256: str,
    normalized_audio_sha256: str,
    processing_profile: str,
) -> bool:
    if checkpoint is None:
        return False
    return (
        checkpoint.source_media_sha256 == source_media_sha256
        and checkpoint.normalized_audio_sha256 == normalized_audio_sha256
        and checkpoint.processing_profile == processing_profile
        and checkpoint.chunk == chunk
        and checkpoint.alignment_validated
    )


def _raise_if_canceled(
    is_cancel_requested: Callable[[], bool] | None,
    *,
    sidecar: AudioTranscriptionSidecarClient,
    request_handle: str,
) -> None:
    if is_cancel_requested is None or not is_cancel_requested():
        return
    sidecar.cancel(request_handle)
    _finalize_sidecar(sidecar=sidecar, request_handle=request_handle, suppress_errors=True)
    raise PdfConversionCanceledV2(job_id=request_handle)


def _finalize_sidecar(
    *,
    sidecar: AudioTranscriptionSidecarClient,
    request_handle: str,
    suppress_errors: bool,
) -> None:
    try:
        sidecar.finalize(request_handle)
    except ServiceError:
        if not suppress_errors:
            raise
