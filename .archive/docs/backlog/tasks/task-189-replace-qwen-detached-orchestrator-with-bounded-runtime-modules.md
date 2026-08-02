---
id: task-189-replace-qwen-detached-orchestrator-with-bounded-runtime-modules
title: Replace Qwen detached orchestrator with bounded runtime modules
type: task
status: completed
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - architecture
  - detached-runtime
  - orchestration
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the mixed-concern detached Qwen host runtime with bounded
detached-runtime modules so ids, path construction, Docker command building,
launch, inspection, artifact freshness, and stop behavior have separate
owners.

## PR Scope

- Create a dedicated detached-runtime package for Qwen training launches.
- Move command construction, detached launch, detached inspection, and stop
  control into separate modules.
- Remove the old `orchestrator.py` umbrella after import migration.
- Keep detached launch/status/report behavior stable for operators.

## Deliverables

- [x] Bounded detached-runtime modules exist for ids, settings snapshots,
  paths, command building, launch, inspection, artifact freshness, and stop.
- [x] All internal imports are migrated away from the old mixed-concern module.
- [x] The old `orchestrator.py` file is deleted rather than kept as a shim.
- [x] Focused tests cover detached command building and status inspection.

## Acceptance Criteria

- [x] No mixed-concern detached-runtime module exceeds the Story 28 cap.
- [x] Detached launch/status/report artifacts remain truthful after import
  migration.
- [x] Resumed-launch stale-artifact filtering remains correct on the new module
  boundaries.
- [x] No compatibility wrapper or deprecated alias module remains.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
