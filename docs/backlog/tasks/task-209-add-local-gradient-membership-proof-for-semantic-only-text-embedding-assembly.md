---
id: 'task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly'
title: 'Add local gradient-membership proof for semantic-only text embedding assembly'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/reviews/review-03-architect-review-of-post-task-101-qwen-stabilization-candidates-after-story-29.md
labels:
  - qwen
  - finetuning
  - architecture
  - proof
  - gradient
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add the smallest-signal local proof for Candidate 1 by demonstrating that only
semantic text token ids can ever contribute row membership to
`text_embedding.weight.grad`.

## PR Scope

- Build one synthetic batch/probe where semantic ids and scaffold ids are
  deliberately disjoint and easy to inspect.
- Add one minimal forward/backward proof that only semantic ids appear in the
  text-embedding gradient row set.
- Add the stronger poisoned-upstream variant when feasible so scaffold-position
  corruption still cannot leak into text-embedding parameter-row membership.
- Keep this task local-only; do not launch Hemma long runs until this proof is
  green.

## Deliverables

- [ ] One local gradient-membership proof exists for the semantic-only lane.
- [ ] The proof fails if scaffold ids can still appear in
  `text_embedding.weight.grad`.
- [ ] The proof is linked as the required gate before any new Hemma long proof.

## Acceptance Criteria

- [ ] The synthetic proof asserts that only semantic ids can appear in
  `text_embedding.weight.grad` row membership.
- [ ] A deliberately distinct scaffold-id set is shown not to enter the
  trainable text-embedding gradient row set.
- [ ] This proof becomes the first required validation after Candidate 1 code
  lands and before any new Hemma proof attempt.
- [ ] Docs validation and task indexing stay green.

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
