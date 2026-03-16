---
id: task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate
title: Launch the first clean base restart after the bounded stability gate
type: task
status: proposed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - restart
  - proof-gated
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Launch the first clean base restart only after Story 29 proves bounded
numerical stability through either the preferred `1500` gate or the fallback
`1470 + standalone eval` gate.

## PR Scope

- Block this task until either:
  - `T197` reaches step `1500` and completes the scheduled eval there, or
  - `T198` satisfies the fallback `1470 + standalone eval` gate
- Launch from `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, not from a legacy checkpoint.
- Use the winning mitigation contract from the proof phase.
- Use the canonical scheduled posture:
  - checkpoint every `500`
  - eval every `100`
  - retain newest `3`
- Record the restart result immediately in the training reference ledger.

## Deliverables

- [ ] One proof-gated clean restart launch record exists.
- [ ] One operator-facing ledger entry records which proof gate justified the
  restart.
- [ ] One restart acceptance record states whether step `100` eval completed
  without a non-finite guard event.

## Acceptance Criteria

- [ ] The task does not start before the preferred or fallback proof gate is
  explicitly satisfied in the training reference ledger.
- [ ] The first restart acceptance gate is completion of the first scheduled
  eval at step `100` without a non-finite guard event.
- [ ] Any new restart failure window is written back into the training
  reference ledger immediately rather than treated as an informal note.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
