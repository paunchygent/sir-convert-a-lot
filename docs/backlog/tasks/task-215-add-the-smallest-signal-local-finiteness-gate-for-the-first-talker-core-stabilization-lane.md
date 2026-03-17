---
id: task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane
title: Add the smallest-signal local finiteness gate for the first talker-core stabilization lane
type: task
status: proposed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - stabilization
  - local-gate
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add the smallest-signal local gate for the first talker-core stabilization
lane so we can test whether the new recipe actually removes the immediate
fresh-start non-finite family before we spend Hemma time on another long proof.

This task is the promotion boundary between the Story 31 exploration lane and
the governed proof lane.

## PR Scope

- Reuse the exact fresh-start failure family already established by
  `T211-T214`:
  - same Candidate 1 clean semantics baseline
  - same row pair lineage where useful
  - same branch order:
    `main_loss`, `sub_talker_loss`, `combined_loss`
- Validate the first stabilization surface from `T216`, not the old lane.
- Reuse the Story 31 exploration surface instead of building another bespoke
  test-only harness.
- Keep the gate as small and causal as possible:
  - one forward/backward window
  - no optimizer step required unless explicitly justified
  - prove whether the previously failing surface now stays finite locally
- Require the gate to inspect the exact surfaces that mattered in the latest
  RCA:
  - `talker_core.layer_16.mlp.gated_product`
  - `talker_core.layer_15.output`
  - `input_text_embedding.grad`
  - `text_embedding.weight.grad`
- Do not let this task grow into another generic discovery suite.
- Define explicit promotion criteria:
  - exact failing branch surfaces stay finite
  - the stabilized lane preserves the clean text-semantics contract
  - if a short 1-2 step local run is included, it stays finite too
- Require matrix results to be recorded in one compact table rather than one
  task or proof package per experimental cell.

## Deliverables

- [ ] One committed local finiteness gate exists for the first talker-core
  stabilization lane.
- [ ] One focused test/probe artifact states whether the stabilization surface
  keeps the previously failing branches finite.
- [ ] One compact promotion rule is documented for moving from exploration to
  governed proof.
- [ ] One doc update records the gate as mandatory before the next Hemma proof.

## Acceptance Criteria

- [ ] The gate fails on the pre-stabilization behavior and passes only on the
  new stabilization surface.
- [ ] The gate checks the exact fresh-start failure family rather than a looser
  synthetic proxy only.
- [ ] The gate is fast enough to become the first required local acceptance
  step before `T217`.
- [ ] The gate and result table make it unnecessary to create a new backlog
  task for each micro-experiment.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training -q`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
