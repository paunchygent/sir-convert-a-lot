---
type: decision
id: ADR-0005
title: V2 Long-Job Progress, Checkpoints, Partials, Cancel-with-Save, Resume, and Retention
status: accepted
created: '2026-03-04'
updated: '2026-03-04'
owners:
  - platform
tags:
  - adr
  - v2
  - long-pdf
  - progress
  - checkpoints
  - partial-results
  - cancel
  - resume
  - retention
links:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-18-page-level-progress-and-stall-telemetry-contract.md
  - docs/backlog/stories/story-19-checkpointed-partial-results-and-resumable-ocr-pipeline.md
  - docs/backlog/tasks/task-68-publish-adr-for-progress-checkpoint-and-resume-contract.md
  - docs/backlog/tasks/task-69-add-page-level-progress-fields-to-v2-jobs-api.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - docs/backlog/tasks/task-71-add-cancel-with-save-and-resume-from-checkpoint-flow.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
---

## Status

- Accepted
- Date: 2026-03-04

## 1. Problem and Context

Long PDF OCR conversions can run for minutes to hours. Today, v2 provides a job lifecycle with
heartbeat timestamps but lacks:

- page-level progress for operators and UIs,
- deterministic partial artifacts/checkpoints for safe interruption,
- contract-locked cancel-with-save and resume semantics,
- explicit retention rules for partial artifacts/checkpoints to prevent unbounded disk growth.

Additionally, client poll windows must distinguish between:

- active long-running jobs that exceed local wait windows, and
- stalled jobs that stopped heartbeating/progressing.

This ADR locks semantics before implementation work lands (`T69-T71`) to prevent contract drift.

## 2. Decision

Adopt the following v2 long-job contract rules for PDF conversions:

1. Add **page-aware progress fields** to polling and async push (SSE/webhooks) payloads.
1. Introduce **checkpoint + partial markdown** persistence during execution (chunk-based).
1. Define **partial artifact retrieval** for running and canceled jobs.
1. Define **cancel-with-save** as the default cancellation semantics for long PDF jobs.
1. Define **resume-from-checkpoint** as a first-class v2 workflow that produces a new `job_id`.
1. Bound storage growth via explicit **retention and cleanup** rules.

## 3. Scope and Versioning

- Applies to **service API v2 only**.
- Initial scope is **PDF routes** (primary: `pdf -> md`, later `pdf -> docx` if/when checkpoints are
  extended).
- Non-PDF routes remain compatible:
  - new PDF-specific progress/checkpoint fields are omitted or set to `null` by contract.
- Polling remains supported and unchanged as a surface; payload shape is additive.
- Async push must remain parity-aligned with polling for progress fields (see ADR-0003).

## 4. Progress Contract (Polling + Push)

### 4.1 Fields (PDF routes)

Extend `job.progress` with optional PDF-only fields:

| Field | Type | Rules |
| --- | --- | --- |
| `total_pages` | `int \| null` | Total pages discovered; set once known. |
| `processed_pages` | `int \| null` | Monotonic; never decreases; `<= total_pages`. |
| `failed_pages` | `int \| null` | Monotonic; never decreases; `<= total_pages`. |
| `percent_complete` | `float \| null` | Monotonic non-decreasing; range `0..100`. |
| `pages_per_minute` | `float \| null` | Non-negative; best-effort estimate. |
| `eta_seconds` | `int \| null` | Non-negative; best-effort estimate. |

Existing progress diagnostics remain:

- `stage`
- `last_heartbeat_at`
- `current_phase_started_at`
- `phase_timings_ms`

### 4.2 Non-PDF routes

For non-PDF routes:

- `total_pages`, `processed_pages`, `failed_pages`, `percent_complete`, `pages_per_minute`,
  `eta_seconds` are **omitted or `null`**.
- `last_heartbeat_at` remains present for liveness.

### 4.3 Push parity

SSE and webhook lifecycle progress payloads must carry the same PDF-only progress fields when
available, so UI clients do not require polling for progress visibility.

## 5. Timeout and Stall Taxonomy (Client Semantics)

Clients must distinguish:

- **Active-running poll window exceeded**:
  - job is still `status=running` and heartbeat/progress remains fresh,
  - client emits `error_code=job_poll_window_exceeded` (non-failure running outcome).
- **Stalled timeout**:
  - job is still `status=running` but heartbeat/progress is stale past a configured threshold,
  - client emits `error_code=job_timeout` (treated as failure-like and requires operator attention).

Backward compatibility:

- If page-level progress fields are absent/`null`, clients fall back to heartbeat-only freshness.

## 6. Checkpoints and Partial Artifacts

### 6.1 Chunk model (PDF routes)

- A long PDF job is processed in deterministic **chunks** (page windows).
- Each chunk completion must persist:
  - chunk identity (page range),
  - monotonic counters (`processed_pages`, `failed_pages`),
  - stage timings and heartbeat updates,
  - partial markdown output for completed chunks.

### 6.2 Partial artifact semantics

Partial markdown is defined as:

- concatenation of completed chunk markdown in source order,
- deterministic separators/metadata to avoid duplicate headings on resume merges,
- explicitly labeled as partial (not final) in metadata where returned.

### 6.3 Retrieval endpoints (additive)

Add new endpoints:

1. `GET /v2/convert/jobs/{job_id}/artifact/partial`
   - `200`: returns partial markdown bytes (when available), for `running` or `canceled` jobs.
   - `202`: job exists but no partial artifact is available yet.
   - `404`: job not found/expired.
1. `GET /v2/convert/jobs/{job_id}/checkpoint`
   - `200`: returns checkpoint metadata JSON (when available).
   - `202`: job exists but no checkpoint is available yet.
   - `404`: job not found/expired.

The existing `GET /v2/convert/jobs/{job_id}/artifact` remains terminal-success-only.

## 7. Cancel-with-Save

`POST /v2/convert/jobs/{job_id}/cancel` semantics for long PDF jobs:

- Cancellation remains idempotent.
- On acceptance, the service must:
  - stop further chunk processing,
  - finalize and persist the latest valid checkpoint,
  - make partial artifact retrievable via `/artifact/partial` once available.

Cancel is not guaranteed to be instantaneous; callers should poll for `status=canceled` and then
fetch `/artifact/partial`.

## 8. Resume-from-Checkpoint

Add:

- `POST /v2/convert/jobs/{job_id}/resume`

Rules:

- Resume always creates a new job with a new `job_id`.
- Resume is only allowed when:
  - the original job exists and has a valid checkpoint, and
  - required input material is still available (within retention window, or pinned).
- The resumed job must:
  - skip already completed chunks/pages,
  - preserve deterministic ordering and avoid duplicate output on merge/finalization.

## 9. Retention and Cleanup

Storage must be bounded:

- Checkpoints and partial artifacts are stored under the job’s data root and **expire with the job**.
- `retention.pin=true` pins the job directory and therefore pins partial/checkpoint artifacts as
  well (explicitly opt-in).
- Resume is only supported within the job retention window; pinning is the user-facing mechanism to
  extend that window.

No implementation may introduce unbounded growth (for example per-poll snapshots, unbounded
checkpoint history, or per-page artifacts) without an explicit retention contract update.

## 10. Consequences

Positive:

- Operators and UIs gain real progress, not only heartbeat.
- Long jobs become interruptible and recoverable (cancel-with-save + resume).
- Disk usage remains bounded by explicit retention semantics.

Tradeoffs:

- Additional contract surfaces and storage complexity.
- Chunking introduces known merge/fidelity tradeoffs; these must be documented and tested.
