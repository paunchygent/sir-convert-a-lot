---
id: story-14-v2-only-clean-break-and-api-surface-unification
title: V2 only clean break and API surface unification
type: story
status: in_progress
priority: critical
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - v2
  - api
  - clean-break
---
Implementation slice with acceptance-driven scope.

## Objective

Execute a strict clean break to a single v2 conversion API surface with no v1 compatibility lane,
while keeping the core behavior deterministic and operationally simple.

## Scope

- Remove v1 HTTP routes, v1 client paths, and v1-specific job spec/runtime handling where superseded by v2.
- Add/lock v2 `pdf -> md` route semantics so PDF-to-Markdown remains first-class under v2.
- Unify CLI route selection and transport so all conversions resolve to v2 surfaces only.
- Replace compatibility-policy language that assumes long-lived v1/v2 coexistence.
- Strengthen route and manifest contract clarity so callers can reason about one version.

## Acceptance Criteria

- [ ] `/v1/convert/jobs*` is removed from service and tests.
- [ ] CLI no longer branches to v1 for any route.
- [ ] v2 supports `pdf -> md` with deterministic idempotency, status, result, and error behavior.
- [ ] API/docs/ADR references no longer claim v1/v2 coexistence as active architecture.

## Test Requirements

- [ ] Add contract tests that assert v2-only route behavior for all supported routes.
- [ ] Add regression tests ensuring removed v1 paths do not reappear.
- [ ] Run full quality gates and docs validations.

## Done Definition

Single-version v2 API surface is the only conversion route in code, tests, and docs.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
