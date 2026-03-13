---
id: task-163-define-saturation-oriented-task-101-qwen-launch-profiles-and-acceptance-gates-on-hemma
title: Define saturation-oriented Task 101 Qwen launch profiles and acceptance gates on Hemma
type: task
status: proposed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-156-activate-first-class-mlflow-and-accelerate-tracking-for-task-101-qwen-training.md
  - docs/backlog/tasks/task-158-make-high-resolution-hemma-resource-monitoring-default-for-long-task-101-qwen-runs.md
  - docs/backlog/tasks/task-159-correct-task-101-checkpoint-cadence-and-step-semantics-for-throughput-oriented-qwen-runs.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - profiles
  - acceptance
  - saturation
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace today’s effectively unbounded ad hoc launch posture with explicit Task
101 run profiles and one documented saturation-oriented acceptance gate.

## Why This Exists

The live `2026-03-13` run used sentinel-like settings such as `num_epochs=1000`
and `max_steps=1000000` while also carrying a debug-friendly checkpoint
cadence. That makes it too easy to launch the wrong operational posture for the
wrong purpose.

## PR Scope

- Define explicit Task 101 launch profiles such as:
  - `smoke`
  - `profile`
  - `pilot-long`
  - `convergence`
- Bind each profile to an explicit default posture for:
  - checkpoint cadence
  - tracker behavior
  - monitor resolution
  - profiler enablement
  - duration / max-step expectations
- Document the canonical saturation gate:
  - `>= 90%` median GPU busy
  - `>= 10` contiguous steady-state non-checkpoint minutes
  - `<= 1.0` second monitor sampling
- Keep the CLI and runbook explicit about which profile is intended for which
  operational goal.

## Non-Goals

- Do not itself implement precomputed bundle mels.
- Do not itself resolve MIOpen warnings.
- Do not broaden this slice into a new evaluation protocol.

## Deliverables

- [ ] Explicit Task 101 launch profiles documented in code and runbook docs.
- [ ] One canonical saturation acceptance gate for Story 26.
- [ ] Launch metadata records the selected profile.
- [ ] Current story/reference/current-log docs point at the same acceptance
  target.

## Acceptance Criteria

- [ ] A Task 101 launch can be classified unambiguously as smoke, profile,
  pilot-long, or convergence.
- [ ] Each profile selects a coherent default policy instead of leaving the
  operator to assemble settings manually.
- [ ] The story-level success gate is documented as `>= 90%` median GPU busy
  over a steady-state non-checkpoint window, not as a vague throughput claim.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
