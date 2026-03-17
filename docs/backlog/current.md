---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-17'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-192-add-ml-specific-quality-gates-and-importlib-safe-qwen-test-collection.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma.md
  - docs/backlog/tasks/task-205-establish-idle-safe-recurring-hemma-scratch-maintenance.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md
  - docs/backlog/reviews/review-03-architect-review-of-post-task-101-qwen-stabilization-candidates-after-story-29.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - session-log
  - active-work
---

## Context

Epic 08 remains the active lane. The repo focus is bounded closure for the
preserved no-projection Task 101 training series, with Story 29 acting as the
mandatory mitigation gate before any new clean restart.

The current proof posture is:

- exhausted replay-family evidence:
  - preferred gate attempts with accumulation `4`, `2`, and `1` all failed
  - the fallback `1406 -> 1470` replay also failed on the current code path
- final post-fix rule:
  - land one code-bearing text-token span correction
  - then run exactly one decisive Hemma proof:
    - clear `1406 -> 1470`
    - then complete detached standalone eval from that checkpoint
  - if that final post-fix proof still fails numerically before `1470`, stop
    bounded RCA on this preserved lane

Story 28 is now operating policy:

- `RULE-095` enforces the Qwen package split and `400` LoC hot-path cap
- `qwen_train.py` is a composition root only
- host control-plane logic lives under `ml/qwen/training/control_plane/`
- detached runtime logic lives under `ml/qwen/training/detached_runtime/`
- reporting lives under `ml/qwen/training/reporting/`
- deleted legacy god files must not return

## Worklog

- 2026-03-13:
  - Story 26 throughput and observability evidence established the lane as
    host-orchestration/synchronization bound with persistent `NaN` risk.
- 2026-03-15:
  - `T184/T185/T180/T186` established truthful checkpoint cadence, the `1236`
    eval baseline, strict-resume `1238`, and fail-closed optimizer-boundary
    proof at step `1405`.
  - Story 28 / `T187-T191` landed the permanent SRP/DDD split.
  - `T192` added the fast ML gate lane with `test-ml`, `typecheck-ml`, and
    importlib-safe pytest collection.
  - `T193` restored the upstream no-projection fine-tuning contract and added
    stage-resolved clip-boundary forensics.
  - `T194` became the RCA narrowing slice for the first pre-clip text-embedding
    gradient failure.
- 2026-03-16:
  - trainer-native exact capture succeeded at step `1401`, and the bounded
    replay under `task194-20260316t-1405-rca-a1` crossed the old `1405`
    failure window cleanly and minted `state-step-00001406`.
  - the bounded continuation from `1406` failed again at optimizer step `1417`
    with the same shape:
    - `trigger_reason=pre_clip_non_finite_gradients`
    - parameters and optimizer state remained finite
    - `text_embedding.weight.grad` was the first poisoned parameter surface
  - the bounded `1406 -> 1418` replay reproduced the failure exactly and
    narrowed the root cause further:
    - the first bad backward surface is `input_text_embedding.grad`
    - the first bad microbatch is `851`
    - `507/508` token positions in that sample went non-finite
    - the poisoned `93` text-embedding rows match the sample's `93` unique
      token ids exactly
    - token id `151671` appeared `375` times, which matches the active
      codec-span text-pad surface
  - Story 29 became the explicit mitigation lane built on that RCA:
    - `T195` made `text_span_only` the fresh-launch default and kept
      `legacy_codec_span` only for bounded RCA reproduction
    - `T196` made `gradient_accumulation_steps` explicit across launch,
      resume, capture, diagnose, eval, and schedule
    - `T203` reverted the auxiliary codebook fusion helper from the proof lane
      after Hemma ROCm evidence showed unchanged oracle error and about `1.26x`
      slowdown in both `bf16` and `fp16`
    - `T197` then ran on Hemma under `task197-20260316t183555z-a1` and failed
      again at optimizer step `1417`, so `text_span_only` plus accumulation `4`
      did not satisfy the preferred gate
    - `T198` then ran its first accumulation-`2` replay under
      `task198-20260316t185616z-accum2-a1`
    - that replay cleared the old `1417` numerical window and reached `1418`
      without a non-finite gradient, but it failed during durable checkpoint
      save because Hemma scratch free space fell to about `9 GB`
  - `T204` added the manual scratch audit/remediation lane and the proof
    launch headroom preflight so detached Story 29 work now fails early on
    insufficient scratch headroom
    - `T205` then restored healthy recurring scratch governance on Hemma:
      - idle-safe `qwen-scratch-policy maintain`
      - a user-level maintenance timer
      - enough reclaimed SSD headroom for the clean accumulation-`2` rerun
    - the clean `T198` rerun under
      `task198-20260316t202541z-accum2-a2`
      then exited the bounded `1406 -> 1418` replay cleanly, minted
      `state-step-00001418`, and completed the scheduled eval at that replay
      boundary
    - the preferred `1500` continuation from that clean `1418` checkpoint then
      failed at optimizer step `1428` with the same optimizer-boundary class:
      - `trigger_reason=pre_clip_non_finite_gradients`
      - `first_non_finite_stage=pre_clip`
      - `first_non_finite_surface=text_embedding.weight.grad`
      - `current_train_iteration=852`
    - no newer durable checkpoint beyond `1418` was minted during that failed
      continuation, so `1418` remains the latest truthful accumulation-`2`
      recovery anchor for this rerun
    - the focused accumulation-`1` replay under
      `task198-20260316t213409z-accum1-a1`
      then exited the bounded `1406 -> 1418` replay cleanly, minted its own
      `state-step-00001418`, completed the scheduled eval there, and pushed
      the preferred `1500` continuation farther before failing
    - that accumulation-`1` preferred-gate attempt then failed at optimizer
      step `1449` with the same optimizer-boundary class:
      - `trigger_reason=pre_clip_non_finite_gradients`
      - `first_non_finite_stage=pre_clip`
      - `first_non_finite_surface=text_embedding.weight.grad`
      - `current_train_iteration=851`
      - `first_non_finite_tensor=grad_norm`
    - the direct fallback replay under
      `task198-20260317t062816z-fallback1470-a1`
      then also failed at optimizer step `1449`
    - the fallback replay preserved the same optimizer-boundary class:
      - `trigger_reason=pre_clip_non_finite_gradients`
      - `first_non_finite_stage=pre_clip`
      - `first_non_finite_surface=text_embedding.weight.grad`
    - no truthful `1470` checkpoint was minted, so detached standalone eval
      was correctly not launched
    - `T198` is now terminal negative evidence for the current replay family
    - `T206` is now the next active task:
      prove the true text-token span contract and define the final post-fix
      restart/stop rule
