---
id: task-231-pin-the-post-t219-bounded-fresh-start-promotion-contract-before-any-governed-proof
title: Pin the post-T219 bounded fresh-start promotion contract before any governed proof
type: task
status: proposed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-230-test-one-diagnosed-post-t219-micro-family-against-the-first-verified-layer16-sub-boundary.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - mechanism
  - promotion
  - governance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

If `T230` finds a local winner, freeze the exact bounded fresh-start
promotion contract before any governed proof launches. If `T230` finds no
winner, record that `T217` stays blocked and stop.

This task exists to keep the promotion ladder disciplined:
local gate -> bounded fresh-start promotion contract -> governed proof.

## PR Scope

- Activate only after `T230` closes.
- If `T230` found no local winner:
  - record that outcome explicitly
  - keep `T217` blocked
  - hand the lane to `T232`
- If `T230` found one local winner:
  - pin exactly one candidate and no fallback co-winner
  - declare the full Story 32 experiment spec for the bounded promotion run
  - freeze the early-window run bounds:
    - exact bundle root
    - exact candidate/stabilizer variant
    - max-step or max-iteration window
    - eval posture
    - stop rules
  - state exactly what the bounded run is allowed to answer
  - map the winner onto the existing `T217` governed fresh-start surface
    without widening it into a larger recovery proof
- Do not add a second candidate, extra bundle changes, or a broader recipe
  search in this task.

## Deliverables

- [ ] One exact bounded promotion contract is recorded for the post-`T219`
  local winner, or one explicit "no winner, keep `T217` blocked" result is
  recorded.
- [ ] One full Story 32 experiment-spec entry is prepared for the bounded
  promotion run.
- [ ] One explicit operator rule states whether `T217` may launch and under
  what exact bounded conditions.

## Acceptance Criteria

- [ ] The task promotes at most one local winner.
- [ ] The bounded contract is frozen before any governed proof launch.
- [ ] The task does not silently widen the bounded promotion run into a longer
  recovery proof.
- [ ] If there is no local winner, the task explicitly keeps `T217` blocked
  and routes the lane to `T232`.

## Validation

- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-train launch --help`
- [ ] `pdm run qwen-train status --help`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
