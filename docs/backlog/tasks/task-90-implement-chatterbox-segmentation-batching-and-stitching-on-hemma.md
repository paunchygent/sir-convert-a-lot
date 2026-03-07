---
id: task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma
title: Implement Chatterbox segmentation batching and stitching on Hemma
type: task
status: completed
priority: high
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes.md
  - docs/backlog/tasks/task-91-implement-speech-aware-chatterbox-stitching-and-tail-cleanup-on-hemma.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
  - docs/reference/ref-espeak-ng-swedish-phoneme-integration-for-chatterbox.md
labels:
  - chatterbox
  - segmentation
  - batching
  - stitching
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add one bounded quality layer for Chatterbox on Hemma that segments longer
Swedish text more safely, batches the resulting chunks deterministically, and
stitches the outputs back together without changing the public service
contract.

## Problem Statement

The pre-Task 90 Chatterbox path was single-pass and lacked sentence-aware
segmentation, chunk execution, and deterministic stitching. That left the repo
without a reviewable long-form synthesis path.

Task 89 also clarified one explicit boundary decision:

- eSpeak preprocessing stays available for future model experiments
- eSpeak is no longer part of the active Chatterbox quality path
- Chatterbox quality work now continues on the normal text path only

## PR Scope

- Add one repo-owned text segmentation module for Swedish-oriented Chatterbox
  lanes.
- Keep segmentation deterministic and reviewable:
  - preserve the original text,
  - write the segment plan as evidence,
  - keep segment order stable.
- Add one bounded chunk execution path that calls the existing Chatterbox
  generation surface one segment at a time.
- Add one deterministic output stitcher:
  - concatenate or cross-fade adjacent chunks,
  - write per-chunk artifacts when debug retention is enabled.
- Keep the current sidecar request contract text-based.
- Add one Hemma benchmark runner that compares:
  - current single-pass lane,
  - segmented-and-stitched lane.
- Add targeted tests for segmentation, batching, stitching, and benchmark
  reporting.

## Non-Goals

- do not redesign the public TTS API
- do not add undocumented Chatterbox generation arguments
- do not combine this task with new phoneme preprocessing logic beyond the
  already-bounded Task 89 helper path

## Deliverables

- [x] Deterministic segmentation planner for longer Swedish text.
- [x] Deterministic chunk execution path for Chatterbox.
- [x] Deterministic stitcher with explicit evidence output.
- [x] Hemma benchmark evidence comparing single-pass vs segmented output.
- [x] Runbook updates for the new quality path.

## Result

Task 90 is now implemented with live Hemma evidence under:

- `build/verification/task-90-chatterbox-segmented-hemma/`

The segmented lane now records deterministic debug artifacts:

- `segmented/segment-debug/segment_plan.json`
- `segmented/segment-debug/chunk_01.wav`
- `segmented/segment-debug/chunk_02.wav`
- `segmented/segment-debug/chunk_03.wav`
- `segmented/segment-debug/stitched.wav`

Measured Task 90 result:

- single-pass lane succeeded
- segmented lane succeeded
- single-pass Swedish clone duration: `51.904` seconds
- segmented Swedish clone duration: `57.473` seconds
- single-pass peak VRAM: `5959815168` bytes
- segmented peak VRAM: `5742292992` bytes
- segmented plan used `3` deterministic text segments at `max_chars=160` with
  `cross_fade_ms=80`

Qualitative listening judgment is now recorded:

- segmented output is roughly equal overall but better than single-pass toward
  the end of longer passages
- the single-pass lane sounds more stressed later in the passage
- remaining defects are now localized to chunk boundaries:
  - noisy tails after speech stops
  - pauses that are too long because stitching is not yet speech-aware

Those remaining issues are intentionally deferred into `T91`.

## Acceptance Criteria

- [x] The sidecar contract remains text-based.
- [x] The repo records the exact segment plan used for each benchmark lane.
- [x] The segmented lane runs the same reference clip as the single-pass lane.
- [x] The segmented lane writes one final stitched artifact under
  `build/verification/`.
- [x] Optional chunk-level debug artifacts are deterministic when enabled.
- [x] The benchmark records whether segmented output is judged better, worse, or
  unchanged versus the single-pass baseline.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
