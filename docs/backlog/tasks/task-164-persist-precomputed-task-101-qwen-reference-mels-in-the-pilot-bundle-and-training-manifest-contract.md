---
id: task-164-persist-precomputed-task-101-qwen-reference-mels-in-the-pilot-bundle-and-training-manifest-contract
title: Persist precomputed Task 101 Qwen reference mels in the pilot bundle and training manifest contract
type: task
status: proposed
priority: medium
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-141-define-frozen-qwen-pilot-dataset-use-for-finetuning.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/backlog/tasks/task-161-add-ref-mel-caching-and-a-promotion-decision-for-precomputed-task-101-qwen-reference-mels.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
labels:
  - qwen
  - finetuning
  - ref-mel
  - bundle
  - manifests
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Expand the Task 101 pilot-bundle contract to include precomputed reference mels
only if the earlier cache-and-dataloader tasks still fail to meet the story’s
saturation target.

## Why This Exists

`T161` is the intentionally lower-risk first attempt to eliminate duplicate
`ref_mel` work. If cache-only optimization still leaves the steady-state GPU
busy below the story gate, the next coherent move is to precompute and persist
the reference mels in the deterministic pilot bundle rather than recomputing
them at runtime forever.

## PR Scope

- Extend the deterministic Task 101 pilot-bundle materialization path to write
  precomputed reference-mel artifacts for the stable canonical speaker refs.
- Extend the prepared-manifest or related training-row contract so the trainer
  can load precomputed mels when present.
- Keep legacy bundle compatibility explicit:
  - either via fallback runtime mel extraction,
  - or via a fail-closed contract bump that is clearly documented.
- Measure the storage impact and bundle-build cost of the new artifact family.

## Non-Goals

- Do not open this task before `T161` explicitly concludes that cache-only is
  insufficient.
- Do not broaden the bundle contract to unrelated feature tensors here.

## Deliverables

- [ ] Precomputed reference-mel artifact contract defined.
- [ ] Task 101 bundle builder writes the new artifacts.
- [ ] Task 101 trainer consumes precomputed mels when available.
- [ ] Storage-cost and throughput evidence are documented.

## Acceptance Criteria

- [ ] The task lands only if `T161` documented that cache-only is insufficient.
- [ ] The deterministic pilot-bundle contract remains reviewable and
  relocation-safe after the new artifact family is added.
- [ ] A bounded Hemma comparison shows that precomputed bundle-level mels
  materially improve throughput over runtime-only mel extraction.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma evidence records bundle-size cost and runtime gain.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
