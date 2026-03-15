---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-15'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
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

## Next Actions

- Use the completed `T186` proof to decide the next bounded `T179`
  stability-retry slice rather than relaunching broad training blindly.
- Use `pdm run test-ml` / `pdm run typecheck-ml` as the fast local gate before
  broad repo-wide validation when iterating on Qwen ML code.
- Keep Task 101 live progress and operator truth in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep all new Qwen control-plane/runtime work inside the Story 28 package
  boundaries enforced by `RULE-095`.
