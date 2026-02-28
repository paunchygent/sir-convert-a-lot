---
id: task-50-remove-eval-container-and-simplify-compose-runtime-topology
title: Remove eval container and simplify compose runtime topology
type: task
status: proposed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - runtime
  - docker
  - cleanup
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove eval-lane container complexity and keep one canonical runtime topology for production-oriented conversion workflows.

## PR Scope

- Remove eval container service definitions and associated profile paths.
- Remove eval app entrypoint/surfaces when no longer needed.
- Update runbooks and operational scripts for single-runtime assumptions.
- Keep readiness/liveness and GPU governance checks intact.

## Deliverables

- [ ] Compose/runtime definitions simplified to one canonical conversion service topology.
- [ ] Eval entrypoint codepaths removed or archived outside active runtime surface.
- [ ] Operational docs and scripts updated.

## Acceptance Criteria

- [ ] `docker compose config` no longer includes eval conversion lane for canonical workflow.
- [ ] Existing smoke checks pass against the single canonical runtime.
- [ ] No active docs require or reference eval container usage for normal operations.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
