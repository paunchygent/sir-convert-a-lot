---
id: task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2
title: Remove v1 API CLI clients and contracts clean break to v2
type: task
status: proposed
priority: critical
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - v2
  - clean-break
  - api
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove v1 conversion surfaces and re-home required behavior in v2 so the platform has one API version only.

## PR Scope

- Remove v1 job routes and v1 client adapter usage from canonical paths.
- Add/lock `pdf -> md` under v2 route contract.
- Remove v1-specific compatibility logic from CLI routing.
- Remove v1 contract references from active converter docs where superseded.
- Preserve deterministic error envelope/idempotency behavior under v2.

## Deliverables

- [ ] v1 runtime routes and CLI branch logic removed.
- [ ] v2 `pdf -> md` route implemented and documented.
- [ ] Tests migrated from v1-path assumptions to v2-path assumptions.
- [ ] Docs updated for v2-only API usage.

## Acceptance Criteria

- [ ] Requests to previous v1 conversion routes are no longer part of supported API surface.
- [ ] CLI executes `pdf -> md` through v2 only.
- [ ] Contract tests pass for v2 `pdf -> md` lifecycle and result retrieval.
- [ ] No active docs recommend using v1 conversion endpoints.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
