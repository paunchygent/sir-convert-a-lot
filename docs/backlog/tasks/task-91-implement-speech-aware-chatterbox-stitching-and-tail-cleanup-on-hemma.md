---
id: task-91-implement-speech-aware-chatterbox-stitching-and-tail-cleanup-on-hemma
title: Implement speech-aware Chatterbox stitching and tail cleanup on Hemma
type: task
status: proposed
priority: high
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
labels:
  - chatterbox
  - stitching
  - post-processing
  - speech-boundaries
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Improve segmented Chatterbox output quality on Hemma by making chunk stitching
aware of speech endings and pause intent, so tail noise is reduced without
collapsing the natural pauses between clauses and sentences.

## Problem Statement

Task 90 proved that segmented normal-text Chatterbox output is better overall
than the single-pass baseline, especially toward the end of longer passages.

The remaining quality defects are now narrower and specific to stitching:

- noise remains at some chunk tails after speech stops
- the current cross-fade is waveform-only, not speech-boundary-aware
- pauses between segments can become too long because stitching does not yet
  reason about end-of-speech versus intended pause duration

The repo therefore needs a second-stage stitching pass that operates on actual
tail behavior instead of treating every chunk boundary the same way.

## PR Scope

- Add one bounded tail-analysis stage for segmented Chatterbox chunks.
- Detect trailing low-energy or noise-only regions near chunk ends before
  stitching.
- Add one pause-aware stitching policy that distinguishes:
  - speech overlap candidates,
  - intended clause pauses,
  - intended sentence pauses.
- Trim or attenuate noisy tails before overlap decisions are applied.
- Keep the sidecar contract text-based and internal-only:
  - no new public request fields,
  - no model-specific API drift.
- Add deterministic debug evidence for each stitched lane:
  - pre-trim chunk artifacts,
  - post-trim chunk artifacts or metadata,
  - per-boundary stitch decisions,
  - final stitched artifact.
- Benchmark the current Task 90 stitcher versus the new speech-aware stitcher
  on Hemma using the same reference audio and longer Swedish probe text.

## Non-Goals

- do not redesign segmentation itself as part of this task
- do not add undocumented Chatterbox inference arguments
- do not treat phonetic respelling or phoneme preprocessing as solved by this
  stitching task

## Deliverables

- [ ] Tail-noise analysis and cleanup step for segmented chunks.
- [ ] Pause-aware stitcher that preserves needed natural pauses.
- [ ] Deterministic stitch-decision debug evidence per boundary.
- [ ] Hemma benchmark evidence comparing:
  - current Task 90 stitcher,
  - speech-aware stitcher.
- [ ] Runbook updates for the improved stitching path.

## Acceptance Criteria

- [ ] The segmented Chatterbox path remains text-based.
- [ ] The repo records what trim or attenuation decision was made at each chunk
  boundary.
- [ ] The improved stitcher reduces tail-noise artifacts at chunk ends in the
  benchmark evidence.
- [ ] The improved stitcher preserves intended natural pauses rather than
  flattening all boundaries into the same overlap rule.
- [ ] The Hemma benchmark records whether the speech-aware stitcher is judged
  better, worse, or unchanged versus the Task 90 baseline.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
