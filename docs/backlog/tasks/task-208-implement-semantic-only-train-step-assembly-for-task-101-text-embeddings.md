---
id: 'task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings'
title: 'Implement semantic-only train-step assembly for Task 101 text embeddings'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/reviews/review-03-architect-review-of-post-task-101-qwen-stabilization-candidates-after-story-29.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - architecture
  - semantic-only
  - train-step
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Change train/eval embedding assembly so only semantic text ids are passed
through the trainable text-embedding lookup, then assemble those semantic
embeddings into the final runtime inputs alongside codec and scaffold
surfaces.

## PR Scope

- Consume the semantic-only batch contract from `T207`.
- Remove the current full-collated-text lookup followed by late masking from
  the active Task 101 lane.
- Update train-step, eval, and any closely coupled reporting/forensics surfaces
  required by the new assembly contract.
- Keep the no-projection lane and avoid compatibility wrappers back to the old
  batch semantics.
- Do not run long Hemma proofs in this task.

## Deliverables

- [ ] Semantic-only train-step embedding assembly lands in the active Task 101
  lane.
- [ ] The old full-channel text-embedding lookup is removed from the live path.
- [ ] Focused local tests cover the new assembly shape.

## Acceptance Criteria

- [ ] Non-semantic scaffold positions no longer traverse the trainable
  `text_embedding(...)` lookup in the active lane.
- [ ] Train and eval code consume the semantic-only contract consistently.
- [ ] No legacy shim preserves the old full-channel lookup behavior.
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
