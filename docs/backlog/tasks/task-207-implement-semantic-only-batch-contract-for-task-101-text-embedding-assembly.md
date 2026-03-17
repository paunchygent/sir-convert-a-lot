---
id: task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly
title: Implement semantic-only batch contract for Task 101 text embedding assembly
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/reviews/review-03-architect-review-of-post-task-101-qwen-stabilization-candidates-after-story-29.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - architecture
  - semantic-only
  - batch-contract
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the current full-text-channel batch contract with one explicit semantic
text contract so the trainable text-embedding path no longer depends on a late
mask over scaffold positions.

## PR Scope

- Introduce typed batch fields that carry semantic text ids and their resolved
  collated positions explicitly.
- Preserve the existing no-projection Task 101 outer lane while changing the
  internal batch contract away from full-sequence text lookup semantics.
- Keep codec, attention, and reference-input surfaces coherent with the new
  semantic-only batch representation.
- Update focused dataset/collation tests to prove the semantic-only contract.
- Do not launch Hemma proofs in this task.

## Deliverables

- [x] One committed semantic-only batch contract exists for Task 101 collation.
- [x] Dataset/collation tests prove scaffold positions are not part of the
  trainable text-embedding input contract.
- [x] Downstream runtime consumers receive the new typed fields without
  fallback shims.

## Acceptance Criteria

- [x] The batch contract exposes semantic text ids and semantic positions as
  first-class fields.
- [x] The batch contract no longer requires downstream code to infer semantic
  membership from the full collated text channel plus a late mask.
- [x] Focused local tests prove semantic positions are structurally isolated in
  the batch output.
- [x] Docs validation and task indexing stay green.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_training_rows.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py -q`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_train_step_runtime.py tests/sir_convert_a_lot/ml/qwen/training/test_eval_runtime.py tests/sir_convert_a_lot/ml/qwen/training/test_training_rows.py -q`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training -q`
- [x] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Outcome

`T207` now emits semantic-only text fields directly from dataset collation:

- `semantic_text_ids`
- `semantic_text_positions`
- `semantic_text_mask`

These fields are now part of the enforced `BatchTensors` contract and are
produced natively in the collate step rather than inferred later from
`input_ids` plus `text_embedding_mask`.

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [x] Docs updated
