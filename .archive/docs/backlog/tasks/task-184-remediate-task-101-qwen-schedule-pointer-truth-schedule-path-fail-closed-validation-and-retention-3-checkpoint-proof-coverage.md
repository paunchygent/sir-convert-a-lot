---
id: task-184-remediate-task-101-qwen-schedule-pointer-truth-schedule-path-fail-closed-validation-and-retention-3-checkpoint-proof-coverage
title: Remediate Qwen schedule pointer truth, schedule-path fail-closed validation, and retention-3 checkpoint proof coverage
type: task
status: completed
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training.md
  - docs/backlog/tasks/task-183-control-checkpoint-cadence-and-retention-for-scheduled-task-101-qwen-training.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - scheduling
  - checkpoints
  - review-remediation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close the post-review control-plane gaps in the shipped Task 101 scheduled-run
posture so operator-facing schedule control remains truthful after
`500/100/3` shipped.

## PR Scope

- Update schedule-driven resume flow so the canonical latest-launch pointer
  follows the resumed detached launch rather than the already-stopped source
  launch.
- Make schedule control fail closed for launch-derived checkpoint/eval/bundle
  paths in the same way the standalone eval surface already does.
- Add explicit regression coverage for the real retention-`3` durable
  checkpoint contract rather than only proving the older retention-`2`
  boundary.
- Keep the slice bounded to truthfulness, operator safety, and proof coverage;
  do not change checkpoint cadence or eval cadence again.

## Ordered Execution

1. Add docs-as-code remediation tracking linked to the active schedule-control
   task.
1. Patch schedule resume so the latest launch pointer follows the resumed
   detached launch.
1. Harden schedule path validation for launch-derived defaults and explicit
   overrides.
1. Add focused regression coverage for pointer truth and retention-`3`
   boundary behavior.
1. Run focused Qwen training tests plus docs validators.

## Deliverables

- [x] Schedule-driven resumes update the canonical latest-launch pointer.
- [x] Schedule control rejects invalid launch-derived eval/checkpoint/bundle
  paths before detached eval/resume proceeds.
- [x] Durable checkpoint tests prove newest-`3` retention at the real boundary.
- [x] Task and runbook docs capture the remediation slice.

## Acceptance Criteria

- [x] After one schedule-driven resume, pointerless `qwen-train status` and
  `qwen-train stop` target the resumed launch rather than the stopped source
  launch.
- [x] Schedule control fails closed when launch metadata points at
  non-scratch-root or missing eval/checkpoint/bundle paths.
- [x] Focused tests explicitly prove retention-`3` keeps the newest three
  durable checkpoints after the fourth valid durable save.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_eval_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_schedule_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_checkpoint_persistence.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Notes

- Schedule-driven `_resume_from_checkpoint()` now updates the canonical latest
  detached launch pointer immediately after writing the resumed launch
  metadata.
- Schedule preflight now validates launch-derived defaults for checkpoint,
  eval-manifest, and bundle-root paths instead of only validating explicit CLI
  overrides.
- Durable checkpoint helper coverage now includes the shipped retention-`3`
  boundary by saving a fourth durable checkpoint and asserting newest-three
  retention plus truthful latest-pointer behavior.
