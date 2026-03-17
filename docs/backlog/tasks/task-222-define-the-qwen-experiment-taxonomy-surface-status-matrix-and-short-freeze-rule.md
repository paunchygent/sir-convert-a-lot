---
id: task-222-define-the-qwen-experiment-taxonomy-surface-status-matrix-and-short-freeze-rule
title: Define the Qwen experiment taxonomy, surface-status matrix, and short freeze rule
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - .agents/rules/096-qwen-experiment-governance.md
labels:
  - qwen
  - finetuning
  - governance
  - taxonomy
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the experiment classes, surface-status matrix, and temporary launch
freeze that let the repo separate provenance, mechanism, and recovery work
before any further inference is drawn from the current Qwen surfaces.

## PR Scope

- Define the three experiment classes:
  - `provenance`
  - `mechanism`
  - `recovery`
- Define the one-question-per-run rule for future active Qwen experiments.
- Publish one explicit status matrix for the current public surfaces:
  - `qwen-t221-historical-control`
  - `qwen-story31-stability-lab`
  - governed `qwen-train launch/status` recovery proof
  - `qwen-story30-freshstart-proof`
  - `qwen-story30-backward-lineage`
  - `qwen-t197-proof`
  - `qwen-t198-proof`
- Record the Story 32 freeze posture:
  - do not start new Story 31 variants or governed recovery proofs while the
    package lands
  - keep the already-running `T221` provenance surface alive
- Publish the taxonomy in the backlog, rule surface, runbook, and live ledger.

## Deliverables

- [x] One explicit experiment taxonomy exists for Qwen Task 101 work.
- [x] One active surface matrix maps each public surface to a class and status.
- [x] One short freeze rule is recorded for the Story 32 landing slice.
- [x] Story 31 and the live ledger are updated to use the matrix.

## Acceptance Criteria

- [x] `qwen-t221-historical-control` is documented as
  `provenance` / `active`.
- [x] `qwen-story31-stability-lab` is documented as
  `mechanism` / `active`.
- [x] The governed `qwen-train` proof lane is documented as
  `recovery` / `active but blocked until promotion`.
- [x] `qwen-story30-freshstart-proof` and
  `qwen-story30-backward-lineage` are documented as `legacy-readonly`.
- [x] `qwen-t197-proof` and `qwen-t198-proof` are documented as `deprecated`
  for new work and preserved as historical Story 29 evidence.
- [x] No new launch was introduced while landing the taxonomy package.

## Validation

- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Outcome

- The repo now has a single active surface matrix that answers
  "what question does this surface answer?" before "what command does it run?"
- `T221` is explicitly treated as provenance-only evidence while unresolved.
- Story 31 is no longer described as a generic proof lane; it is the
  mechanism owner, with recovery still blocked behind promotion.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
