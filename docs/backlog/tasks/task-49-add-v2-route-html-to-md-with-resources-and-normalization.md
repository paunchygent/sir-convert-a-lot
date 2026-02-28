---
id: task-49-add-v2-route-html-to-md-with-resources-and-normalization
title: Add v2 route html to md with resources and normalization
type: task
status: proposed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - markdown
  - route
  - html
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement `html -> md` as a first-class v2 route with deterministic handling of resources and normalization.

## PR Scope

- Extend v2 route validator and executor for HTML to Markdown conversion.
- Reuse resources bundle extraction and enforce clear resource-resolution semantics.
- Apply deterministic Markdown normalization and warning behavior.
- Add contract + usage docs for HTML markdown-ingress workflows.

## Deliverables

- [ ] `html -> md` v2 route implemented.
- [ ] Resource-resolution behavior documented and tested.
- [ ] Deterministic normalization and error mapping for missing/invalid resources.

## Acceptance Criteria

- [ ] HTML input converts to Markdown under v2 lifecycle semantics.
- [ ] Missing required resources produce deterministic, actionable errors.
- [ ] Route appears in CLI route diagnostics and API docs.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
