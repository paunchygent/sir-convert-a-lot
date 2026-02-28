---
id: 'task-59-enforce-90-percent-test-coverage-gate-for-conversion-core'
title: 'Enforce 90 percent test coverage gate for conversion core'
type: 'task'
status: 'proposed'
priority: 'critical'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - pyproject.toml
labels:
  - quality-gate
  - coverage
  - testing
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Enforce a hard `>=90%` automated test coverage gate for the conversion core so quality requirements
are measurable and non-negotiable in local and CI workflows.

## PR Scope

- Add/confirm coverage tooling in project dependencies and config.
- Add a canonical coverage command in PDM scripts:
  - `pdm run run-local-pdm coverage-gate`
- Lock fail-under threshold at 90 for the conversion-core source tree.
- Update active Epic/Story acceptance language to reference the 90% gate.
- Ensure docs/rules quality-gate references include the coverage gate command.

## Deliverables

- [ ] Coverage toolchain configured in `pyproject.toml` with `fail_under = 90`.
- [ ] Canonical `coverage-gate` script available via `run-local-pdm`.
- [ ] Epic/Story/task acceptance criteria reference `>=90%` coverage gate.
- [ ] Validation evidence includes coverage command output.

## Acceptance Criteria

- [ ] `pdm run run-local-pdm coverage-gate` fails when coverage is below 90%.
- [ ] Coverage gate behavior is deterministic and documented for contributors.
- [ ] Docs-as-code validators pass with updated coverage requirements.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
