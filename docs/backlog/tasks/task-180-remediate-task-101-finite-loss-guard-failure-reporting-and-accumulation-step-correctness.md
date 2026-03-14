---
id: task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness
title: Remediate Task 101 finite-loss guard, failure reporting, and accumulation-step correctness
type: task
status: in_progress
priority: high
created: '2026-03-14'
last_updated: '2026-03-14'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-171-eliminate-task-101-per-step-host-synchronization-overhead-and-add-finite-loss-guards.md
  - docs/backlog/tasks/task-175-close-the-remaining-task-101-throughput-truth-gaps-from-the-review-alignment.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - training
  - numerical-stability
  - observability
  - testing
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Fix the concrete Task 101 training/runtime defects exposed by the rebuilt-bundle
throughput proofs so the finite-loss guard and terminal artifacts tell the
truth, and so the accumulation-mode training loop obeys correct optimizer-step
semantics before `T179` launches the next bounded Hemma saturation repro.

## Why This Exists

The review of the rebuilt-bundle throughput failures exposed repo-side logic
and observability defects that are strong candidates for causing or obscuring
the `NaN` lane:

- the failed run path does not write canonical `report.json`
- failed `status.json` can contradict the finite-loss-guard payload because it
  reuses stale heartbeat counters
- the accumulation-mode test harness does not model real
  `gradient_accumulation_steps=4` semantics
- the training loop currently appears to call `optimizer.step()` and
  `optimizer.zero_grad()` outside the `completed_optimizer_step` gate, which
  may advance optimizer state on every microbatch instead of only on
  accumulation boundaries

The rebuilt-bundle rerun on Hemma stayed finite longer but still failed:

- first failed proof: `task175-20260314t-throughput-a2`
  - guard tripped at `optimizer_step=4`
- rerun proof: `20260314T181545Z`
  - guard tripped at `optimizer_step=17`

That pattern means we need to repair the core loop and failure surfaces before
spending more time on saturation-only retries.

This task is intentionally narrower than `T179`:

- `T180` owns the code-side remediation and regression coverage
- `T179` owns the next bounded Hemma repro and the decision about whether the
  numerical-stability window is now sufficient for another saturation attempt

## PR Scope

- Prove whether the patched training loop currently advances optimizer state on
  non-sync microbatches under accumulation mode.
- If that behavior is confirmed, gate `optimizer.step()` and `optimizer.zero_grad()`
  on true accumulation boundaries and add regression coverage for that fix.
- Make terminal failed runs write a canonical machine-readable failure report in
  addition to `failure.txt` and `status.json`.
- Ensure failed `status.json` uses the actual failure-step counters rather than
  stale heartbeat values when the exception carries more precise progress data.
- Strengthen the fake-accelerator / fake-optimizer test harness so unit tests
  model real gradient-accumulation semantics instead of treating every batch as
  a completed optimizer step.
- Add regression tests that prove:
  - optimizer state advances only on accumulation boundaries
  - failed status and finite-loss-guard payloads agree on the failing step
  - failed runs persist canonical machine-readable report artifacts

## Non-Goals

- Do not redesign the Qwen loss function or objective in this task.
- Do not broaden this work into bundle observability, drive ingestion, or host
  package-manager recovery.
- Do not claim the `NaN` root cause is fully solved in this task alone.
- Do not use this task to close the bounded Hemma repro work that belongs to
  `T179`.

## Deliverables

- [ ] The accumulation-boundary audit is resolved and documented:
  - if the suspected optimizer-step bug is confirmed, the training loop only
    performs optimizer step / zero-grad work on true accumulation boundaries
  - if the suspicion is disproven, the task records that evidence explicitly in
    this task's completion notes or current-progress section without landing an
    unproven behavior change
- [ ] Failed Qwen training runs persist canonical `report.json` artifacts with
  failure metadata.
- [ ] Failed `status.json` payloads report the actual terminal progress counters
  rather than stale heartbeat counters.
- [ ] The unit-test harness can simulate `gradient_accumulation_steps > 1`
  truthfully.
- [ ] Regression tests cover the exact reviewed failure modes.

## Acceptance Criteria

- [ ] A focused unit/integration test proves the accumulation-aware prepared
  optimizer only advances effective step / zero-grad state on sync boundaries,
  even though the caller still invokes `optimizer.step()` and
  `optimizer.zero_grad()` inside `accelerator.accumulate(model)` as the
  official Accelerate guidance expects.
- [ ] A focused failure-path test proves a `NonFiniteLossError` writes:
  - `failure.txt`
  - `status.json`
  - `report.json`
    with matching failing-step truth.
- [ ] If the optimizer-step audit disproves the suspected accumulation bug, the
  task records that evidence explicitly and still lands the failed-artifact and
  regression-harness fixes without making an unproven behavior change.
- [ ] Failed `status.json` and `report.json` both expose the same terminal
  failure-step truth, including:
  - `current_optimizer_step`
  - `current_train_iteration`
  - `error`
  - `finite_loss_guard`
- [ ] The accumulation-aware regression harness proves at least one non-sync
  microbatch occurs before a sync boundary in the failing-lane test shape, so
  `T179` does not need ad hoc observability patches before its next bounded
  Hemma repro.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py`
- [ ] The validation tests explicitly assert:
  - failed runs write `report.json`
  - failed `status.json.current_optimizer_step` matches
    `finite_loss_guard.optimizer_step`
  - accumulation-mode tests exercise non-sync microbatches before one sync
    boundary
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `T179` is updated or remains explicitly aligned as the dependent bounded
  Hemma repro task after this code-side remediation lands.

## Current Progress

- Local code-side remediation is in progress.
- The failure-report and failed-status fixes are being landed together with an
  accumulation-aware fake Accelerate harness.
- The optimizer-step suspicion has been audited against the official
  Hugging Face Accelerate accumulation guidance and a wrapped-optimizer test
  harness:
  - `accelerator.accumulate(model)` still expects `optimizer.step()` and
    `optimizer.zero_grad()` to be called inside the loop body
  - the effective step/zero-grad semantics are owned by the prepared optimizer
    on sync boundaries rather than by ad hoc caller-side gating
- Because of that audit result, this task does not land an unproven behavior
  change to the live training loop. It instead hardens the failure artifacts,
  failed-status truth, and accumulation-aware regression coverage that `T179`
  needs for the next bounded rebuilt-bundle repro.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
