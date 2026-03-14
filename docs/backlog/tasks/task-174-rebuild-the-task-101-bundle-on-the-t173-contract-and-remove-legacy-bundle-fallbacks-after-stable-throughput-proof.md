---
id: task-174-rebuild-the-task-101-bundle-on-the-t173-contract-and-remove-legacy-bundle-fallbacks-after-stable-throughput-proof
title: Rebuild the Task 101 bundle on the T173 contract and remove legacy-bundle fallbacks after stable throughput proof
type: task
status: proposed
priority: high
created: '2026-03-14'
last_updated: '2026-03-14'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-172-increase-task-101-per-launch-gpu-work-via-bucketed-batching-and-vectorized-codebook-fusion.md
  - docs/backlog/tasks/task-173-persist-bundle-level-precomputed-ref-mel-or-speaker-embedding-inputs-for-task-101.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - training
  - throughput
  - bundle
  - cleanup
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Rebuild the canonical Task 101 bundle on the persisted `T173` precomputed-ref
input contract and then remove the temporary legacy-bundle compatibility trees
that were kept only to unblock live `T172` throughput validation.

## Why This Exists

The current training lane contains temporary legacy-bundle fallback logic so we
can validate `T171` and `T172` against the already-materialized Hemma bundle
without paying an immediate training reset cost. That fallback must not become
permanent architecture.

This cleanup is only justified after we have strong evidence that the tuned
throughput profiles produce a real, durable gain on Hemma.

## Entry Criteria

- `T172` throughput-profile tuning is complete.
- Real Hemma evidence shows improved throughput/GPU utilization versus the
  pre-`T172` baseline.
- The improved behavior is stable for at least `24` hours of training evidence,
  not just one short profiling window.
- The team has chosen the canonical post-`T172` launch profile from evidence.

## PR Scope

- Rebuild the canonical Task 101 bundle on Hemma with the `T173` persisted
  precomputed-reference-input contract.
- Verify the rebuilt bundle exposes canonical
  `training_bundle_report.json` metadata and per-row
  `precomputed_ref_input_*` fields.
- Remove the temporary legacy-bundle launch and dataset fallback branches that
  allow old bundles without `T173` metadata to launch.
- Remove any temporary legacy-oriented `if` trees that only exist to bridge the
  old bundle contract.
- Update runbooks and backlog docs so operators rebuild the bundle before new
  long-run training launches.

## Non-Goals

- Do not retune throughput profiles in this task.
- Do not change the chosen post-`T172` default profile unless the rebuild
  itself exposes a regression.
- Do not accept cleanup-only completion without a real rebuilt Hemma bundle.

## Deliverables

- [ ] One rebuilt canonical Task 101 bundle exists on Hemma under the `T173`
  contract.
- [ ] Legacy-bundle fallback branches are removed from the training launch and
  dataset path.
- [ ] Docs and operator surfaces point to the rebuilt-bundle path only.

## Acceptance Criteria

- [ ] A real Hemma run launched from the rebuilt bundle succeeds without any
  legacy-bundle fallback logic.
- [ ] The rebuilt-bundle run preserves the post-`T172` throughput gain for at
  least `24` hours of observed training.
- [ ] The repo no longer contains temporary legacy-bundle compatibility trees
  introduced only to bridge pre-`T173` bundles.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root <focused-paths>`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Real Hemma rebuilt-bundle evidence is written under `build/verification/`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
