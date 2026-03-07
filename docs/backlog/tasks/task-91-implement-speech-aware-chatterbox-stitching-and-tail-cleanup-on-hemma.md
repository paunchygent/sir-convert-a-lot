---
id: task-91-implement-speech-aware-chatterbox-stitching-and-tail-cleanup-on-hemma
title: Implement speech-aware Chatterbox stitching and tail cleanup on Hemma
type: task
status: in_progress
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

- [x] Tail-noise analysis and cleanup step for segmented chunks.
- [x] Pause-aware stitcher that preserves needed natural pauses.
- [x] Deterministic stitch-decision debug evidence per boundary.
- [x] Hemma benchmark evidence comparing:
  - current Task 90 stitcher,
  - speech-aware stitcher.
- [x] Runbook updates for the improved stitching path.

## Implementation Notes

Task 91 is now implemented in the repo-owned Chatterbox segmented path:

- `scripts/sir_convert_a_lot/tts_sidecar/chatterbox_segmented_generation.py`
- `scripts/sir_convert_a_lot/tts_sidecar/chatterbox_runtime.py`
- `scripts/sir_convert_a_lot/devops/run_task91_hemma_chatterbox_speech_aware_stitching_experiment.py`
- `scripts/sir_convert_a_lot/devops/run_task91_chatterbox_speech_aware_stitching_experiment.py`

The new stitch mode is internal-only and does not change the public sidecar
request contract. The benchmark/runtime surface now supports:

- `segment_stitch_mode=simple`
- `segment_stitch_mode=speech_aware`

The speech-aware stitcher now adds:

- low-energy edge trimming per chunk
- short edge fades after trimming
- boundary classification from the preceding chunk text
- pause targets that differ for clause and sentence boundaries
- deterministic debug evidence for chunk analysis and boundary decisions

## Hemma Evidence

Live Hemma evidence now exists under:

- `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/`

Primary artifacts:

- simple stitch lane:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/simple/artifacts/scenario-a-sv-ref-sv-out.wav`
- speech-aware stitch lane:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/speech_aware/artifacts/scenario-a-sv-ref-sv-out.wav`
- summary:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/report.json`
- speech-aware chunk analysis:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/speech_aware/segment-debug/chunk_analysis.json`
- speech-aware boundary decisions:
  `build/verification/task-91-chatterbox-speech-aware-stitching-hemma/speech_aware/segment-debug/boundary_decisions.json`

Measured result:

- simple segmented lane:
  - `synthesized_ok=true`
  - duration `123.426` seconds
  - peak VRAM `6239154176` bytes
- speech-aware segmented lane:
  - `synthesized_ok=true`
  - duration `94.954` seconds
  - peak VRAM `5945778176` bytes
- speech-aware boundary decisions recorded:
  - boundary `1`: sentence pause `180 ms`, previous tail trim `500 ms`, next leading trim `120 ms`
  - boundary `2`: sentence pause `180 ms`, previous tail trim `500 ms`, next leading trim `200 ms`

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

Current acceptance status:

- text-based contract: satisfied
- trim and boundary decisions recorded: satisfied
- live Hemma benchmark completed: satisfied
- qualitative verdict from listening review: still pending

## Validation

Local validation completed:

- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_chatterbox_segmented_generation.py tests/sir_convert_a_lot/test_tts_sidecar_chatterbox_adapter.py tests/sir_convert_a_lot/test_task86_chatterbox_benchmark.py tests/sir_convert_a_lot/test_task90_chatterbox_segmented_experiment.py tests/sir_convert_a_lot/test_task91_chatterbox_speech_aware_stitching_experiment.py`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
