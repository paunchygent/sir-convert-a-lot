---
id: task-63-cli-auto-rerun-on-idempotent-failed-replays
title: Superseded CLI failed-replay workaround
type: task
status: completed
priority: high
created: '2026-03-01'
last_updated: '2026-06-29'
related:
  - docs/converters/sir_convert_a_lot.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md
labels:
  - cli
  - v2
  - ux
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Historical Task 63 introduced a CLI-side failed-replay workaround before
Service API v2 owned retryable failed reattempts.

This behavior is superseded. Task 368 moved retryable failed reattempts to
Service API v2, and Task 369 removed the caller-side compatibility wrapper.
This document is retained only as historical context and is no longer current
CLI or client behavior authority.

Current authority:

- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md`
- `docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md`

Current policy:

- Service API v2 owns retryable failed reattempts and exposes
  `idempotency.state = "service_reattempt"` when it admits a fresh active
  attempt for the same logical request.
- CLI/client invocations submit one create-job request for a conversion and
  record only the service-returned job in the manifest.
- `--new-job` is explicit independent user intent to start a separate
  conversion with a new `Idempotency-Key`; it is not failed-replay
  remediation.

## PR Scope

Superseded historical scope:

- The client exposed replay state before the service-owned JSON idempotency
  contract existed.
- The CLI provided temporary failed-replay UX around strict service
  idempotency.
- Task 369 removed that workaround from current runtime behavior.

## Deliverables

- [x] Historical workaround implemented in 2026-03-01 slice.
- [x] Superseded by Task 368 service-owned reattempt policy.
- [x] Runtime workaround removal governed by Task 369.

## Acceptance Criteria

Superseded historical acceptance is no longer current behavior authority. See
Task 368 and Task 369 for the accepted service-owned replacement and removal
evidence.

## Validation Commands

- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`

## Validation Evidence

- [x] Lint:
  - `pdm run run-local-pdm lint-fix` (pass, 2026-03-01).
- [x] Type safety:
  - `pdm run run-local-pdm typecheck-all`
    (pass: `Success: no issues found in 158 source files`, 2026-03-01).
- [x] Targeted tests:
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
    (pass: `15 passed`, 2026-03-01).
- [x] Full coverage gate:
  - `pdm run run-local-pdm coverage-gate`
    (pass: `397 passed, 5 skipped`; total coverage `95.24%`, 2026-03-01).
- [x] Docs gates:
  - `pdm run run-local-pdm validate-tasks` (pass: `Validated 88 backlog files`).
  - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=110 rules=9`).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
