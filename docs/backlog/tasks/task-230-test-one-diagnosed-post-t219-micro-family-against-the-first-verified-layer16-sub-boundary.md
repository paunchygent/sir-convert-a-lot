---
id: 'task-230-test-one-diagnosed-post-t219-micro-family-against-the-first-verified-layer16-sub-boundary'
title: 'Test one diagnosed post-T219 micro-family against the first verified layer16 sub-boundary'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-229-split-the-post-t219-layer16-handoff-seam-into-sub-boundary-probes.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - stabilization
  - follow-on
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Test one diagnosed micro-family only against the first verified post-`T219`
layer-16 sub-boundary so the repo learns whether one precise causal idea
extends the finite window, instead of launching another mixed stabilizer
sweep.

## PR Scope

- Activate only if `T229` identifies one target sub-boundary clearly enough to
  shape the next intervention family.
- Implement and compare only one causal idea:
  - if the earliest break is at the residual handoff, test only residual-side
    variants
  - if the earliest break is at the downstream normalization entry, test only
    pre-`input_layernorm` variants
- Expose at most:
  - `off`
  - two diagnosed micro-family variants
- Reuse the Story 31 lab and gate rather than building a separate proof stack.
- Keep all non-intervention factors fixed:
  - bundle root
  - selected rows
  - seed/shuffle
  - batch size and accumulation
  - assembly mode
  - mask policy
- Stop if the new family only relocates failure without improving the finite
  window or promotion margin.

## Deliverables

- [ ] One diagnosed micro-family is registered in the Story 31 lab.
- [ ] One compact result matrix compares `off` against at most two
  micro-family variants.
- [ ] One explicit outcome states whether a local winner exists for promotion
  work or whether the lane remains negative.

## Acceptance Criteria

- [ ] The task tests one diagnosed causal idea only; it does not mix residual,
  normalization, optimizer, and bundle changes in the same family.
- [ ] The task compares no more than two variants plus `off`.
- [ ] The result explicitly distinguishes:
  - no winner
  - one local winner with a longer finite window
  - one local winner that earns bounded promotion consideration
- [ ] `T217` remains blocked unless this task produces a clear local winner.

## Validation

- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-story31-stability-lab run --skip-build`
- [ ] `pdm run qwen-story31-stability-lab gate --output-root <lab-output-root>`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
