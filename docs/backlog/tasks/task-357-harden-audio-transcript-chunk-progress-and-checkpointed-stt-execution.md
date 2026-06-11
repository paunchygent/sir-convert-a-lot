---
id: task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution
title: Harden audio transcript chunk progress and checkpointed STT execution
type: task
status: in_progress
priority: high
created: '2026-06-11'
last_updated: '2026-06-11'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json.md
  - docs/backlog/reviews/review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - stt
  - audio
  - v2
  - progress
  - checkpointing
  - diarization
  - sidecar
---

PR-sized execution unit linked to the accepted STT runtime lane.

## Objective

Harden the accepted `audio -> transcript_bundle` runtime so long-running audio
jobs expose truthful, monotonic chunk progress during transcription instead of
only stage heartbeats while the sidecar call is blocking.

Task 356 delivered the first deployed JSON runtime and remains accepted. The
live polling gap is narrower: a job can be healthy and actively
`transcribing`, with fresh `last_heartbeat_at`, while
`audio_total_media_seconds`, `audio_processed_media_seconds`,
`audio_percent_complete`, `audio_current_chunk_index`, and
`audio_total_chunks` remain `null` until the sidecar returns. This task closes
that gap by making Sir Convert own the durable chunk plan, checkpoint state,
public progress projection, retry semantics, and cancellation cleanup.

The sidecar remains the GPU-backed capability provider. Sir Convert must not
move FasterWhisper, pyannote, FFmpeg, model-cache, or codec dependencies into
the main service image, and must not introduce CPU fallback.

Local implementation has landed in the worktree for Review 43 repair. It is not
closed until validation and live Hemma/tunnel proof are recorded.

## Design Decision

Use service-owned chunk planning and checkpointing as the durable source of
public progress. Sidecar progress hooks may be consumed as best-effort
intra-chunk telemetry, but they must not be the authoritative lifecycle state.

The preferred runtime shape is:

1. Probe and normalize the full source under the governed sidecar/media
   boundary.
1. Persist normalized media metadata, duration, hashes, and deterministic chunk
   plan in the Sir Convert job store.
1. Run global diarization over the normalized audio so speaker labels remain
   consistent across chunks.
1. Run chunked FasterWhisper transcription over deterministic windows.
1. Align chunk transcript segments against global exclusive diarization.
1. Advance audio progress only after each chunk's transcript output is accepted
   and checkpointed.
1. Persist final `transcript_json` only after all chunks complete and
   cross-chunk alignment validates.

Do not implement independent per-chunk diarization as the default path unless a
reviewed reconciliation design prevents speaker-label drift across chunks.

Review 43 repair locks the sidecar transition as a clean internal contract:
the main Service API v2 runtime uses `/probe-media`, `/diarize`,
`/transcribe-chunk`, `/finalize`, and `/cancel`. It must not use the retired
blocking `/transcribe` path. Normalized media is an opaque sidecar-owned
capability issued by `/probe-media`, verified by `request_handle` and
`normalized_audio.sha256` before diarization or chunk transcription, and
finalized idempotently at terminal job cleanup.

Third-party API research from the planning pass:

- FasterWhisper exposes segments, word timestamps, batched/chunked inference,
  VAD filtering, and `log_progress`; it does not provide durable service-owned
  progress state.
- pyannote.audio supports GPU execution, exact `num_speakers`,
  `min_speakers` / `max_speakers`, exclusive diarization output, and
  `ProgressHook`; those hooks are useful telemetry but not a replacement for
  Sir Convert's persisted job lifecycle.

## PR Scope

- Introduce a purpose-named domain model for audio chunk plans and checkpoint
  state:
  - normalized media hash;
  - chunk index;
  - start/end seconds;
  - overlap seconds;
  - processing profile;
  - checkpoint status;
  - accepted transcription segment ids;
  - accepted diarization window ids;
  - alignment validation state.
- Extend or adapt the internal STT sidecar contract so Sir Convert can request
  bounded operations needed by the service-owned lifecycle:
  - probe/normalization metadata sufficient to create a deterministic plan;
  - global diarization for normalized media;
  - chunk transcription for a deterministic media window;
  - optional intra-chunk progress events if the sidecar can expose them without
    becoming the lifecycle owner.
