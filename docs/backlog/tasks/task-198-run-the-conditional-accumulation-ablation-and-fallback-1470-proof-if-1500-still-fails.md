---
id: task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails
title: Run the conditional accumulation ablation and fallback 1470 proof if 1500 still fails
type: task
status: completed
priority: high
created: '2026-03-16'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma.md
  - docs/backlog/tasks/task-205-establish-idle-safe-recurring-hemma-scratch-maintenance.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
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
  `build/verification/qwen-fallback-accumulation-proof/<proof-id>/`
- Canonical wrapper:
  `pdm run qwen-fallback-accumulation-proof`
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
  - `fallback1470-launch.json`
  - `fallback1470-status.json`
  - `fallback1470-status.md`
  - `fallback-eval-launch.json`
  - `fallback-eval-status.json`
  - `fallback-eval-status.md`
- First prepared accumulation-`2` package:
  - proof id: `task198-20260316t185616z-accum2-a1`
  - local root:
    `build/verification/qwen-fallback-accumulation-proof/task198-20260316t185616z-accum2-a1/`
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
- Focused next lane after the failed preferred gate:
  - use the existing `qwen-fallback-accumulation-proof` surface again
  - keep `text_embedding_mask_policy=text_span_only`
  - lower `gradient_accumulation_steps` from `2` to `1`
  - attempt the preferred gate again before the fallback gate is activated
  - keep the fallback `1470 + standalone eval` gate as the immediate next
    contingency if accumulation `1` still does not clear the preferred lane
  - prepared proof id:
    `task198-20260316t213409z-accum1-a1`
  - local root:
    `build/verification/qwen-fallback-accumulation-proof/task198-20260316t213409z-accum1-a1/`
  - bounded replay outcome:
    - the detached `1406 -> 1418` replay exited cleanly with `exit_code=0`
    - `current_optimizer_step=1418`
    - one scheduled eval completed there with
      `latest_eval_loss=8.293148636817932`
    - durable checkpoint
      `state-step-00001418`
      exists under the window run root
  - preferred `1500` continuation outcome:
    - the continuation launched directly from that clean `1418` checkpoint
    - the detached continuation exited with `exit_code=1`
    - `current_optimizer_step=1449`
    - `current_train_iteration=851`
    - no newer durable checkpoint beyond `1418` was minted
  - exact failure shape:
    - `trigger_reason=pre_clip_non_finite_gradients`
    - `first_non_finite_stage=pre_clip`
    - `first_non_finite_surface=text_embedding.weight.grad`
    - `first_non_finite_tensor=grad_norm`
    - `optimizer_step_attempted=false`
    - `optimizer_step_completed=false`
    - parameters and optimizer-state probes remained finite before the
      attempted optimizer step
    - `microbatch_count=1` at the failing optimizer step
  - operator interpretation:
    - accumulation `1` improved the preferred-gate reach from `1428` to `1449`
    - accumulation `1` still did not satisfy the preferred `1500` gate
    - the documented fallback `1470 + standalone eval` gate is now the
      strongest next governed lane unless a new design reason argues otherwise
- committed fallback surface:
  - `qwen-fallback-accumulation-proof` now exposes the fallback commands directly:
    - `launch-fallback1470`
    - `status-fallback1470`
    - `launch-fallback-eval`
    - `status-fallback-eval`
  - the fallback replay is a direct bounded `1406 -> 1470`
    `diagnose-non-finite` run from the canonical RCA checkpoint
  - the fallback standalone eval launches through the detached Hemma helper
    `qwen-fallback-eval-detached` so the eval result no longer depends on an
    attached local session
  - live fallback outcome:
    - proof id:
      `task198-20260317t062816z-fallback1470-a1`
    - the direct bounded fallback replay exited with `exit_code=1`
    - `current_optimizer_step=1449`
    - `current_train_iteration=851`
    - the same optimizer-boundary class remained:
      - `trigger_reason=pre_clip_non_finite_gradients`
      - `first_non_finite_stage=pre_clip`
      - `first_non_finite_surface=text_embedding.weight.grad`
    - no truthful `1470` checkpoint was minted
    - detached fallback standalone eval was therefore not launched
  - operator conclusion:
    - the planned Story 29 replay family is exhausted on the current code path
    - `T198` is terminal negative evidence, not the next active lane
    - `T206` is now the next active task:
      prove the true text-token span contract and define the final post-fix
      restart rule

## Exact Command Sequence

1. Prepare the accumulation-`2` proof package locally:
   `pdm run qwen-fallback-accumulation-proof prepare --proof-id <proof-id> --skip-build`
1. Launch the detached bounded replay:
   `pdm run qwen-fallback-accumulation-proof launch-window --proof-id <proof-id>`
1. Inspect the bounded replay:
   `pdm run qwen-fallback-accumulation-proof status-window --proof-id <proof-id>`
1. Launch the detached `1500` continuation only after the replay passes:
   `pdm run qwen-fallback-accumulation-proof launch-gate1500 --proof-id <proof-id>`
1. Inspect the detached `1500` continuation:
   `pdm run qwen-fallback-accumulation-proof status-gate1500 --proof-id <proof-id>`
1. For the next focused ablation lane, prepare accumulation `1` explicitly:
   `pdm run qwen-fallback-accumulation-proof prepare --proof-id <proof-id> --gradient-accumulation-steps 1 --skip-build`
1. If the preferred gate still fails after the planned accumulation ladder,
   launch the direct fallback replay:
   `pdm run qwen-fallback-accumulation-proof launch-fallback1470 --proof-id <proof-id>`
1. Inspect the direct fallback replay:
   `pdm run qwen-fallback-accumulation-proof status-fallback1470 --proof-id <proof-id>`
1. Launch detached standalone eval only after the fallback replay exits
   cleanly with a truthful `1470` checkpoint:
   `pdm run qwen-fallback-accumulation-proof launch-fallback-eval --proof-id <proof-id>`
1. Inspect the detached fallback eval:
   `pdm run qwen-fallback-accumulation-proof status-fallback-eval --proof-id <proof-id>`

## Deliverables

- [x] One committed `qwen-fallback-accumulation-proof` wrapper prepares deterministic local
  proof artifacts and renders the exact detached Hemma commands/checklist for
  the accumulation-`2` lane.
- [x] One side-by-side proof record exists for accumulation values `4`, `2`,
  and `1` as needed.
- [x] If the preferred `1500` gate still fails, one fallback proof record
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
- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
