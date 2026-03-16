---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-16'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-192-add-ml-specific-quality-gates-and-importlib-safe-qwen-test-collection.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-197-prove-the-text-span-only-mitigation-on-the-1406-1418-window-and-the-preferred-1500-gate.md
  - docs/backlog/tasks/task-198-run-the-conditional-accumulation-ablation-and-fallback-1470-proof-if-1500-still-fails.md
  - docs/backlog/tasks/task-204-restore-story-29-scratch-headroom-and-establish-cold-artifact-demotion-policy-on-hemma.md
  - docs/backlog/tasks/task-205-establish-idle-safe-recurring-hemma-scratch-maintenance.md
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

- preferred gate:
  - clear the mitigated `1406 -> 1418` replay
  - then reach `1500`
  - then complete scheduled eval at `1500`
- fallback gate:
  - only after the planned structural and accumulation proofs fail
  - clear `1406 -> 1470`
  - then run standalone held-out eval from `1470`

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
    - `T205` is the active follow-on: add idle-safe recurring maintenance,
      a small user-level timer, and recurring cold-artifact archive policy so
      scratch does not collapse again between proof runs

## Next Actions

- Keep the preserved Task 101 lane on the restored no-projection fine-tuning
  graph; do not reopen the projection-enabled experiment.
- Keep `state-step-00001406` as the canonical RCA checkpoint.
- Treat Story 29 as the required mitigation-and-restart gate:
  - no fresh clean restart before the preferred `1500` proof or the fallback
    `1470 + standalone eval` gate passes
- Keep the auxiliary codebook fusion helper on the plain vectorized reduction;
  do not revive the explicit `float32` reducer without new Hemma evidence.
- Keep the committed proof wrappers and hot-path audit surfaces available:
  - `pdm run qwen-t197-proof ...`
  - `pdm run qwen-t198-proof ...`
  - `pdm run run-hemma -- pdm run qwen-codebook-fusion-proof ...`
- Treat the completed `T197` Hemma proof as negative evidence and the first
  `T198` replay as positive numerical evidence but incomplete proof.
- Use `T204/T205` as the active enabling slice before the clean `T198` rerun:
  - audit Hemma scratch with
    `pdm run run-hemma -- pdm run qwen-scratch-policy audit`
  - run one idle-safe maintenance pass with
    `pdm run run-hemma -- pdm run qwen-scratch-policy maintain --prune-docker-state`
  - install the recurring timer with
    `pdm run run-hemma -- pdm run qwen-scratch-policy install-timer --enable-linger --prune-docker-state`
  - inspect timer state with
    `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`
- Once scratch headroom is healthy again, rerun the same accumulation-`2` lane:
  - `pdm run qwen-t198-proof launch-window --proof-id task198-20260316t185616z-accum2-a1`
  - only then allow `launch-gate1500` if the bounded replay exits cleanly
- Use `pdm run test-ml` and `pdm run typecheck-ml` as the fast local gate
  before broader repo validation while iterating on Qwen ML code.
- Keep Task 101 operator truth in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep all new Qwen control-plane/runtime work inside the Story 28 package
  boundaries enforced by `RULE-095`.
