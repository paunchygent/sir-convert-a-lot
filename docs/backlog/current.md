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
  - The first `T179` remediation slice is now in progress:
    - an upstream-shape audit found the patched trainer/eval/guard were
      resolving `text_projection` from `model.talker.model` even though
      upstream Qwen exposes it on `model.talker`
    - the text path is now centralized in
      `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_runtime.py`
      so train, eval, and optimizer-boundary probes share one runtime-shape
      contract
    - local Qwen regressions and `pdm run typecheck-ml` passed after the fix
  - The first corrected-graph `T179` replay then finished at
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task179-20260315t-textpath-replay-a1`
    and proved the fix was active but the resumed trainer-state lane still
    failed earlier at optimizer step `1239`.
  - That replay included the full text-path probe family
    (`text_embedding.weight` plus `text_projection.linear_fc1/2.*`) and showed
    finite forward losses with finite pre-step parameters/optimizer state, but
    already-`NaN` text-embedding and text-projection gradients.
  - `state-step-00001238` is therefore no longer treated as the authoritative
    next corrected-graph continuation checkpoint; it is now diagnostic/salvage
    input only.
  - Runtime-shape visibility is now explicit in artifacts:
    - the trainer writes a `talker_runtime` fingerprint with resolved text,
      codec, and projection paths plus probeability truth
    - focused resolver tests now cover talker-level projection, nested
      fallback, missing projection, and callable-but-non-module projection
  - Decision taken: clean corrected-graph base restart is the new mainline.
    Salvage from `1238` is optional side evidence only.

## Next Actions

- Launch the clean corrected-graph base restart on Hemma using the same Task
  152 replacement bundle and truthful `500/100/3` control posture as the last
  valid lane.
- Use `pdm run test-ml` / `pdm run typecheck-ml` as the fast local gate before
  broad repo-wide validation when iterating on Qwen ML code.
- Keep Task 101 live progress and operator truth in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Keep all new Qwen control-plane/runtime work inside the Story 28 package
  boundaries enforced by `RULE-095`.
