---
id: task-97-align-f5-reference-duration-and-add-segmented-hemma-lane
title: Align F5 reference duration and add segmented Hemma lane
type: task
status: completed
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

- [x] F5 wrapper reference preparation is aligned to approximately `12`
  seconds rather than the stricter local `10` second cap.
- [x] One corrected single-pass Christian Hedlund Hemma evidence bundle exists
  after the reference-length change.
- [x] One segmented F5 Hemma evidence bundle exists for the same reference and
  prompt family.
- [x] Docs record whether the rushed delivery was improved more by reference
  alignment, segmentation, or neither.

## Acceptance Criteria

- [x] The local F5 wrapper no longer truncates an `11.5` second approved
  reference clip before its paired exact transcript ends.
- [x] The corrected Christian rerun is recorded under `build/verification/`
  with deterministic report and artifact paths.
- [x] The segmented F5 lane writes deterministic chunk/stitch evidence and a
  final stitched WAV without changing the public sidecar contract.
- [x] The resulting docs make a concrete recommendation on whether segmented
  F5 is worth keeping as a follow-up quality lane.

## Current Evidence

- The local F5 wrapper now accepts a bounded configurable reference-prep limit
  and defaults it to `12.0` seconds, so the approved `11.5` second Christian
  Hedlund reference clip is no longer truncated before its paired transcript
  ends.
- The corrected single-pass Hemma rerun exists under:
  - `build/verification/task-97-f5-reference-12s-hemma/`
  - `run_id=20260308T015946Z`
  - `repo_head=e3a3a83be2656f2ad1bae46dad83a59fcbc5c1dc`
  - rebuilt image:
    `sha256:f2161b09aefd1b000b4a6c8476e334784dd00ce9f7d5a7101259e458a53eafab`
  - synthesized artifact:
    `build/verification/task-97-f5-reference-12s-hemma/artifacts/sample_sv.wav`
  - artifact SHA256:
    `46c31cbb6f8eb685d64a321afde81e5387c60fed444d6d9ba2e71d91bf9f9ab7`
  - synthesized duration:
    `18.538` seconds
- The earlier Christian quality-first run from `T95` was only `16.266`
  seconds long, so the corrected `12.0` second reference handling appears to
  be the main reason the new sample is less rushed.
- The new segmented Hemma lane exists under:
  - `build/verification/task-97-f5-segmented-hemma/`
  - `run_id=20260308T020119Z`
  - `repo_head=e3a3a83be2656f2ad1bae46dad83a59fcbc5c1dc`
  - reused image:
    `sha256:f2161b09aefd1b000b4a6c8476e334784dd00ce9f7d5a7101259e458a53eafab`
  - synthesized artifact:
    `build/verification/task-97-f5-segmented-hemma/artifacts/sample_sv.wav`
  - artifact SHA256:
    `12255eb80ab66b897425b00c09ab8feb87243e7e1008afacdcc25d7e14307b01`
  - synthesized duration:
    `18.362` seconds
  - deterministic segmentation evidence:
    - `segment_count=4`
    - `segment-debug/segment_plan.json`
    - `segment-debug/chunk_analysis.json`
    - `segment-debug/boundary_decisions.json`
    - `segment-debug/stitched.wav`
- The segmented planner used four sentence-bounded chunks at
  `max_chars=160`, `cross_fade_ms=80`, and `stitch_mode=simple`.
- Recommendation:
  - keep the segmented F5 lane as a benchmark/debug comparison surface,
  - do not make it the default F5 path yet,
  - the measured pace improvement came primarily from fixing the reference
    duration mismatch, while segmentation produced a very similar final sample
    length and therefore does not yet justify default-path complexity by
    itself.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
