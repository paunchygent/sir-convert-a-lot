---
id: task-364-truthful-stt-progress-and-phase-timing-telemetry
title: Truthful STT progress and phase timing telemetry
type: task
status: completed
priority: high
created: '2026-06-14'
last_updated: '2026-06-14'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md
  - docs/backlog/reviews/review-49-ruthless-review-of-task-364-truthful-stt-progress-and-phase-timing-telemetry.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/downstream_integration_contract_v2.md
labels:
  - stt
  - audio
  - progress
  - telemetry
  - service-api-v2
  - diarization
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make long-running `audio -> transcript_bundle` jobs visibly alive and
truthfully measurable across the full STT pipeline, including the current
pre-transcription diarization gap.

Task 357 already made chunked transcription progress truthful after chunk
planning and accepted chunk checkpoints. Task 362 fixed production runtime
drift by requiring the batched FasterWhisper sidecar path. The remaining user
problem is earlier and broader: a short clip can sit in a visually frozen
state because Sir Convert does not emit explicit diarization progress before
the blocking `sidecar.diarize(...)` call and does not retain phase timing
evidence that downstream UI can use for a measured progress bar and ETA.

This task adds content-safe phase progress and timing telemetry for the
existing Service API v2 STT job lifecycle. It must improve observability and
downstream progress truth without changing chunk size, batch size, route
contracts, retention boundaries, or the accepted canonical transcript JSON
artifact contract.

## PR Scope

- Emit an explicit public progress/stage update before starting diarization.
  Downstream should be able to show normal teacher-facing copy such as
  "Hittar talare" while diarization is actually running, instead of appearing
  frozen between upload/admission and transcription.
- Add sanitized per-phase timing telemetry for:
  - probe and normalization;
  - diarization;
  - transcription;
  - alignment;
  - packaging / final artifact persistence.
- Expose a measured progress/ETA basis suitable for a downstream progress bar.
  The implementation may use current job measurements plus bounded historical
  or configured phase weights, but it must never advance progress from
  heartbeat freshness alone.
- Keep existing audio progress fields for real media/chunk progress:
  `audio_total_media_seconds`, `audio_processed_media_seconds`,
  `audio_percent_complete`, `audio_current_chunk_index`, and
  `audio_total_chunks`.
- Preserve the accepted 300-second chunk planning and production
  `batch_size=8` runtime defaults. Benchmarking smaller chunks or different
  batch sizes is explicitly deferred to a later governed tuning task.
- Preserve fail-closed behavior for media probe, normalization, diarization,
  transcription, alignment, packaging, cancellation, retry, and artifact
  persistence failures.
- Keep telemetry and logs content-safe: no transcript text, utterances,
  speaker display names, raw filenames as user labels, media hashes as labels,
  credentials, API keys, signed headers, model provider secrets, or source
  content.
- Update Service API v2 docs/OpenAPI/downstream contracts if new public
  progress fields are added or existing field semantics are clarified.

Out of scope:

- No chunk-size change.
- No batch-size change.
- No local or downstream formatter work.
- No browser/UI implementation in Skriptoteket.
- No CPU fallback, silent sidecar fallback, or changed GPU/offload policy.
- No partial transcript artifacts for running, failed, or canceled jobs.

## Deliverables

- [x] Explicit `diarizing` progress/stage emission before the sidecar
  diarization call begins.
- [x] Per-phase timing telemetry for probe/normalize, diarization,
  transcription, alignment, and packaging.
- [x] Measured progress/ETA data that downstream consumers can render as a
  progress bar without treating 0% as dead for single- or few-chunk jobs.
- [x] Content-safety tests for telemetry/logging redaction.
- [x] Updated Service API v2 converter/downstream docs for any public
  progress-field additions or semantic clarifications.
- [x] Handoff note for Skriptoteket `PR-0351` describing the exact progress
  payload and which fields are estimated versus observed.

## Acceptance Criteria

- [x] A job entering diarization emits a visible progress state before
  `sidecar.diarize(...)` blocks; polling must not skip directly from
  probe/normalization to transcription when diarization is in progress.
- [x] Phase timings are recorded for successful and failed jobs with
  correlation/job/route metadata only, and no transcript text, utterances,
  speaker display names, credentials, signed headers, or source content.
- [x] The measured progress/ETA payload is monotonic, bounded, and documented.
  It must not claim exact chunk completion when no chunk has been accepted and
  must not advance solely because `last_heartbeat_at` is fresh.
- [x] Existing Task 357 chunk progress remains truthful and monotonic after
  chunk checkpoints are accepted.
