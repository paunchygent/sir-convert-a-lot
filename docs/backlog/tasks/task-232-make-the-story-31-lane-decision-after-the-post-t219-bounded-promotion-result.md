---
id: task-232-make-the-story-31-lane-decision-after-the-post-t219-bounded-promotion-result
title: Make the Story 31 lane decision after the post-T219 bounded promotion result
type: task
status: proposed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-231-pin-the-post-t219-bounded-fresh-start-promotion-contract-before-any-governed-proof.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - governance
  - decision
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

After the bounded post-`T219` promotion result is known, make one truthful
Story 31 lane decision:

- promote to the next governed recovery proof,
- keep the lane in mechanism and open a new localized slice,
- or classify the attempted family as historical evidence only.

## PR Scope

- Consume exactly one bounded promotion outcome:
  - the explicit "no winner" conclusion from `T231`, or
  - the bounded fresh-start result executed through `T217`
- Update Story 31 operator truth without mixing in unrelated runs.
- Decide only one next state:
  - `T217` remains blocked and a new mechanism slice must be opened
  - `T217` completed bounded proof but did not justify broader recovery
  - `T217` justified the next governed recovery step and unblocked downstream
    work
- Record the decision in:
  - Story 31
  - `docs/backlog/current.md`
  - the Task 101 live ledger
- Do not launch new experiments from this task; this is an interpretation and
  routing task.

## Deliverables

- [ ] One explicit lane decision is recorded after the bounded post-`T219`
  promotion result.
- [ ] One updated operator-facing statement explains whether the next move is a
  new mechanism slice, a governed recovery proof, or historical-only
  classification.
- [ ] Story 31, `current.md`, and the Task 101 ledger agree on the same next
  step.

## Acceptance Criteria

- [ ] The decision cites one exact bounded promotion result instead of a mixed
  run family.
- [ ] The task does not make recovery claims from a local lab result alone.
- [ ] If the bounded result is negative, the task keeps the lane in mechanism
  and defines the next localized question.
- [ ] If the bounded result is positive, the task states exactly what broader
  recovery step is now justified.

## Validation

- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
