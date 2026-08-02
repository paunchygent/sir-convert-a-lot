---
id: task-42-split-oversized-cli-and-v2-job-store-cancel-cas
title: Split oversized CLI and v2 job store + cancel CAS
type: task
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md
  - docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - refactor
  - cli
  - job-store
  - cancel
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove SRP/maintainability violations introduced during the v2 pivot by splitting oversized modules
below the 500 LoC guardrail, and fix v2 cancellation semantics to be **compare-and-swap safe** so
late cancels cannot overwrite terminal success.

## PR Scope

- Split modules:
  - `scripts/sir_convert_a_lot/interfaces/cli_app.py` (currently >500 LoC)
  - `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py` (currently >500 LoC)
  - Preserve public import surfaces and CLI command behavior (no new UX flags in this task).
- Cancellation CAS fix:
  - Ensure cancel only transitions from `queued|running` -> `canceled` under the manifest lock.
  - Reject cancel attempts on terminal jobs (do not overwrite `succeeded|failed`).
  - Add a deterministic error envelope behavior for “cancel conflict” at the HTTP layer if needed.
- Tests:
  - Add a focused unit test that reproduces the “late cancel overwrites success” hazard and proves
    the CAS fix.
  - Keep existing CLI tests passing (may need to update import paths after refactor).

## Deliverables

- [x] Oversized modules are split below 500 LoC without behavior drift.
- [x] v2 cancellation is race-safe and cannot overwrite terminal success.
- [x] Regression tests exist for the cancellation hazard.

## Acceptance Criteria

- [x] `pdm run run-local-pdm typecheck-all` passes.
- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q` passes.
- [x] `pdm run run-local-pdm validate-tasks` and `validate-docs` pass.
- [x] Module sizes: both target modules are \<500 LoC after refactor.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
