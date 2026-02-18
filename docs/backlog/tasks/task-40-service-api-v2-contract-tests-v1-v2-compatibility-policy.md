---
id: task-40-service-api-v2-contract-tests-v1-v2-compatibility-policy
title: Service API v2 contract tests + v1/v2 compatibility policy
type: task
status: proposed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md
  - docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md
  - docs/decisions/0002-multi-format-service-api-v2.md
labels:
  - tests
  - contract
  - v1
  - v2
  - compatibility
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add service-side contract tests for the new v2 HTTP surface and explicitly define the **v1/v2
compatibility policy** for internal Hemma services, including a documented path towards contract
unification without breaking the locked v1 contract.

## PR Scope

- Tests:
  - Add `tests/sir_convert_a_lot/test_api_contract_v2.py` (FastAPI TestClient).
  - Stub `execute_v2_job_conversion()` to avoid requiring Pandoc/WeasyPrint in local test lanes.
  - Cover:
    - auth (`X-API-Key`) + standard error envelope (`api_version="v2"`)
    - idempotency replay + collision semantics (`X-Idempotent-Replay`, `409`)
    - `/result` and `/artifact` pending behavior (`202` with pending payload)
    - terminal failure behavior (`409 job_not_succeeded`)
    - cancel behavior response codes (`202 accepted`, `200 already_canceled`, `409 not_cancelable`)
- Docs contract sync:
  - Update `docs/converters/multi_format_conversion_service_api_v2.md` to document the full response
    matrix for `/result`, `/artifact`, and `/cancel` (pending + terminal-failure cases).
- Compatibility policy (unification path):
  - Add a short, explicit compatibility policy document under `docs/converters/` that defines:
    - versioning rules (no breaking changes inside v1/v2; breaking change => v3)
    - error envelope invariants shared across versions (shape, correlation id behavior)
    - idempotency semantics invariants shared across versions
    - the “unification path” target: shared envelope semantics + shared doc structure, without
      rewriting v1 routes
  - Update both v1 and v2 contract docs to link to this policy.

Notes:

- Service is internal today, but this policy prevents accidental drift before any future
  internet-facing exposure.

## Deliverables

- [ ] v2 service contract tests exist and run without external converter binaries.
- [ ] v2 contract doc reflects real endpoint semantics for pending/failed outcomes.
- [ ] Compatibility policy doc exists and is referenced by both v1 and v2 contracts.

## Acceptance Criteria

- [ ] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py -q` passes.
- [ ] `pdm run run-local-pdm validate-docs` passes after contract doc updates.
- [ ] v1 contract tests remain unchanged and continue passing.
- [ ] Compatibility policy explicitly states how v1/v2 stay compatible while converging on shared
  envelope semantics and stable response shapes.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
