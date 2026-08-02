---
id: task-183-control-checkpoint-cadence-and-retention-for-scheduled-task-101-qwen-training
title: Control checkpoint cadence and retention for scheduled Qwen training
type: task
status: completed
priority: critical
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-153-retain-only-bounded-durable-qwen-training-checkpoints-and-guard-scratch-capacity-on-hemma.md
  - docs/backlog/tasks/task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift.md
  - docs/backlog/tasks/task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - checkpoints
  - scheduling
  - eval
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and implement the canonical checkpoint and eval cadence policy for
scheduled Qwen runs so durable checkpoints happen at deliberate,
operator-useful boundaries rather than at smoke-test frequency, while retaining
only the newest `3` durable trainer-state checkpoints.

## Why This Exists

`T182` proved that:

- standalone `qwen-train eval` is now real on Hemma
- epoch-aware schedule control can read canonical `dataloader_length` and
  checkpoint metadata from a fresh Task 182-compliant launch
- the schedule surface itself is not blocked by missing eval logic

The current open problem is operational policy, not whether checkpoints should
exist at all:

- durable checkpoints are mandatory for truthful `train -> stop -> eval -> resume`
  control
- per-step smoke checkpointing is much too expensive to use as a real run
  cadence
- the real operator question is which checkpoint interval and retention window
  are correct for:
  - restart safety
  - held-out eval cadence
  - scratch usage
  - acceptable replay loss after interruption

The next slice must therefore stop treating checkpoint cost as a binary
problem and instead set a canonical cadence and retention policy for scheduled
training.

## PR Scope

- Define the canonical scheduled-run checkpoint policy for Task 101 in terms of:
  - durable checkpoint interval in optimizer steps
  - held-out eval interval in optimizer steps
  - retention count for durable trainer-state checkpoints
- Keep the current exact-resume contract and bounded retention machinery from
  `T153` and `T154`.
- Make the schedule/runbook/task surfaces explicit about the intended cadence
  tiers, rather than leaving operators to infer them from smoke defaults.
- Persist the agreed canonical scheduled lane policy:
  - durable checkpoint every `500` optimizer steps
  - held-out eval every `100` optimizer steps
  - retain newest `3` durable checkpoints
- Add focused implementation only where needed to align the live CLI/runtime
  defaults or schedule-control behavior to the approved cadence policy.
- Ground the chosen cadence against the measured full-pilot posture:
  - about `1500` optimizer steps per epoch
  - eval material is tiny (`8` held-out rows)
  - durable checkpoints are large and slow to finalize on Hemma

## Non-Goals

- Do not remove durable checkpoints from the scheduled lane.
- Do not weaken resumability into export-only restart.
- Do not reopen the batch-shape or GPU-saturation tuning work from `T172`.
- Do not redesign the Qwen objective or held-out eval metric set in this task.
- Do not require a new pilot-bundle rebuild to decide checkpoint cadence.

## Ordered Execution

1. Open the docs/task slice for schedule-specific checkpoint cadence and
   retention policy.
1. Review the current live defaults and operator surfaces for:
   - `checkpoint_interval_steps`
   - `eval_interval_steps`
   - `durable_checkpoint_retention`
1. Reconcile those defaults with the real scheduled-run posture rather than the
   short proof/smoke posture.
1. Document the canonical policy for:
   - checkpoint every `500` optimizer steps
   - eval every `100` optimizer steps
   - retain newest `3` durable checkpoints
1. Implement any necessary CLI/runtime default changes and focused tests.
1. Update runbook/task guidance so operators have one unambiguous scheduled-run
   contract.

## Deliverables

- [x] Canonical documented checkpoint/eval cadence policy for scheduled Qwen pilot runs.
- [x] Canonical documented durable checkpoint retention policy of newest `3`.
- [x] Any required CLI/runtime default alignment to that policy.
- [x] Focused tests covering the chosen default cadence/retention contract.
- [x] Updated runbook/task guidance for real scheduled Hemma operation.

## Acceptance Criteria

- [x] The repo documents and ships the canonical durable checkpoint cadence for
  scheduled Qwen pilot runs as every `500` optimizer steps.
- [x] The repo documents and ships the canonical held-out eval cadence for
  scheduled Qwen pilot runs as every `100` optimizer steps, explicitly
  accounting for the small held-out eval set and the full pilot epoch length.
- [x] The repo documents and enforces the canonical durable checkpoint
  retention count of `3`.
- [x] The chosen cadence/retention policy is reflected consistently across
  task/runbook/CLI/runtime surfaces.
- [x] Focused tests prove the configured defaults or schedule-policy helpers
  match the documented contract.
- [x] The resulting policy is explicitly justified in terms of:
  - recovery point loss
  - checkpoint finalization cost
  - held-out signal frequency
  - scratch retention pressure

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_eval_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_schedule_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Notes

- `T182` already proved the standalone eval path on Hemma with:
  - `eval_dataloader_length=3`
  - `eval_batches_completed=3`
  - `eval_loss=6.681333859761556`
- The next question is therefore not whether eval works, but shipping the
  agreed durable-checkpoint control posture for real scheduled operation.
- The chosen scheduled default is:
  - durable checkpoint every `500` optimizer steps
  - held-out eval every `100` optimizer steps
  - retain newest `3` durable trainer-state checkpoints
- Current full-pilot planning still puts one epoch at roughly `1500` optimizer
  steps, so this policy yields about three durable resume points per epoch and
  a denser held-out signal without per-step checkpoint churn.
- The shipped defaults were aligned in both the detached `qwen-train` CLI and
  the in-container patched trainer surface so the public launcher and the
  actual runtime now agree on `500/100/3`.