- [x] Existing malformed media, diarization failure, transcription failure,
  alignment failure, cancellation, retry, retention, and owner-scoped access
  behavior remains fail-closed.
- [x] OpenAPI/docs still describe the existing Service API v2 job lifecycle;
  any new progress fields are additive and backward-compatible.

## Red-First Test Plan

Add or extend focused tests before production changes:

- `tests/sir_convert_a_lot/test_audio_transcript_phase_progress_v2.py`
  - proves `diarizing` progress is emitted before the sidecar diarize call;
  - proves heartbeat-only activity does not fabricate percent completion;
  - proves single- or few-chunk jobs expose a measured progress/ETA payload
    while long blocking phases are active.
- `tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py`
  - proves probe/normalize, diarization, transcription, alignment, and
    packaging timings are recorded for success;
  - proves failure timings are retained without leaking content.
- `tests/sir_convert_a_lot/test_audio_transcript_progress_redaction_v2.py`
  - proves telemetry/log output excludes transcript text, utterances, speaker
    display names, credentials, signed headers, source content, and raw
    artifact bytes.
- Existing focused regression suites from Tasks 357 and 362 must still pass
  for chunk progress, checkpointing, cancellation, sidecar contract, and
  batched FasterWhisper capability truth.

Focused validation commands:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_phase_progress_v2.py
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_phase_timing_telemetry_v2.py
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_progress_redaction_v2.py
```

Full close-out:

```bash
pdm run format-all
pdm run lint-fix
pdm run typecheck-all
pdm run coverage-gate
pdm run docs-sync
pdm run docs-validate
pdm run skills-validate
pdm run handoff-validate
git diff --check
```

## Stop Conditions

- Stop before changing chunk size, overlap size, chunk count semantics, or
  sidecar batch size.
- Stop before reporting fake percent completion from heartbeat freshness,
  elapsed wall time alone, or unaccepted chunk output.
- Stop before exposing transcript text, utterances, speaker display names,
  media hashes, credentials, signed headers, or source content in logs,
  metrics, traces, artifacts, or public errors.
- Stop before changing the Service API v2 route contract in a breaking way.
- Stop before weakening Task 357 checkpoint/cancellation guarantees or Task
  362 batched-runtime truth.

## Handoff Requirement

Before this task is marked complete, record a concise downstream handoff for
Skriptoteket `PR-0351` that names:

- the exact progress fields to consume;
- which fields are observed and which are measured estimates;
- the phase names that may be safely mapped to normal Swedish UI copy;
- timeout/failure semantics;
- the focused smoke or test command proving a representative job emits the new
  diarization/progress/timing evidence.

## Implementation Evidence

Task 364 is locally implemented and approved by the fixed independent
gpt-5.5 high ruthless review in
`docs/backlog/reviews/review-49-ruthless-review-of-task-364-truthful-stt-progress-and-phase-timing-telemetry.md`.

Implemented public progress contract:

- `stage` now emits `diarizing` before the blocking `sidecar.diarize(...)`
  call starts.
- Existing observed chunk fields remain the exact media/chunk truth:
  `audio_total_media_seconds`, `audio_processed_media_seconds`,
  `audio_percent_complete`, `audio_current_chunk_index`, and
  `audio_total_chunks`.
- Additive whole-pipeline estimates are exposed as
  `audio_pipeline_percent_complete` and `audio_pipeline_eta_seconds`. They are
  monotonic, bounded, and updated only on explicit phase/progress events, never
  from heartbeat freshness alone.
- Canonical audio timing keys are persisted in
  `job.progress.phase_timings_ms`: `audio_probe_normalize_ms`,
  `audio_diarization_ms`, `audio_transcription_ms`, `audio_alignment_ms`, and
  `audio_packaging_ms`, alongside existing terminal timing keys such as
  `final_artifact_persist_ms` and `conversion_total_ms`.

Validation evidence:

- Red-first focused Task 364 suite first failed with `5 failed` because
  `diarizing`, canonical audio timing keys, and additive pipeline progress
  fields were absent.
- Focused Task 364 trio later passed with `5 passed`.
- Focused regression bundle plus phase timing helper proof passed with
  `20 passed`.
- Independent Review 49 reran the Task 364/focused regression bundle with
  `10 passed`.
- `coverage-gate` passed with `1721 passed, 6 skipped` and `95.37%`
  coverage.
- `format-all`, `lint-fix`, `typecheck-all`, `docs-validate`,
  `skills-validate`, `handoff-validate`, and `git diff --check` passed during
  implementation/review closeout.
- No live Hemma deploy or GPU sidecar validation was run for this local
  contract slice.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
