---
id: story-54-transcript-formatter-strategies-over-canonical-json
title: Transcript formatter strategies over canonical JSON
type: story
status: completed
priority: high
created: '2026-06-09'
last_updated: '2026-06-12'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/tasks/task-356-execute-audio-transcript-jobs-and-persist-canonical-transcript-json.md
  - docs/backlog/tasks/task-357-harden-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md
  - docs/backlog/reviews/review-28-ruthless-review-of-story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/reviews/review-29-ruthless-review-of-story-54-transcript-formatter-strategies-over-canonical-json.md
  - docs/backlog/reviews/review-42-ruthless-review-of-task-356-audio-transcript-runtime-json-persistence.md
  - docs/backlog/reviews/review-43-ruthless-review-of-task-357-audio-transcript-chunk-progress-and-checkpointed-stt-execution.md
  - docs/backlog/reviews/review-44-ruthless-review-of-task-358-product-neutral-transcript-formatter-artifacts.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
labels:
  - transcript
  - formatter
  - json
  - vtt
  - srt
  - markdown
---

Proposed implementation slice with acceptance-driven scope.

## Objective

Add optional human-readable transcript formatter artifacts as modular
strategies over the canonical `transcript_json` artifact now that the JSON core
is accepted and live-proven.

## Runtime Readiness Decision

The old blocked Story 54 state is superseded. Review 29 accepted the
truthfulness of the blocked state while Story 53 had no runtime route or JSON
artifact authority. That is no longer the current lane state: Task 356 and
Review 42 accepted sidecar-backed `audio -> transcript_bundle` execution and
canonical `transcript_json` persistence; Task 357 and Review 43 accepted the
chunked progress/runtime hardening that preserves the JSON core for
long-running jobs.

Story 54 is therefore active for formatter implementation planning. The first
PR-sized execution unit is
`docs/backlog/tasks/task-358-implement-product-neutral-transcript-formatter-artifacts-over-canonical-json.md`.

Current runtime truth:

- Service API v2 accepts and executes `audio -> transcript_bundle`.
- Successful jobs expose canonical `transcript_json` through the v2 result,
  artifact list, and named artifact retrieval surfaces.
- Task 358 implementation work adds optional product-neutral `txt`, `md`,
  `vtt`, and `srt` formatter artifacts over canonical JSON, with requested
  artifacts exposed through named retrieval and unrequested artifacts represented
  explicitly as `unrequested`.
- Review 44 accepted Task 358 after the pass-two module extraction, so Story 54
  is complete for the product-neutral formatter authority slice.

## Ownership Boundary

Sir Convert owns deterministic, product-neutral standard-format transformations
from canonical transcript JSON to TXT, neutral Markdown, WebVTT, and SRT.
Downstream apps own product meaning: which export buttons appear, teacher-facing
labels, filenames, durable save/readback behavior, lesson-material or
subtitle-workbench workflows, search, sharing, and any product-specific
Markdown derivatives.

## Scope

- Implement formatter strategies for:
  - plain text;
  - Markdown;
  - WebVTT;
  - SubRip/SRT.
- Keep formatter logic downstream of JSON artifact assembly; formatters must
  not call STT, diarization, or segment-alignment code.
- Wire formatter strategies with small DDD/Clean components and DI where route
  composition benefits from it.
- Preserve diarization and timestamp truth in subtitle formats.
- Fail or omit formatter artifacts explicitly when the JSON core does not meet
  formatter prerequisites.
- Keep future Skriptoteket-specific presentation choices out of Sir Convert's
  core formatter strategy layer.
- Keep Sir Convert artifact retention short and operational; durable transcript
  saves remain downstream product responsibilities.

## Acceptance Criteria

- [x] `transcript_txt`, `transcript_md`, `transcript_vtt`, and
  `transcript_srt` can be requested only after `transcript_json` is valid.
- [x] Formatter artifacts are named, typed, and represented explicitly in
  bundle metadata.
- [x] Formatters preserve segment ordering, timestamps, speaker labels, and
  warnings where the target format supports them.
- [x] No formatter duplicates transcription, diarization, or alignment logic.
- [x] Formatter-specific errors do not corrupt or replace the canonical JSON
  artifact.

## Test Requirements

- [x] Golden JSON-to-TXT/Markdown/VTT/SRT formatter tests.
- [x] Timestamp formatting and cue ordering tests for subtitle outputs.
- [x] Speaker-label rendering tests for multi-speaker transcripts.
- [x] Error-path tests for invalid JSON core and unsupported formatter
  requests.
- [x] DI composition tests for route formatter strategy selection.
- [x] Docs validation: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Done Definition

The story is done when transcript formatter artifacts are available as
side-effect-free strategies over canonical JSON and downstream consumers can
choose JSON-first persistence without waiting for every human-readable format.

## Checklist

- [x] Historical blocked implementation decision recorded
- [x] Historical unimplemented formatter state superseded by Task 358
  implementation checkpoint
- [x] Story 53 blocker superseded by Task 356/357 acceptance
- [x] Runtime readiness state updated after Task 356/357 acceptance
- [x] Task 358 created for product-neutral formatter implementation
- [x] Runtime formatter implementation complete
- [x] Runtime tests and validations complete
- [x] Runtime docs synchronized
