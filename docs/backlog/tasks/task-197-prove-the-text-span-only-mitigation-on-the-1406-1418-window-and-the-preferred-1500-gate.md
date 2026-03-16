---
id: task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate
title: Prove the text-span-only mitigation on the 1406-1418 window and the preferred 1500 gate
type: task
status: proposed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-195-land-an-explicit-task-101-text-embedding-mask-policy-and-text-span-only-mitigation.md
  - docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - proof
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the first bounded mitigation proof from `state-step-00001406` using
`text_embedding_mask_policy=text_span_only` and
`gradient_accumulation_steps=4`, then prove whether the structural fix alone is
enough to clear the old failure window and the preferred next review gate.

## PR Scope

- Reuse the canonical RCA checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
- First proof gate:
  - clear bounded replay `1406 -> 1418`
  - no non-finite guard event
- Preferred second proof gate:
  - continue the same mitigated lane to optimizer step `1500`
  - complete the scheduled eval at `1500`
- Record the full RCA delta and operator interpretation in the training
  reference ledger, whether the proof passes or fails.

## Deliverables

- [ ] One bounded replay artifact proves whether the mask-only mitigation
  clears the `1417` window.
- [ ] One bounded continuation or equivalent proof artifact proves whether the
  same mitigation reaches step `1500` and completes eval there.
- [ ] The training reference ledger records the proof outcome, the active mask
  policy, the active accumulation value, and the resulting operator decision.

## Acceptance Criteria

- [ ] The `1406 -> 1418` proof artifact is self-describing and records
  `text_embedding_mask_policy=text_span_only` with
  `gradient_accumulation_steps=4`.
- [ ] If the proof reaches `1500`, the step-`1500` eval result is written into
  the training reference ledger and treated as the preferred restart gate.
- [ ] If the proof fails before `1500`, the failure step and first bad surface
  are written into the training reference ledger and `T198` becomes the next
  active task.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
