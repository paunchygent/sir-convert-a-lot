---
id: task-59-enforce-90-percent-test-coverage-gate-for-conversion-core
title: Enforce 90 percent test coverage gate for conversion core
type: task
status: completed
priority: critical
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

- [x] Coverage toolchain configured in `pyproject.toml` with `fail_under = 90`.
- [x] Canonical `coverage-gate` script available via `run-local-pdm`.
- [x] Epic/Story/task acceptance criteria reference `>=90%` coverage gate.
- [x] Validation evidence includes coverage command output.

## Acceptance Criteria

- [x] `pdm run run-local-pdm coverage-gate` fails when coverage is below 90%.
- [x] Coverage gate behavior is deterministic and documented for contributors.
- [x] Docs-as-code validators pass with updated coverage requirements.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence (2026-02-28)

- `pdm run run-local-pdm coverage-gate` failed with `Total coverage: 71.80%`, confirming
  fail-under enforcement at `90%`.
- `pdm run run-local-pdm typecheck-all` passed (`Success: no issues found in 129 source files`).
- `pdm run run-local-pdm coverage-gate` passed with `Total coverage: 92.77%`
  (`311 passed, 7 skipped`), confirming threshold enforcement and deterministic pass behavior.
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_read_cancel.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_paths.py tests/sir_convert_a_lot/test_v2_conversion_executor_general.py`
  passed (`57 passed`), confirming split-file refactor behavior.
- `pdm run validate-tasks` passed.
- `pdm run validate-docs` passed.
