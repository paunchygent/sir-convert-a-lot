---
id: task-192-add-ml-specific-quality-gates-and-importlib-safe-qwen-test-collection
title: Add ML-specific quality gates and importlib-safe Qwen test collection
type: task
status: completed
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/current.md
labels:
  - qwen
  - ml
  - quality-gates
  - testing
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add explicit ML-only quality-gate commands so the Qwen preprocessing/training
lane can be validated quickly without always paying the cost of the full
repo-wide gate, while keeping the gate truthful to the real ML code surface.

## PR Scope

- Add a dedicated `test-ml` PDM script for the Qwen ML subtree.
- Make the ML pytest lane importlib-safe so duplicate test basenames such as
  `test_support.py` in preprocessing and training do not break collection.
- Add a dedicated `typecheck-ml` PDM script that covers the real Qwen ML code
  surface:
  - `scripts/sir_convert_a_lot/cli/ml`
  - `scripts/sir_convert_a_lot/ml/qwen`
  - `scripts/devops/qwen_finetuning_patches`
  - `tests/sir_convert_a_lot/ml/qwen`
- Fix any newly exposed mypy issues in that scoped ML lane rather than hiding
  them behind a narrower or misleading gate.
- Update current task memory and handoff context so future contributors know
  the canonical fast ML gates.

## Deliverables

- [x] `test-ml` exists as a PDM-owned command and collects the full Qwen ML
  subtree without duplicate-module import errors.
- [x] `typecheck-ml` exists as a PDM-owned command and covers the real Qwen ML
  code surface, including the patched runtime modules.
- [x] The newly exposed ML type issues are fixed so the scoped gate is green.
- [x] Docs and session memory mention the new ML-specific quality gates.

## Acceptance Criteria

- [x] `pdm run test-ml` passes for `tests/sir_convert_a_lot/ml/qwen`.
- [x] `pdm run typecheck-ml` passes for the scoped ML paths without excluding
  the patched Qwen runtime.
- [x] The repo keeps `test` / `typecheck-all` as the broad gates, while the new
  ML commands are clearly documented as the fast Qwen lane.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-ml`
- [x] `pdm run test-ml`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
