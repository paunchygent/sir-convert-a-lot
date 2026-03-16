---
id: task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails
title: Run the conditional accumulation ablation and fallback 1470 proof if 1500 still fails
type: task
status: proposed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - ablation
  - fallback
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the planned accumulation ablations only if the structural
`text_span_only` proof clears the old `1417` window but still fails before the
preferred `1500` gate, and use those ablations to decide whether the next
restart can be justified through the preferred or fallback stability proof.

## PR Scope

- Keep `text_embedding_mask_policy=text_span_only` fixed.
- Repeat the bounded proof sequence with:
  - `gradient_accumulation_steps=2`
  - then `gradient_accumulation_steps=1` if needed
- Prefer the same `1500` gate.
- If `1500` still cannot be cleared and no new design/runtime gap is found,
  use the fallback gate:
  - reach step `1470` cleanly from `1406`
  - mint a fallback checkpoint
  - run standalone held-out eval from that `1470` checkpoint
- Record whether the best-known fix is:
  - structural only
  - structural plus reduced accumulation

## Deliverables

- [ ] One side-by-side proof record exists for accumulation values `4`, `2`,
  and `1` as needed.
- [ ] If the preferred `1500` gate still fails, one fallback proof record
  exists for `1470 + standalone eval`.
- [ ] The training reference ledger states whether restart is allowed through
  the preferred gate or only through the fallback gate.

## Acceptance Criteria

- [ ] The task remains blocked unless `T197` clears `1418` but fails before
  `1500`.
- [ ] Each ablation artifact records both the active mask policy and the active
  accumulation value.
- [ ] If the fallback gate is used, the resulting `1470` checkpoint and
  standalone eval result are written into the training reference ledger before
  any restart is allowed.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
