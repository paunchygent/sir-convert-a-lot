---
id: task-93-implement-clause-aware-duration-bounded-chatterbox-chunk-planning-on-hemma
title: Implement clause-aware duration-bounded Chatterbox chunk planning on Hemma
type: task
status: completed
priority: high
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-90-implement-chatterbox-segmentation-batching-and-stitching-on-hemma.md
  - docs/backlog/tasks/task-91-implement-speech-aware-chatterbox-stitching-and-tail-cleanup-on-hemma.md
  - docs/backlog/tasks/task-92-promote-chatterbox-sidecar-to-hemma-production-candidate-and-mark-experimental-sidecars-explicitly.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
labels:
  - chatterbox
  - segmentation
  - swedish
  - prosody
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the current sentence-packing Chatterbox segment planner with a
clause-aware, list-item-aware, duration-bounded planner that produces smaller,
more stable chunks for Swedish long-form synthesis on Hemma.

## PR Scope

- Redesign the internal segment planner in the repo-owned Chatterbox path.
- Treat structural list-item boundaries as preferred split points.
- Prefer clause-sized planning units instead of packing whole sentences until a
  large character budget is exhausted.
- Add duration-aware planning heuristics so chunking targets:
  - average chunk duration around `4-6` seconds,
  - a hard planning ceiling of `9` seconds per chunk.
- Keep `segment_max_chars` as a secondary safety rail rather than the primary
  planning policy.
- Preserve deterministic debug evidence so each emitted segment plan is
  reviewable.
- Add local tests that cover:
  - numbered or rhetorical list items,
  - oversized clauses,
  - hard-cap enforcement,
  - intro-plus-first-item packing,
  - non-list fallback behavior.

## Non-Goals

- Do not change the public sidecar request contract.
- Do not redesign speech-aware stitching in this task.
- Do not add phoneme or eSpeak preprocessing back into the active Chatterbox
  path.
- Do not tune undocumented Chatterbox inference parameters.

## Deliverables

- [x] Clause-aware duration-bounded segment planner in the Chatterbox sidecar.
- [x] Deterministic tests for list-aware and hard-cap chunk planning.
- [x] Updated runbook guidance describing the new planner rules.
- [x] Hemma-ready behavior benchmarked against the current Task 92 text shape
  without ad hoc scripting.

## Implementation Notes

The planner redesign is now implemented locally in:

- `scripts/sir_convert_a_lot/tts_sidecar/chatterbox_segmented_generation.py`

The old planner packed whole sentences until a large character budget was
exhausted. The new planner now:

- derives clause-aware planning units before word fallback,
- treats explicit list-item markers as preferred split boundaries,
- estimates segment duration from text length and word count,
- targets `4-6` second chunks on average,
- enforces a hard planning ceiling of `9` seconds per chunk,
- keeps `segment_max_chars` as a secondary safety rail,
- records planner metadata in `segment_plan.json`.

The local test slice now covers:

- list-aware chunk planning,
- oversized list-item splitting,
- sentence and clause fallback behavior,
- segmented debug artifact writing,
- existing Task 90 / Task 91 / Task 86 compatibility surfaces.

## Acceptance Criteria

- [x] The planner treats list-item boundaries as preferred split points instead
  of merging many items into one oversized segment.
- [x] The planner targets smaller chunks in the `4-6` second band on average
  for long-form Swedish instructional text.
- [x] The planner enforces a hard planning ceiling of `9` seconds per chunk by
  splitting oversized units further on clause boundaries or fallback word
  boundaries.
- [x] The planner remains deterministic and produces reviewable debug evidence.
- [x] Local tests cover list-aware planning, oversized unit fallback, and
  duration-bound packing behavior.

## Validation

Local validation completed:

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_tts_sidecar_chatterbox_segmented_generation.py tests/sir_convert_a_lot/test_task90_chatterbox_segmented_experiment.py tests/sir_convert_a_lot/test_task91_chatterbox_speech_aware_stitching_experiment.py tests/sir_convert_a_lot/test_task86_chatterbox_benchmark.py`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

Live Hemma evidence now exists under:

- `build/verification/task-93-chatterbox-delegates-text/`

Primary artifacts:

- clone output:
  `build/verification/task-93-chatterbox-delegates-text/artifacts/scenario-a-sv-ref-sv-out.wav`
- summary:
  `build/verification/task-93-chatterbox-delegates-text/report.json`
- segment plan:
  `build/verification/task-93-chatterbox-delegates-text/segment-debug/segment_plan.json`
- chunk analysis:
  `build/verification/task-93-chatterbox-delegates-text/segment-debug/chunk_analysis.json`

Measured result on the delegate-text lane:

- old planner baseline for the same text had a `19.92` second first chunk
- new planner emitted `7` chunks
- predicted chunk durations ranged from `1.613` to `4.636` seconds
- actual raw chunk durations ranged from `3.6` to `5.36` seconds
- average raw chunk duration was approximately `4.5` seconds
- no chunk exceeded the `9` second planning ceiling

The new plan kept the list structure explicit:

- intro plus item one
- item two
- item three
- item four
- item five
- item six
- closing narration

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
