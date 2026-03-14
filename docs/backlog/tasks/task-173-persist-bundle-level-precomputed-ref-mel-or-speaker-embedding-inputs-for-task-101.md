---
id: task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101
title: Persist bundle-level precomputed ref-mel or speaker-embedding inputs for Task 101
type: task
status: proposed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-161-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-task-101-qwen-reference-mels.md
  - docs/backlog/tasks/task-164-persist-precomputed-task-101-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
labels:
  - qwen
  - training
  - preprocessing
  - throughput
  - artifacts
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Move Task 101 input preparation from per-row runtime compute to deterministic
bundle-level precomputed artifacts (`ref_mel` or equivalent speaker embeddings)
so training no longer burns host cycles on repeated reference preparation.

## Why This Exists

`T161` evidence showed runtime cache metrics effectively dead in practical lane
execution (`0/0/0`) and no saturation lift. Bundle-level materialization is now
the required follow-on, not optional tuning.

## PR Scope

- Extend the pilot-bundle contract to persist stable precomputed
  `ref_mel` (or speaker-embedding equivalent) artifacts per canonical speaker
  anchor.
- Extend manifest schema and validation to carry the new artifact references.
- Update in-container dataset/trainer path to load precomputed artifacts instead
  of computing mels in the hot `__getitem__` path.
- Preserve relocation safety and deterministic bundle ownership rules.
- Emit explicit artifact-version metadata in launch/report/status payloads.

## Non-Goals

- Do not redesign batching or codebook fusion in this task.
- Do not change checkpoint cadence or durable retention policy.
- Do not silently break compatibility for existing deterministic pilot bundles;
  any migration behavior must be explicit.

## Deliverables

- [ ] Bundle materialization persists precomputed reference input artifacts.
- [ ] Training manifest contract carries explicit precomputed artifact fields.
- [ ] Task 101 runtime consumes precomputed inputs in the training hot path.

## Acceptance Criteria

- [ ] Runtime `ref_mel` extraction no longer appears as a dominant hot-path
  operation in bounded profiling traces.
- [ ] Bounded Hemma run with precomputed inputs improves steady-state train GPU
  median over the `T161` cache-on baseline.
- [ ] Contracts and runbook docs remain explicit about artifact provenance and
  deterministic bundle ownership.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_ref_mel_cache.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_qwen_training_profiling.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma precomputed-input evidence written under `build/verification/`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
