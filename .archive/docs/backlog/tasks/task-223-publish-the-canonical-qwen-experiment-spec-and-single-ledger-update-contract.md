---
id: task-223-publish-the-canonical-qwen-experiment-spec-and-single-ledger-update-contract
title: Publish the canonical Qwen experiment spec and single-ledger update contract
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
  - docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - .codex/rules/096-qwen-experiment-governance.md
labels:
  - qwen
  - finetuning
  - governance
  - ledger
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish one canonical Qwen experiment-spec contract and make the Task 101
progress reference the single live ledger for future active runs.

## PR Scope

- Define the required experiment-spec fields for future active runs:
  - `experiment_class`
  - `question_answered`
  - `surface_name`
  - `code_revision`
  - `image`
  - `bundle_root`
  - `sampler_or_batching_policy`
  - `seed_or_shuffle_policy`
  - `batch_size`
  - `gradient_accumulation_steps`
  - `text_embedding_assembly_mode`
  - `text_embedding_mask_policy`
  - `stabilizer_variant`
  - `max_steps`
  - `eval_policy`
  - `input_artifact_roots`
  - `expected_promotion_target`
  - `status`
  - `result_interpretation`
- Publish one per-run entry template in the live ledger using the exact field
  order above.
- Make the Task 101 progress reference the only live result ledger for active
  Qwen experiment work.
- Avoid legacy backfill; only classify old surfaces and require the template
  for future active runs.

## Deliverables

- [x] One canonical Qwen Experiment Spec contract exists in the live ledger.
- [x] One structured per-run entry template exists for future active runs.
- [x] The Task 101 progress reference is explicitly documented as the single
  live result ledger.

## Acceptance Criteria

- [x] The live ledger now distinguishes provenance, mechanism, and recovery at
  the top of the document.
- [x] The live ledger contains one active surface matrix.
- [x] The live ledger contains one explicit experiment-spec field contract.
- [x] The live ledger contains one reusable entry template that can be used for
  `T221`, Story 31 mechanism runs, and future governed recovery proofs.
- [x] Legacy surfaces are classified without requiring historical artifact
  backfill.

## Validation

- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Outcome

- The repo no longer needs a separate "results ledger" proposal; the existing
  Task 101 progress reference is now the normative live ledger.
- Future active runs must declare the full state vector before the repo treats
  them as evidence instead of "close enough" comparisons.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
