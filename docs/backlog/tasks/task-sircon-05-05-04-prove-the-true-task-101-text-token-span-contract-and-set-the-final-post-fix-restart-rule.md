---
type: task
id: TASK-SIRCON-05-05-04
title: Prove the true Task 101 text-token span contract and set the final post-fix
  restart rule
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-05-05
task_kind: story
acceptance_criteria:
- '- [ ] `T198` is treated as terminal negative evidence and is not reused as a reason
  to keep sweeping replay-only ablations.'
- '- [ ] The repo contains a deterministic artifact proving whether the current code
  still includes the wrong token span in the trainable text-embedding surface.'
- '- [ ] The corrected token-span contract is covered by focused tests and is visible
  in operator-facing metadata or reporting.'
- '- [ ] The canonical correction is chosen by semantic span correctness and minimal
  blast radius, not by small performance differences between otherwise similar variants.'
- '- [ ] The next clean restart remains blocked until the single post-fix proof reaches
  `1470` and the detached standalone eval completes.'
- '- [ ] If that single post-fix proof fails numerically before `1470` with the same
  failure family, Story 29 records a hard stop for bounded RCA on this preserved lane
  and `T199` remains blocked until a new design story exists.'
- '- [ ] Docs, runbook, and reference surfaces all describe the same restart and stop
  rule.'
retired_ids:
- task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule
---
## Context

Source record: docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md

### Objective

> Replace the current heuristic mask-policy theory with a provable Task 101
> text-token span contract, then use that contract to define the final bounded
> restart rule so Story 29 does not keep consuming replay-only RCAs forever.

## Decision And Assumption Ledger

## Story Contract Slice

### PR Scope