- 2026-03-17:
  - `T206` landed the explicit position-mask correction in dataset collation:
    `text_span_only` now activates only the semantic text positions instead of
    the old prefix-length surface
  - the smallest direct regression passed and the post-fix offline audit under
    `build/verification/qwen-token-span-audit/task206-postfix-line101/`
    proved:
    - active span `8..135`
    - no leaked positions
    - no leaked token ids
    - leaked non-finite count `0`
  - the single final post-fix Hemma proof then ran under
    `task206-20260317t074600z-postfix1470-a1`
  - that proof still failed numerically before `1470`:
    - `trigger_reason=pre_clip_non_finite_gradients`
    - `first_non_finite_stage=pre_clip`
    - `first_non_finite_surface=text_embedding.weight.grad`
    - `current_optimizer_step=1407`
    - `current_train_iteration=809`
  - no truthful `1470` checkpoint was minted, so detached standalone eval was
    correctly not launched
  - the Story 29 stop rule is now triggered for the preserved Task 101 lane
  - bounded RCA on this preserved lane is therefore closed
  - Story 30 is now active with the closed architect verdict:
    - Candidate 1 selected
    - ordered contingency `1 -> 3`
    - Candidate 2 rejected as the primary next story

## Next Actions

- Keep the preserved Task 101 lane on the restored no-projection fine-tuning
  graph; do not reopen the projection-enabled experiment.
- Keep `state-step-00001406` as the canonical RCA checkpoint.
- Keep the auxiliary codebook fusion helper on the plain vectorized reduction;
  do not revive the explicit `float32` reducer without new Hemma evidence.
- Keep the Hemma scratch-governance surfaces active and available:
  - `pdm run run-hemma -- pdm run qwen-scratch-policy audit`
  - `pdm run run-hemma -- pdm run qwen-scratch-policy maintain --prune-docker-state`
  - `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`
- Treat Story 29 / `T197-T206` as closed bounded-RCA evidence on the preserved
  lane:
  - the explicit position-mask correction removed the audited leakage
  - the single final post-fix Hemma proof still failed at optimizer step `1407`
  - no truthful `1470` checkpoint was minted and detached eval was not launched
  - `T199` therefore remains blocked
  - the next step is Story 30 Candidate 1, not another replay or post-fix
    proof variant
- Execute Story 30 in this order:
  - `T207` semantic-only batch contract
  - `T208` semantic-only train-step assembly
  - `T209` local gradient-membership proof
  - if Candidate 1 fails, open Candidate 3 directly as the next contingency
- Do not spend the next story on Candidate 2.
- Use `pdm run test-ml` and `pdm run typecheck-ml` as the fast local gate
  before broader repo validation while iterating on Qwen ML code.
- Keep Task 101 operator truth in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep all new Qwen control-plane/runtime work inside the Story 28 package
  boundaries enforced by `RULE-095`.
