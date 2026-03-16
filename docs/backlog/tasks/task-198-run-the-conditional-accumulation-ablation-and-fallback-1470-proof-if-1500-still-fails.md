---
id: task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails
title: Run the conditional accumulation ablation and fallback 1470 proof if 1500 still fails
type: task
status: in_progress
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma.md
  - docs/backlog/tasks/task-205-establish-idle-safe-recurring-hemma-scratch-maintenance.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - ablation
  - fallback
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the planned accumulation ablations after the structural
`text_span_only` proof shows that mask policy alone is insufficient, and use
those ablations to decide whether the next restart can be justified through
the preferred or fallback stability proof.

## PR Scope

- Keep `text_embedding_mask_policy=text_span_only` fixed.
- Start from the completed `T197` Hemma proof result under
  `task197-20260316t183555z-a1`, which failed again at optimizer step `1417`
  before the `1500` continuation could launch.
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

## Prepared Proof Surface

- Local deterministic artifact root:
  `build/verification/qwen-t198-proof/<proof-id>/`
- Canonical wrapper:
  `pdm run qwen-t198-proof`
- The first prepared lane in this task is the accumulation-`2` proof from the
  same canonical `1406` checkpoint used by `T197`.
- Wrapper-generated artifacts:
  - `proof-config.json`
  - `plan.md`
  - `checklist.md`
  - `window-launch.json`
  - `window-status.json`
  - `window-status.md`
  - `gate1500-launch.json`
  - `gate1500-status.json`
  - `gate1500-status.md`
- First prepared accumulation-`2` package:
  - proof id: `task198-20260316t185616z-accum2-a1`
  - local root:
    `build/verification/qwen-t198-proof/task198-20260316t185616z-accum2-a1/`
- First live accumulation-`2` outcome:
  - the bounded replay reached optimizer step `1418`
  - the replay did not fail on a non-finite gradient
  - it then failed during durable checkpoint save because Hemma scratch free
    space dropped below the required headroom
  - `1500` continuation therefore did not launch
  - `T204/T205` are the required enabling tasks before the clean rerun
- Clean rerun after `T204/T205`:
  - proof id: `task198-20260316t202541z-accum2-a2`
  - the bounded replay exited cleanly at optimizer step `1418`
  - the replay minted
    `state-step-00001418`
    under the window run root and completed one scheduled eval there
  - the preferred `1500` continuation then launched from that `1418`
    checkpoint and failed at optimizer step `1428`
  - the terminal failure shape remained the same optimizer-boundary class:
    - `trigger_reason=pre_clip_non_finite_gradients`
    - `first_non_finite_stage=pre_clip`
    - `first_non_finite_surface=text_embedding.weight.grad`
    - `current_train_iteration=852`
  - no new durable checkpoint beyond `1418` was written during that failed
    continuation
  - the fallback decision is intentionally still open:
    - either run the documented `1470 + standalone eval` gate
    - or run the next accumulation ablation if the story owner decides the
      preferred-gate miss still warrants it

## Exact Command Sequence

1. Prepare the accumulation-`2` proof package locally:
   `pdm run qwen-t198-proof prepare --proof-id <proof-id> --skip-build`
1. Launch the detached bounded replay:
   `pdm run qwen-t198-proof launch-window --proof-id <proof-id>`
1. Inspect the bounded replay:
   `pdm run qwen-t198-proof status-window --proof-id <proof-id>`
1. Launch the detached `1500` continuation only after the replay passes:
   `pdm run qwen-t198-proof launch-gate1500 --proof-id <proof-id>`
1. Inspect the detached `1500` continuation:
   `pdm run qwen-t198-proof status-gate1500 --proof-id <proof-id>`

## Deliverables

- [ ] One committed `qwen-t198-proof` wrapper prepares deterministic local
  proof artifacts and renders the exact detached Hemma commands/checklist for
  the accumulation-`2` lane.
- [ ] One side-by-side proof record exists for accumulation values `4`, `2`,
  and `1` as needed.
- [ ] If the preferred `1500` gate still fails, one fallback proof record
  exists for `1470 + standalone eval`.
- [ ] The training reference ledger states whether restart is allowed through
  the preferred gate or only through the fallback gate.

## Acceptance Criteria

- [ ] The task remains blocked unless `T197` has produced a truthful Hemma
  proof artifact showing that `text_span_only` alone did not satisfy the
  preferred gate.
- [ ] The task remains blocked for relaunch while `T204/T205` scratch-headroom
  remediation and recurring-maintenance setup are still open, or while the
  proof wrappers report insufficient Hemma free space.
- [ ] Each ablation artifact records both the active mask policy and the active
  accumulation value.
- [ ] If the fallback gate is used, the resulting `1470` checkpoint and
  standalone eval result are written into the training reference ledger before
  any restart is allowed.
- [ ] If the winning mitigation still includes `text_span_only`, the ledger
  records that `legacy_codec_span` must be removed before `T199` starts.

## Checklist

- [x] Prepare surface complete
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