- Replace the single blocking runtime path with a checkpointed orchestration
  flow that updates persisted public progress after each accepted chunk.
- Set `audio_total_media_seconds` and `audio_total_chunks` after probe/chunk
  planning succeeds.
- Set `audio_processed_media_seconds`, `audio_percent_complete`, and
  `audio_current_chunk_index` monotonically as chunks are accepted.
- Keep `last_heartbeat_at` fresh independently of numeric progress.
- Preserve the existing canonical `transcript_json` schema and named artifact
  access contract.
- Preserve the existing fail-closed diarization behavior: no successful job may
  expose missing speakers, placeholder speakers, or `diarization_unavailable`.
- Preserve `retention.pin=false`, short Sir Convert artifact retention, and
  product-owned durable transcript storage boundaries.
- Preserve owner-scoped API-key tunnel and Gateway
  `InternalIdentityContextV1` access behavior.
- Preserve all existing PDF, DOCX, Markdown, HTML, DigiExam, and formatter
  blocked-state behavior.
- Deploy to Hemma and prove live tunnel behavior with at least one real audio
  fixture whose transcription phase lasts long enough to observe non-null
  progress during polling.

Out of scope:

- Markdown, TXT, VTT, or SRT formatter artifacts.
- Skriptoteket durable transcript saves.
- Public grant, anonymous, direct browser, or direct sidecar ingress.
- CPU fallback for any STT or diarization work.
- Per-chunk diarization without a reviewed speaker-reconciliation design.
- Exposing partial transcript artifacts for failed, canceled, or running jobs.

## Implementation State

As of the 2026-06-11 Review 43 repair pass:

- Purpose-named runtime modules exist for chunk planning, checkpoint
  persistence, progress projection, transcript payload assembly, sidecar
  request construction, alignment, and checkpoint merge.
- The sidecar FastAPI/runtime contract exposes `/probe-media`, `/diarize`,
  `/transcribe-chunk`, `/finalize`, and `/cancel`.
- `/probe-media` returns a sidecar-owned opaque normalized-audio handle and
  SHA-256. `/diarize` and `/transcribe-chunk` reject unknown, wrong-request,
  stale, or hash-mismatched handles with deterministic client-safe errors.
- The Service API v2 runtime finalizes sidecar-owned normalized media on
  success, terminal failure, and cancellation, while preserving the original
  governed sidecar error code on terminal failure.
- Local behavior tests cover public chunk progress, checkpoint replay,
  cancellation cleanup, canonical `transcript_json`, fail-closed alignment,
  sidecar HTTP contract, sidecar handle validation, and sidecar media cleanup.
- Hemma deploy verification passed for revision
  `fdee238bedc6bb5193910993ce465576d67903f3` with service revision parity:
  `build/verification/hemma-deploy-verify/report.md`.
- Live tunnel proof passed for revision
  `fdee238bedc6bb5193910993ce465576d67903f3`:
  `build/verification/task-357-live-progress-proof-fdee238/proof.md`.
  The proof submitted the English two-speaker fixture, observed running
  `transcribing` progress with `audio_total_media_seconds=675.250667`,
  `audio_processed_media_seconds=675.250667`,
  `audio_percent_complete=100.0`, `audio_current_chunk_index=2`, and
  `audio_total_chunks=3`, then retrieved terminal `transcript_json_v1` with
  `293` segments.

## Deliverables

- [x] Updated `docs/converters/audio-transcription-service-api-artifact-contract.md`
  language that distinguishes stage heartbeat from numeric audio progress and
  records the Task 357 chunk/checkpoint hardening contract.
- [x] Purpose-named implementation modules for chunk planning, checkpoint
  persistence, progress projection, and transcript merge/alignment.
- [x] Internal sidecar contract/client changes for global diarization and
  chunk transcription, or an explicitly reviewed equivalent that preserves
  service-owned public progress.
- [x] Red-first behavior tests for public polling progress during active
  transcription.
