---
id: task-190-replace-qwen-reporting-module-with-bounded-reporting-packages
title: Replace Qwen reporting module with bounded reporting packages
type: task
status: proposed
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
  - reporting
  - status
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Split the Qwen reporting/status surface into bounded modules so payload
building, failure projection, artifact I/O, runtime version discovery, and
writer configuration stop accumulating in one umbrella file.

## PR Scope

- Replace `reporting.py` with a reporting package composed of focused modules.
- Move canonical JSON artifact writing into one owner and remove duplication
  with metadata helpers.
- Preserve detached status/report truth while exposing the new diagnostic and
  optimizer-boundary fields already introduced by `T180/T186`.

## Deliverables

- [ ] Reporting modules exist for config, writer, status payloads, report
  builders, failure projection, step semantics, artifact I/O, and runtime
  versions.
- [ ] One canonical artifact-I/O owner exists for status/report JSON writes.
- [ ] The old `reporting.py` umbrella is removed rather than preserved as a
  compatibility layer.
- [ ] Focused tests cover status payload builders and failure projection.

## Acceptance Criteria

- [ ] Reporting/status/report-building concerns are separated on stable module
  boundaries under the Story 28 cap.
- [ ] `status.json`, `report.json`, and failure payloads stay contract-aligned
  after the refactor.
- [ ] Diagnostic launch kinds and optimizer-boundary failure fields remain
  visible and truthful in the new reporting package.
- [ ] No duplicate artifact-writing paths remain between reporting and
  metadata.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
