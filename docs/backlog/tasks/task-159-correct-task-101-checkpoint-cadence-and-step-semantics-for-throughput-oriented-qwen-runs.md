---
id: task-159-correct-task-101-checkpoint-cadence-and-step-semantics-for-throughput-oriented-qwen-runs
title: Correct Task 101 checkpoint cadence and step semantics for throughput-oriented Qwen runs
type: task
status: completed
priority: critical
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-153-retain-only-bounded-durable-qwen-training-checkpoints-and-guard-scratch-capacity-on-hemma.md
  - docs/backlog/tasks/task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - checkpoints
  - throughput
  - semantics
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove avoidable throughput loss from the current Task 101 long-run checkpoint
policy and make the visible step counters truthful enough for operators and
tests to reason about real training progress.

## Why This Exists

The live `2026-03-13` run used:

- `checkpoint_interval_steps = 2`
- durable trainer-state checkpoints of about `11G` each

while the patched trainer still reports progress through a surface named
`optimizer_steps_completed` despite `gradient_accumulation_steps = 4`.

That combination is operationally confusing and almost certainly too expensive
for a long saturation-oriented run.

## PR Scope

- Change the long-run Task 101 default durable-checkpoint cadence from `2`
  steps to a throughput-oriented default, with `100` steps as the intended
  canonical long-run posture unless evidence later disproves it.
- Preserve shorter checkpoint cadence only for explicitly bounded smoke or
  profile launches.
- Audit and correct the current step semantics so the runtime distinguishes
  loop iteration counters from optimizer-update counters when gradient
  accumulation is enabled.
- Persist the clarified counters into Task 101 status/report/tracker surfaces.
- Keep durable retention `N=2`, compatibility defaults, staging-save behavior,
  and latest-checkpoint truthfulness unchanged.

## Non-Goals

- Do not weaken resumability into export-only checkpoints.
- Do not change dataloader or tracker work in this slice.
- Do not silently change the smoke-profile defaults without documenting the new
  launch-profile contract.

## Deliverables

- [x] Long-run checkpoint cadence is reduced from the current `2`-step posture.
- [x] Step semantics are explicitly documented and machine-readable.
- [x] Task 101 metadata/report surfaces distinguish iteration-style counters
  from optimizer-update counters where relevant.
- [x] Focused tests prove the new cadence/defaults and step semantics.

## Acceptance Criteria

- [x] Long Task 101 runs no longer default to durable trainer-state saves every
  `2` steps.
- [x] Smoke/profile runs retain an explicitly documented tighter checkpoint
  posture where needed.
- [x] The visible counters used in status, reports, and tracking are truthful
  enough that an operator can tell what one “step” means.
- [x] Checkpoint retention, latest-pointer truthfulness, exported model
  checkpoints, and resume compatibility do not regress.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_status_reporter.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma proof records lower checkpoint churn and the new counter
  semantics in machine-readable artifacts.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
