---
id: task-97-align-f5-reference-duration-and-add-segmented-hemma-lane
title: Align F5 reference duration and add segmented Hemma lane
type: task
status: in_progress
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-85-benchmark-f5-tts-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-95-expose-f5-tuning-controls-and-exact-voice-tag-support-on-hemma.md
  - docs/backlog/tasks/task-94-extract-youtube-reference-audio-for-chatterbox-pipeline.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
labels:
  - tts
  - f5-tts
  - segmented
  - hemma
  - benchmark
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Reduce the rushed F5-TTS result risk by aligning the local wrapper with the
upstream reference-length guidance of approximately `12` seconds, rerun the
Christian Hedlund sample on Hemma with the corrected reference handling, and
then add a repo-owned segmented F5 lane for long-form comparison.

## PR Scope

- Change the repo-owned F5 wrapper so reference preparation no longer hard-caps
  at `10` seconds when upstream guidance allows roughly `12` seconds.
- Preserve the normalized ADR-0007 `/synthesize` contract while changing only
  the internal reference-preparation policy.
- Rerun the Christian Hedlund F5 sample on Hemma with the corrected reference
  handling and the current quality-first Task 85 settings.
- Add a repo-owned segmented F5 benchmark lane for long-form text:
  - bounded text planning,
  - deterministic chunk artifacts,
  - deterministic stitching,
  - no backend-native contract expansion.
- Reuse the existing repo-owned segmentation/stitching discipline where safe
  instead of introducing one-off ad hoc stitching code.

## Deliverables

- [ ] F5 wrapper reference preparation is aligned to approximately `12`
  seconds rather than the stricter local `10` second cap.
- [ ] One corrected single-pass Christian Hedlund Hemma evidence bundle exists
  after the reference-length change.
- [ ] One segmented F5 Hemma evidence bundle exists for the same reference and
  prompt family.
- [ ] Docs record whether the rushed delivery was improved more by reference
  alignment, segmentation, or neither.

## Acceptance Criteria

- [ ] The local F5 wrapper no longer truncates an `11.5` second approved
  reference clip before its paired exact transcript ends.
- [ ] The corrected Christian rerun is recorded under `build/verification/`
  with deterministic report and artifact paths.
- [ ] The segmented F5 lane writes deterministic chunk/stitch evidence and a
  final stitched WAV without changing the public sidecar contract.
- [ ] The resulting docs make a concrete recommendation on whether segmented
  F5 is worth keeping as a follow-up quality lane.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
