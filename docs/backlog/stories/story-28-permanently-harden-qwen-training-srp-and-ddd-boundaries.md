---
id: story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries
title: Permanently harden Qwen training SRP and DDD boundaries
type: story
status: completed
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - architecture
  - ddd
  - srp
  - solid
---

Implementation slice with acceptance-driven scope.

## Objective

Permanently remove the god-file pressure in the Task 101 Qwen control-plane and
patched training runtime by codifying a stricter `400` LoC SRP/DDD policy and
refactoring the current mixed-concern modules into bounded, testable domain
packages.

## Scope

- Create the permanent architecture-governance lane for the Qwen training
  control plane as a separate story from `T186`.
- Refactor `qwen_train.py` into a true composition root backed by bounded
  control-plane use-case modules.
- Replace the detached host runtime orchestration layer with bounded
  detached-runtime modules.
- Replace the reporting/status umbrella module with bounded reporting packages.
- Split the patched training loop into bounded runtime modules aligned to
  resume, train-step, phase-control, loss-runtime, and summary concerns.
- Add architecture guard tests that fail when god files return.

Out of scope:

- public CLI renames or flag removals,
- new compatibility wrappers for old internal imports,
- broad training-objective changes beyond the architecture refactor.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-187-define-and-codify-qwen-training-control-plane-architecture-rules.md`
1. `docs/backlog/tasks/task-188-refactor-host-qwen-cli-control-plane-use-cases-out-of-qwen-train-py.md`
1. `docs/backlog/tasks/task-189-replace-qwen-detached-orchestrator-with-bounded-runtime-modules.md`
1. `docs/backlog/tasks/task-190-replace-qwen-reporting-module-with-bounded-reporting-packages.md`
1. `docs/backlog/tasks/task-191-split-qwen-patched-training-loop-into-bounded-runtime-modules.md`

## Acceptance Criteria

- [x] Story 28 is the explicit blocker on further growth in the current Qwen
  control-plane and runtime god files.
- [x] A repo rule makes the `400` LoC cap and SRP/DDD/DRY/SOLID boundaries
  normative for this lane.
- [x] `qwen_train.py` is reduced to a composition root and no longer owns
  bundle validation, path policy, or use-case orchestration.
- [x] The detached host runtime is split into bounded modules and the old
  mixed-concern `orchestrator.py` is removed.
- [x] The reporting/status/report-building lane is split into bounded modules
  and the old mixed-concern `reporting.py` is removed.
- [x] The patched Qwen training loop is split into bounded runtime modules and
  the old loop file is reduced to orchestration only.
- [x] Architecture guard tests enforce the new boundaries and line-count caps.

## Test Requirements

- [x] Focused tests exist for control-plane use cases, detached-runtime
  command/inspect behavior, reporting payload builders, and train-step runtime.
- [x] Integration tests still prove truthful detached launch/status/report and
  `diagnose-non-finite` behavior after import migration.
- [x] Architecture guard tests fail if the named hot-path modules exceed the
  cap or if old mixed-concern module paths reappear.

## Done Definition

Done when the four current god files are deleted or reduced to bounded
composition roots under the new cap, all Qwen training tests pass, and the
runbook/skill/current-task memory point at Story 28 as the permanent
architecture guardrail. This is now delivered in commit `338a0df`.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
