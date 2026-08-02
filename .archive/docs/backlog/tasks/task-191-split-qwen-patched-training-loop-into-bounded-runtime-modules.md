---
id: task-191-split-qwen-patched-training-loop-into-bounded-runtime-modules
title: Split Qwen patched training loop into bounded runtime modules
type: task
status: completed
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-180-remediate-task-101-finite-loss-guard-failure-reporting-and-accumulation-step-correctness.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - architecture
  - runtime
  - training-loop
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Reduce the patched Qwen training loop to orchestration only and move resume
handling, train-step execution, phase transitions, loss runtime, and summary
projection into focused runtime modules that can be tested in isolation.

## PR Scope

- Extract bounded runtime modules from `sft_12hz_loop.py` without adding
  compatibility wrappers.
- Keep the optimizer-boundary guard and forensic helpers as dedicated owners
  rather than moving that logic back into the loop file.
- Add architecture guard tests so the loop and related hot-path files cannot
  regrow unnoticed.

## Deliverables

- [x] Focused runtime modules exist for resume runtime, train-step runtime,
  phase runtime, loss runtime, and summary projection.
- [x] `sft_12hz_loop.py` is reduced to top-level orchestration under the Story
  28 cap.
- [x] Focused train-step tests own the new runtime logic instead of enlarging
  `test_train_loop.py`.
- [x] Architecture guard tests enforce the line-count caps and banned-module
  regressions.

## Acceptance Criteria

- [x] The training loop file no longer mixes resume logic, optimizer-step
  execution, phase control, loss tracking, and summary building in one module.
- [x] The new runtime modules preserve truthful `diagnose-non-finite`,
  checkpoint/eval/stop, and failure-report behavior.
- [x] `test_train_loop.py` remains an integration surface rather than becoming
  the owner of all new runtime scenarios.
- [x] Permanent architecture guard tests fail if the hot-path modules exceed
  the cap or the old broad modules reappear.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
