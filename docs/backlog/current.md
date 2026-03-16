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
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/tasks/task-192-add-ml-specific-quality-gates-and-importlib-safe-qwen-test-collection.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - session-log
  - active-work
---

## Context

Epic 08 is the active lane. The current repo focus is no longer broad Task 101
bring-up; it is bounded closure on Story 26 after the completed `T186` proof,
with live operator truth tracked in
`docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.

Story 28 / `T187-T191` is delivered and now part of core operating policy:

- `RULE-095` enforces the `400` LoC cap and no-shim/no-compat-wrapper policy
- `qwen_train.py` is a composition root only
- host-side logic lives in `ml/qwen/training/control_plane/`
- detached runtime logic lives in `ml/qwen/training/detached_runtime/`
- reporting lives in `ml/qwen/training/reporting/`
- patched training runtime logic is split across bounded `sft_12hz_*` modules
- the deleted `orchestrator.py` and `reporting.py` files must not return

## Worklog

- 2026-03-13:
  - Story 26 throughput and observability evidence established the lane as
    host-orchestration/synchronization bound with persistent `NaN` risk.
- 2026-03-15:
  - `T184` aligned scheduled control truth to `500/100/3`.
  - `T185` restored legacy checkpoint recovery, established the `1236` eval
    baseline, and promoted `1238` as the canonical strict-resume checkpoint.
  - `T180` landed the first-pass truth layer for forensics, sampler truth,
    checkpoint-phase truth, and epoch semantics.
  - The later instrumented replay proved the remaining bug is at the
    optimizer boundary: step `1405` already had non-finite `grad_norm`, and
    step `1406` entered with `input_text_embedding` already poisoned.
  - `T186` landed the root-cause and fail-closed diagnostic proof slice.
  - Story 28 / `T187-T191` landed the permanent SRP/DDD architecture split.
  - `T192` added the fast ML gate lane:
    - `pdm run test-ml`
    - `pdm run typecheck-ml`
    - Qwen ML pytest now uses `--import-mode=importlib` so duplicate test
      basenames do not break collection from repo root.
  - The canonical guarded Hemma proof completed at launch root
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T180643Z`.
  - That proof reused the truthful `500/100/3` source launch root
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/20260315T110545Z`
    and proved fail-closed behavior at optimizer step `1405` with
    `trigger_reason=pre_step_non_finite_grad_norm`,
    `optimizer_step_attempted=false`, and
    `optimizer_step_completed=false`.
  - `text_embedding.weight` and its optimizer state stayed finite pre-step
    while `text_embedding.weight.grad` was already non-finite, which closes
    `T186` as the optimizer-boundary proof slice.
  - The first `T179` remediation slice established one important runtime fact:
    - an upstream-shape audit found the patched trainer/eval/guard were
      resolving `text_projection` from `model.talker.model` even though
      upstream Qwen exposes it on `model.talker`
    - the text path is now centralized in
      `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_runtime.py`
      so train, eval, and optimizer-boundary probes share one runtime-shape
      contract
    - local Qwen regressions and `pdm run typecheck-ml` passed after the fix
  - The first projection-enabled `T179` replay then finished at
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task179-20260315t-textpath-replay-a1`
    and proved the shared resolver was active, but that a projection-enabled
    resumed lane could fail earlier at optimizer step `1239`.
  - The later clean projection-enabled base restart also failed immediately at
    optimizer step `1`. That is now treated as evidence against injecting
    `text_projection` into the fine-tuning graph, not as evidence that the
    preserved no-projection Task 101 lane is worthless.
  - Runtime-shape visibility is now explicit in artifacts:
    - the trainer writes a `talker_runtime` fingerprint with resolved text,
      codec, and projection paths plus probeability truth
    - focused resolver tests now cover talker-level projection, nested
      fallback, missing projection, and callable-but-non-module projection
  - `T193` is now the active numerical-stability slice:
    - the patched train and eval paths are restored to the upstream
      no-projection fine-tuning contract
    - optimizer-boundary artifacts now distinguish `pre_clip`,
      `clip_grad_norm`, `post_clip`, and `post_step`
    - `state-step-00001238` is back in standing as the canonical
      no-projection RCA checkpoint for the preserved Task 101 lane
  - `T194` now owns the next RCA narrowing slice:
    - use the captured `1405` no-projection failure artifact rather than
      another blind training retry
    - identify the exact `text_embedding` rows and token ids behind the first
      `pre_clip` non-finite gradient
    - determine whether corruption appears on `input_text_embedding` gradients
      before parameter gradients and whether accumulation across
      microbatches `801-804` is required
- 2026-03-16:
  - trainer-native exact capture succeeded at optimizer step `1401` under
    `task194-20260316t-capture1401-a3`
  - the bounded `1401 -> 1406` replay under
    `task194-20260316t-1405-rca-a1` crossed the old `1405` failure window
    cleanly and minted a new durable checkpoint at `state-step-00001406`
  - the live continuation policy is now explicit:
    - one full pass over the current pilot material = `32` optimizer steps
    - next review point = optimizer step `1500`
    - bounded continuation target = optimizer step `1566`
    - absolute resume cap = `num_epochs=12`
  - the canonical detached resume surface now accepts bounded
    `--num-epochs` / `--max-steps` overrides, so the `1406 -> 1566`
    continuation can run on the normal `qwen-train resume` command instead of
    an ad hoc launcher

## Next Actions

- Keep the preserved Task 101 lane on the restored no-projection fine-tuning
  graph; do not relaunch the projection-enabled experiment.
- Keep `T194` open as the RCA lane, but the immediate operator move is now the
  bounded `1406 -> 1566` continuation, not another replay by default.
- Review the continued lane at optimizer step `1500`.
- Stop the bounded continuation at optimizer step `1566` if it remains finite.
- Reopen the `1405` RCA track as the primary operator move only if the new
  continuation reintroduces a non-finite boundary.
- Use `pdm run test-ml` / `pdm run typecheck-ml` as the fast local gate before
  broad repo-wide validation when iterating on Qwen ML code.
- Keep Task 101 live progress and operator truth in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep all new Qwen control-plane/runtime work inside the Story 28 package
  boundaries enforced by `RULE-095`.
