---
id: review-01-brutal-review-service-api-v2-multi-format-pivot
title: 'Brutal review: service API v2 multi-format pivot'
type: review
status: pending
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md
  - docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md
  - docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/backlog/tasks/task-39-hemma-v2-conversion-smoke-verification.md
  - docs/backlog/tasks/task-40-service-api-v2-contract-tests-v1-v2-compatibility-policy.md
  - docs/backlog/tasks/task-41-harden-v2-resources-zip-extraction-limits.md
  - docs/backlog/tasks/task-42-split-oversized-cli-and-v2-job-store-cancel-cas.md
labels:
  - review
  - v2
  - api
  - cli
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Surfaces reviewed:
  - v2 HTTP routes: `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
  - v2 runtime: `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
  - v2 job store: `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py`
  - v2 conversion executor: `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`
  - v2 HTTP client: `scripts/sir_convert_a_lot/interfaces/http_client_v2.py`
  - CLI router: `scripts/sir_convert_a_lot/interfaces/cli_routes.py`
  - CLI entrypoint: `scripts/sir_convert_a_lot/interfaces/cli_app.py`
  - v2 contract docs: `docs/converters/multi_format_conversion_service_api_v2.md`
- Validation evidence captured (local):
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q`

## Findings

- Blocker: SRP/size guardrail violations (`>500` LoC):
  - `scripts/sir_convert_a_lot/interfaces/cli_app.py` (~719 LoC)
  - `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py` (~542 LoC)
- High: cancellation state transition is not compare-and-swap safe.
  - Late cancel can overwrite terminal success (job ends “canceled” with an already-written
    artifact).
- High: resources zip extraction lacks zip-bomb limits (entry count / total uncompressed size).
- High: v2 has no service-side contract tests (current coverage is CLI tests with a stubbed v2
  client).
- Medium: v2 contract doc is incomplete vs implementation for `/result`, `/artifact`, and `/cancel`
  (pending `202`, terminal failure `409`, cancel response codes).
- Medium: docs governance drift: v2 contract marked `draft` and ADR-0002 marked `proposed` despite
  being exercised by service+CLI.
- Low: several converter utility module docstrings still describe “local CLI routes” after the
  remote-only pivot.

## Decision

Decision: `changes_requested`.

Approval requires:

1. Hemma v2 smoke evidence exists (docker runtime + tunnel-first submission works).
1. Service-side v2 contract tests exist and match normative docs.
1. Resources zip extraction is hardened against zip-bombs.
1. Cancellation is race-safe (CAS) and does not overwrite terminal success.
1. Oversized modules are split below the 500 LoC guardrail.
1. Backwards compatibility policy + v1/v2 contract unification path is explicitly documented.

## Response

Pending.

- Follow-up tasks have been created (Task 39–42) and will be linked to PRs/commits as they land.
- This review will move to `status: responded` once the response section contains a concrete list
  of accepted/rejected findings and the corresponding PR/task links.

## Follow-up Actions

1. `docs/backlog/tasks/task-39-hemma-v2-conversion-smoke-verification.md`
1. `docs/backlog/tasks/task-40-service-api-v2-contract-tests-v1-v2-compatibility-policy.md`
1. `docs/backlog/tasks/task-41-harden-v2-resources-zip-extraction-limits.md`
1. `docs/backlog/tasks/task-42-split-oversized-cli-and-v2-job-store-cancel-cas.md`

## Completion

Status lifecycle for this review:

- `pending`: findings recorded; response pending.
- `responded`: response recorded, with explicit acceptance/rejection of findings + linked PRs/tasks.
- `completed`: all accepted follow-up actions are complete, with validation evidence captured.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [ ] Response recorded
- [x] Follow-up tasks linked
- [ ] Review closed