- [x] Red-first behavior tests for checkpoint idempotency, retry, cancellation,
  and no partial terminal artifacts.
- [x] Red-first behavior tests for cross-chunk transcript/diarization
  alignment and speaker-label stability.
- [x] Focused live Hemma proof showing non-null numeric progress while a job is
  still running, followed by successful `transcript_json` retrieval.
- [ ] Retained ruthless review artifact accepted after deployed live proof.

## Acceptance Criteria

- [x] After media probe/chunk planning succeeds, public job polling exposes
  non-null `audio_total_media_seconds`, `audio_total_chunks`, and initial
  numeric audio progress without overloading PDF page counters.
- [x] During active transcription, `audio_processed_media_seconds` and
  `audio_percent_complete` advance monotonically after accepted chunk
  checkpoints. Progress must never advance based only on a heartbeat.
- [x] `audio_current_chunk_index` reflects the current or most recently
  accepted chunk according to the documented contract and never exceeds
  `audio_total_chunks - 1`.
- [x] `last_heartbeat_at` remains fresh while probe, diarization,
  transcription, alignment, or packaging work is active, even when a chunk is
  long-running and numeric progress does not change.
- [x] Global diarization or an approved reconciliation equivalent prevents
  speaker-label drift across chunk boundaries.
- [x] Final `transcript_json` remains canonical and is persisted only after all
  chunk transcript segments validate against diarization/alignment.
- [x] Failed or canceled jobs expose no partial transcript artifact and purge
  incomplete normalized media, sidecar temp chunks, checkpoints, and partial
  transcript state according to the retention policy.
- [x] Retry and idempotent replay cannot duplicate transcript segments,
  diarization windows, checkpoints, or named artifacts.
- [x] The sidecar remains internal-only and GPU-required; no main-image STT
  dependencies, direct sidecar ingress, or CPU fallback are introduced.
- [x] Live tunnel proof demonstrates running-state polling with non-null audio
  progress before terminal success.

## Red-First Test Plan

Purpose-named tests should be added before production changes. Suggested test
areas:

- `tests/sir_convert_a_lot/test_audio_transcript_progress_v2.py`
  - proves public job polling shows total duration/chunk count after probe;
  - proves numeric progress advances during transcription;
  - proves progress does not advance from heartbeat-only activity.
- `tests/sir_convert_a_lot/test_audio_transcript_checkpointing_v2.py`
  - proves retry resumes from accepted checkpoints without duplicate segments;
  - proves idempotent replay preserves the same terminal artifact.
- `tests/sir_convert_a_lot/test_audio_transcript_cancellation_v2.py`
  - proves cancellation during chunk execution stops future chunk scheduling
    and exposes no terminal transcript artifact.
- `tests/sir_convert_a_lot/test_audio_transcript_alignment_v2.py`
  - proves final JSON persistence is blocked when cross-chunk
    transcript/diarization alignment fails;
  - proves speaker labels remain stable across chunk boundaries.

Focused validation commands:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_progress_v2.py
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_checkpointing_v2.py
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_cancellation_v2.py
pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcript_alignment_v2.py
```

Full close-out for the implementation task must also run the backend gates from
`AGENTS.md`:

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

- Stop before reporting fabricated percent completion from heartbeat freshness
  alone.
- Stop before accepting per-chunk diarization that can drift speaker labels
  without a governed reconciliation design.
- Stop before exposing partial transcripts as terminal artifacts.
- Stop before adding STT, diarization, FFmpeg, codec, or model dependencies to
  the main service image.
- Stop before changing public API semantics, retention classes, or Gateway
  identity boundaries without updating the converter/API contract and linked
  downstream docs.
- Stop before deploying or reviewing if the live proof cannot show non-null
  numeric progress while a job is still running.

## Done Definition

The task is done when the deployed STT runtime preserves the accepted
`transcript_json` contract and additionally proves service-owned chunk
planning, checkpointed execution, and truthful non-null audio progress during
active transcription through the tunnel.

## Checklist

- [x] Local implementation complete
- [x] Validation complete
- [x] Docs updated
- [x] Live Hemma proof recorded
