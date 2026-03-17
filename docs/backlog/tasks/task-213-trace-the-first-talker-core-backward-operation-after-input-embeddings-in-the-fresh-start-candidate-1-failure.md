---
id: 'task-213-trace-the-first-talker-core-backward-operation-after-input-embeddings-in-the-fresh-start-candidate-1-failure'
title: 'Trace the first talker-core backward operation after input embeddings in the fresh-start Candidate 1 failure'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-212-run-a-single-step-backward-lineage-probe-for-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - candidate-1
  - rca
  - hemma
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Trace the first talker-core backward operation between still-finite
`hidden_states` gradients and newly non-finite `input_embeddings` gradients in
the fresh-start Candidate 1 failure, so the repo can identify the missing
talker-core puzzle piece before making any Candidate `3` implementation move.

## PR Scope

- Treat `T212` as closed truth:
  - the truthful fresh-start backward-lineage probe was
    `task212-20260317t141500z-lineage-a3`
  - both isolated rows failed independently
  - all three loss branches failed
  - `hidden_states` and `talker_hidden_states` gradients stayed finite first
  - `input_embeddings` was the earliest currently instrumented non-finite
    backward hook
- Build one committed talker-core probe surface that:
  - reuses the exact `T212` fresh-start row pair:
    manifest lines `13` and `4`
  - reuses the same probe order:
    `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation
  - instruments the talker-core path between `input_embeddings` and the first
    still-finite hidden-state surfaces
  - identifies the first talker-core backward op or tensor family that turns
    non-finite before the additive input branches inherit that corruption
- Keep the probe detached and committed on Hemma; do not debug through inline
  shell payloads or ad hoc notebooks.
- Do not reopen replay framing in this task.
- Do not open Candidate `3` implementation work until this talker-core trace
  either identifies the decisive missing piece or clearly proves the probe no
  longer yields additional causal signal.

## Deliverables

- [ ] One committed talker-core backward probe surface exists for the exact
  fresh-start row pair from `T212`.
- [ ] One truthful Hemma probe result identifies the earliest non-finite
  talker-core backward op or tensor family between `hidden_states` and
  `input_embeddings`.
- [ ] One operator-facing decision record states whether Candidate `3` should
  now open immediately or whether another smaller causal split is still more
  truthful.

## Acceptance Criteria

- [ ] The probe does not resume from any legacy Task 101 checkpoint.
- [ ] The probe keeps the exact `T212` row pair and branch order unless a
  smaller probe is explicitly documented as more decisive.
- [ ] The result localizes corruption more precisely than:
  `input_embeddings` non-finite / `input_text_embedding.grad` first RCA
  surface / `text_embedding.weight.grad` first parameter surface.
- [ ] The runtime surface uses committed repo commands and detached Hemma
  execution rather than inline remote shell logic.
- [ ] The result is recorded in the active task, `current.md`, and the Task
  101 reference ledger before any Candidate `3` implementation slice starts.

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
