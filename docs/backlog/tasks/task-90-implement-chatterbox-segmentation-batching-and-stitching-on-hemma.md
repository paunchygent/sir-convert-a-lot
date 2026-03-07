---
id: 'task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma'
title: 'Implement Chatterbox segmentation batching and stitching on Hemma'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes.md
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

The current Chatterbox path is single-pass. It does not currently provide:

- sentence splitting
- prosodic-boundary detection
- chunk batching
- chunk stitching or cross-fade

That leaves the repo without a maximal-quality long-form synthesis path.

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

- [ ] Deterministic segmentation planner for longer Swedish text.
- [ ] Deterministic chunk execution path for Chatterbox.
- [ ] Deterministic stitcher with explicit evidence output.
- [ ] Hemma benchmark evidence comparing single-pass vs segmented output.
- [ ] Runbook updates for the new quality path.

## Acceptance Criteria

- [ ] The sidecar contract remains text-based.
- [ ] The repo records the exact segment plan used for each benchmark lane.
- [ ] The segmented lane runs the same reference clip as the single-pass lane.
- [ ] The segmented lane writes one final stitched artifact under
  `build/verification/`.
- [ ] Optional chunk-level debug artifacts are deterministic when enabled.
- [ ] The benchmark records whether segmented output is judged better, worse, or
  unchanged versus the single-pass baseline.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
