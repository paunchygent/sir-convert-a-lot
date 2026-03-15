---
id: task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay
title: Remediate Task 101 optimizer-boundary corruption and deterministic failure replay
type: task
status: in_progress
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - training
  - numerical-stability
  - diagnostics
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Turn the repeated Task 101 non-finite-loss failure from a slow live-run mystery
into a deterministic, bounded, operator-trustworthy root-cause workflow that:

- proves whether the text embedding / text projection params are finite before
  and after the optimizer update,
- proves whether optimizer state for those params is already corrupted, and
- fails closed before a corrupt update is applied when `grad_norm` or targeted
  grads are non-finite.

This task is the canonical prerequisite for any further `T179` bounded
numerical-stability retry.

Permanent anti-god-file refactoring is tracked separately under Story 28 /
`T187-T191`. `T186` owns the optimizer-boundary bug and diagnostic surface;
Story 28 owns the long-term architecture hardening that prevents the same
central files from absorbing new logic again.

## Why This Exists

`T180` delivered truthful finite-loss forensics, per-microbatch provenance, and
checkpoint-phase truth. That work answered the first-order question: the Task
101 failure is real, and the first poisoned runtime surface is
`input_text_embedding`.

The next bounded replay on Hemma proved the deeper transition we now need to
own explicitly:

- at optimizer step `1405`, losses remained finite but `grad_norm` was already
  non-finite,
- the training loop still allowed `optimizer.step()` to execute,
- and the next optimizer step entered with `input_text_embedding` already
  `NaN`, which then poisoned the rest of the forward path.

That means the current root-cause work is no longer “add more generic NaN
forensics.” It is:

- optimizer-boundary corruption detection,
- deterministic failure replay on a realistic detached surface, and
- a fail-closed policy that preserves trustworthy artifacts before weights are
  poisoned.

## PR Scope

- Add one public thin detached diagnostic surface:
  - `pdm run qwen-train diagnose-non-finite`
- Keep CLI/orchestration thin and place the replay/probe logic in domain
  services.
- Add a focused optimizer-boundary diagnostics helper in the Qwen patch area so
  `sft_12hz_loop.py` does not absorb another large block of branching logic.
- Persist machine-readable replay artifacts for the bounded failing window:
  - resumed checkpoint identity
  - deterministic microbatch order
  - pre-step targeted parameter probes
  - pre-step targeted optimizer-state probes
  - post-step targeted parameter probes
  - post-step targeted optimizer-state probes
  - whether `optimizer.step()` was attempted, skipped, or completed
  - exact failure reason and first poisoned surface
- Fail closed on sync boundaries when either of these happens:
  - non-finite `grad_norm`
  - non-finite targeted gradients on `text_embedding` / `text_projection`
- Fail closed immediately after the update when either of these happens:
  - non-finite targeted parameters
  - non-finite targeted optimizer-state tensors
- Reuse the replay-bundle format in tests and local diagnostics so follow-up
  root-cause work does not require repeated multi-minute full-lane reruns.
- Keep the remediation SRP-aligned by extracting:
  - one optimizer-boundary diagnostics/guard module,
  - one replay-artifact/report module, and
  - one detached diagnostic orchestration module.

## Non-Goals

- Do not turn this task into a broad hyperparameter search.
- Do not silently skip bad rows and continue training in this task.
- Do not add a flag lattice of heavyweight diagnostics.
- Do not rerun `T179` until this task lands and produces one clear bounded
  root-cause report.

## Deliverables

- [ ] `T186` backlog, runbook, skill, and operator-reference docs are aligned
  to one canonical diagnostic flow before code changes are landed.
- [ ] `qwen-train diagnose-non-finite` exists as a detached, repo-owned,
  realistic diagnostic surface.
- [ ] The optimizer-boundary guard records and exposes pre-step and post-step
  finiteness for:
  - `model.talker.model.text_embedding`
  - `model.talker.model.text_projection` when present
  - optimizer-state tensors for those params
- [ ] The training loop fails closed before a corrupt update is applied when
  targeted pre-step signals are non-finite.
- [ ] The training loop fails closed immediately after a corrupt update when
  targeted parameters or optimizer state become non-finite.
- [ ] Replay artifacts are reusable by tests so the repo does not remain
  dependent on repeated 20-minute live reruns to inspect the same failure
  window.
- [ ] Focused tests own the new optimizer-boundary and replay logic instead of
  expanding the existing god test files again.

## Acceptance Criteria

- [ ] A focused guard test proves finite losses plus non-finite `grad_norm`
  skip `optimizer.step()` and fail with
  `pre_step_non_finite_grad_norm`.
- [ ] A focused guard test proves finite `grad_norm` plus a targeted
  non-finite gradient skip `optimizer.step()` and fail with
  `pre_step_non_finite_gradients`.
- [ ] A focused post-step test proves a newly corrupted
  `text_embedding.weight` fails immediately with
  `post_step_non_finite_parameters`.
- [ ] A focused post-step test proves corrupted optimizer state
  (`exp_avg` / `exp_avg_sq`) fails immediately with
  `post_step_non_finite_optimizer_state`.
- [ ] A replay test proves the captured `1405 -> 1406` window can be replayed
  deterministically from the persisted replay artifact without depending on
  hidden sampler state.
- [ ] `status.json`, `report.json`, and the failure payload agree on:
  - failure reason,
  - optimizer step,
  - targeted parameter family, and
  - whether the optimizer step was skipped or completed
- [ ] One bounded Hemma `diagnose-non-finite` run from
  `state-step-00001238` writes a clear machine-readable root-cause report
  for the failing window.
- [ ] After the guard lands, rerunning the same detached diagnostic surface
  proves the lane stops before weight corruption rather than after it.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_optimizer_guard.py tests/sir_convert_a_lot/ml/qwen/training/test_diagnostic_replay.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] One detached Hemma `qwen-train diagnose-non-finite` proof exists under
  `build/verification/`.

## Current Progress

- `T186` is now the canonical remediation owner for optimizer-boundary
  corruption and deterministic failure replay.
- `T180` remains the delivered first-pass truth/forensics slice and is being
  closed out as historical context rather than expanded further.
- The currently approved default diagnostic target is strict replay from
  `state-step-00001238` against the replacement Task 152 bundle.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
