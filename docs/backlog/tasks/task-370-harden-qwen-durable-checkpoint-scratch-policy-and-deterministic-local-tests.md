---
id: task-370-harden-qwen-durable-checkpoint-scratch-policy-and-deterministic-local-tests
title: Harden Qwen durable checkpoint scratch policy and deterministic local tests
type: task
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-153-retain-only-bounded-durable-qwen-training-checkpoints-and-guard-scratch-capacity-on-hemma.md
  - docs/backlog/tasks/task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift.md
  - docs/backlog/tasks/task-183-control-checkpoint-cadence-and-retention-for-scheduled-task-101-qwen-training.md
  - docs/backlog/tasks/task-242-establish-permanent-docker-visible-hemma-bind-roots-for-scratch-backed-qwen-runtimes.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - checkpoints
  - scratch
  - testing
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make Qwen durable trainer-state checkpoint writes scratch-policy explicit and
make local checkpoint tests deterministic. Real durable Qwen checkpoints must
only be created on the configured Hemma scratch-backed run root; local macOS
temp space is not valid operational evidence for real checkpoint capacity.

## PR Scope

- Add a focused Qwen checkpoint path policy that fails closed when real
  training output/checkpoint roots escape the configured scratch build root.
- Enforce that policy through the Qwen detached training control-plane/runtime
  boundary rather than inside the public CLI composition root.
- Preserve the existing durable free-space guard:
  `estimated_checkpoint_bytes + durable_checkpoint_min_free_bytes`.
- Update local checkpoint lifecycle tests so positive behavior tests do not
  depend on the actual free space of the local macOS temp filesystem.
- Keep one negative test proving the production free-space floor still fails
  closed with the conservative first-save estimate.
- Retain SRP/DDD boundaries from Story 28 and Rule 095; do not reintroduce
  broad Qwen orchestrator/reporting modules or compatibility shims.

Out of scope:

- Lowering the production `16 GiB` durable checkpoint headroom.
- Treating local disk free space as accepted Qwen runtime capacity evidence.
- Launching a real Hemma training run or changing experiment conclusions.
- Changing Qwen training objective, checkpoint cadence, or retention policy.
- Stopping, pruning, deleting, or moving existing Hemma scratch artifacts.

## Deliverables

- [x] Scratch-policy enforcement for Qwen durable checkpoint/run roots.
- [x] Deterministic local positive tests for durable checkpoint lifecycle.
- [x] Negative free-space guard test that retains the production capacity floor.
- [x] Focused tests for escaped output/run/checkpoint paths at the control-plane
  boundary.
- [x] Retained ruthless review artifact for this task.

## Acceptance Criteria

- [x] Any real Qwen detached training launch/resume/capture/diagnostic path that
  would write durable trainer-state checkpoints outside the configured
  scratch build root fails before container execution.
- [x] The fail-closed diagnostic names the offending path and expected scratch
  root without suggesting local temp space is acceptable.
- [x] Local unit tests for successful checkpoint save, prune, retry, pointer,
  and resume metadata behavior pass regardless of host filesystem free
  space.
- [x] The production checkpoint free-space guard still requires the conservative
  estimated checkpoint size plus the configured minimum headroom.
- [x] The implementation keeps hot-path Qwen modules under Rule 095 size limits
  and adds Google-style module docstrings to new or materially changed
  Python modules.
- [x] The retained review is approved before the task is marked completed.

## Red/Green Plan

Expected red proof:

- Add or update a focused test that proves an escaped Qwen run/checkpoint root
  is rejected before Docker command construction or container launch.
- Reproduce the current environment-coupled weakness by running a positive
  durable checkpoint persistence test without faking free-space headroom on a
  filesystem below the production first-save floor, or document why that exact
  red condition cannot be reproduced deterministically on the current machine
  and use a targeted monkeypatched low-space test for the same failure mode.

Expected green proof:

- Focused Qwen checkpoint/control-plane tests pass.
- Positive checkpoint lifecycle tests no longer consult real local free space.
- The low-space negative test still fails closed at the production floor.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_checkpoint_persistence.py tests/sir_convert_a_lot/ml/qwen/training/test_detached_runtime_command_builder.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py -q`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Review

- Approved in
  `docs/backlog/reviews/review-53-ruthless-review-of-task-370-qwen-durable-checkpoint-scratch-policy.md`.