> - Treat `T198` as terminal negative evidence for the current replay family:
>   - accumulation `4`, `2`, and `1` all failed the preferred gate
>   - the fallback `1406 -> 1470` replay also failed at optimizer step `1449`
>     with the same optimizer-boundary class
> - Stop all further replay-only ablations on the current code path:
>   - no more accumulation sweeps
>   - no more alternate bounded windows
>   - no more restart attempts
>     until one code-bearing token-span correction exists
> - Use the canonical RCA checkpoint and failing sample evidence:
>   - checkpoint:
>     `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
>   - first failing microbatch:
>     train iteration `851`
>   - known matching evidence:
>     `507/508` positions went non-finite and the poisoned `93` rows matched the
>     sample's `93` unique token ids exactly
> - Add one deterministic offline audit surface that proves, for the failing
>   sample and one synthetic regression case:
>   - tokenizer output ids
>   - current trainable text-token span
>   - intended semantic text-token span
>   - whether pad, special, or codec-adjacent ids still leak into the trainable
>     text-embedding gradient surface
> - Convert the current `text_span_only` mitigation from a label into an explicit
>   contract driven by true text-token boundaries.
> - Select one canonical correction for that contract using correctness-first
>   criteria:
>   - it must match the intended semantic text-token boundary on the canonical
>     failing sample
>   - it must exclude pad, special, and codec-adjacent ids from the trainable
>     text-embedding gradient surface
>   - it must preserve the restored no-projection Task 101 fine-tuning contract
>     with the smallest plausible blast radius
>   - if multiple candidate corrections satisfy that contract, use simplicity and
>     operator transparency as the first tiebreakers and only use runtime
>     performance as a secondary tiebreaker
> - Add focused tests for:
>   - pad-token exclusion
>   - special-token exclusion
>   - codec-span exclusion
>   - deterministic span accounting for the failing manifest row
> - Define the final restart rule for the preserved Task 101 lane:
>   - after the token-span correction lands, allow exactly one decisive Hemma
>     proof package on the corrected code
>   - use `1406 -> 1470` plus standalone eval as the restart-authorizing gate
>     for that final post-fix proof
>   - do not require another preferred `1500` proof before the first clean
>     restart decision once the code-bearing token-span fix is in place
> - Define the stop rule for Story 29:
>   - if the single post-fix proof still fails numerically with the same
>     failure family before `1470`, stop bounded RCA on this preserved lane and
>     block `T199`
>   - any further work after that must be a new design/architecture story, not
>     another bounded replay variation
> - Allow reruns only for operational faults that are clearly non-numerical:
>   - storage exhaustion
>   - detached-launch metadata corruption
>   - other host/container execution faults that prevent truthful evidence

## Contract Inputs

## Plan

## Implementation Steps

## Proof

### Deliverables

> - [ ] One committed RCA artifact proves the intended versus actual trainable
>   text-token span for the canonical failing sample.
> - [ ] One committed runtime/control-plane correction enforces the true
>   text-token span contract.
> - [ ] One committed decision record names the canonical correction and explains
>   why nearby alternatives were rejected on contract-first grounds.
> - [ ] One explicit Story 29 restart rule states that the next post-fix proof
>   is the final bounded proof before either restart or stop.
> - [ ] One explicit Story 29 stop rule states that another same-family failure
>   before `1470` closes bounded RCA on the preserved Task 101 lane.

## Validation

## Stop Conditions

## Lessons Learned

### Current Audit Result

> - The offline audit surface now exists at:
>   - `pdm run qwen-token-span-audit`
>   - pre-fix artifact root:
>     `build/verification/qwen-token-span-audit/task206-canonical-line101/`
> - The canonical failing sample audit from manifest line `101` and train
>   iteration `851` proved:
>   - current `text_span_only` still trains positions `0..136`
>   - intended semantic text-only positions are `8..135`
>   - `9` non-semantic positions still leak into the trainable span:
>     `0..7` plus `136`
>   - leaked ids are the prefix special/pad/BOS/EOS ids:
>     `151644`, `77091`, `198`, `151671`, `151672`, `151673`
> - The audit therefore proves the correction cannot be another prefix-length
>   tweak:
>   - the intended semantic span does not start at `0`
>   - the correction family must move to an explicit position mask builder
> - The explicit position-mask correction now exists in dataset collation and the
>   first post-fix signal is green:
>   - smallest direct regression:
>     `tests/sir_convert_a_lot/ml/qwen/training/test_training_rows.py::test_collate_fn_text_span_only_masks_only_semantic_text_positions`
>   - post-fix artifact root:
>     `build/verification/qwen-token-span-audit/task206-postfix-line101/`
> - The post-fix audit now proves the leakage is gone on the canonical failing
>   sample:
>   - current `text_span_only` now resolves to positions `8..135`
>   - leaked positions are empty
>   - leaked token ids are empty
>   - leaked non-finite count is `0`
>   - current trainable non-finite count now equals the intended semantic
>     non-finite count: `128`
> - The remaining `T206` decision work is now narrower:
>   - keep this explicit position-mask correction as the canonical fix if the
>     focused gates and operator reporting remain clean
>   - then run the single final post-fix Hemma proof package
> - The single final post-fix Hemma proof has now been run under
>   `task206-20260317t074600z-postfix1470-a1`:
>   - proof surface:
>     `pdm run qwen-fallback-accumulation-proof launch-fallback1470 --proof-id task206-20260317t074600z-postfix1470-a1`
>   - settings:
>     - `text_embedding_mask_policy=text_span_only`
>     - explicit position-mask correction committed
>     - `gradient_accumulation_steps=1`
>   - outcome:
>     - replay exited with `exit_code=1`
>     - `current_optimizer_step=1407`
>     - `current_train_iteration=809`
>     - `trigger_reason=pre_clip_non_finite_gradients`
>     - `first_non_finite_stage=pre_clip`
>     - `first_non_finite_surface=text_embedding.weight.grad`
>   - no truthful `1470` checkpoint was minted
>   - detached standalone eval was therefore correctly not launched
> - `T206` has therefore answered the final bounded-RCA question for the
>   preserved Task 101 lane:
>   - the explicit position-mask correction removed the audited leakage
>   - but the single final post-fix Hemma proof still failed numerically before
>     `1470`
>   - the Story 29 stop rule is now triggered
>   - any further work must be a new design/architecture story, not another
>     bounded replay variant on this preserved lane

## Notes

## Plan Document Review

## Implementation Review
