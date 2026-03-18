---
id: task-237-test-one-post-t236-micro-family-against-the-first-verified-dominant-sub-talker-outlier-seam
title: Test one post-T236 micro-family against the first verified dominant sub-talker outlier seam
type: task
status: proposed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-236-resolve-the-post-t235-line4-row-local-outlier-before-claiming-a-generic-layer15-output-seam.md
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

Test one micro-family only at the first verified dominant seam produced by
`T236`, so Story 31 can keep drilling toward a real fix without widening back
into another multi-cause stabilizer sweep.

## PR Scope

- Treat `T236` as the gating diagnosis:
  - do not start this task until `T236` resolves one dominant seam cleanly
  - the exact intervention family must be chosen by the `T236` result
- Keep the Story 32 state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same strongest T234 member unless `T236` truthfully proves a different
    fixed baseline is required
- Compare baseline plus at most two strength levels in one micro-family only.
- Target only the exact dominant seam verified by `T236`.
- Do not mix in optimizer, bundle, sampler, or recovery changes.
- Stop if the family only relocates failure without extending the finite
  window.

## Interpretation Contract

- If one member clearly extends the finite window without merely moving the
  first failure to an adjacent seam, that member becomes the only candidate
  eligible for a later bounded promotion gate.
- If the family fails or only relocates failure, close it negative and keep
  Story 31 in mechanism.
- `T217` remains blocked unless a later promotion gate is actually earned.

## Deliverables

- [ ] One diagnosed post-`T236` micro-family is implemented and compared.
- [ ] One compact result matrix records baseline plus at most two strengths.
- [ ] One explicit outcome states whether any candidate qualifies for a later
  promotion gate.

## Acceptance Criteria

- [ ] The task tests one diagnosed causal idea only.
- [ ] The task compares no more than baseline plus two strengths.
- [ ] The output distinguishes a real local winner from a simple failure
  relocation.

## Validation

- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
