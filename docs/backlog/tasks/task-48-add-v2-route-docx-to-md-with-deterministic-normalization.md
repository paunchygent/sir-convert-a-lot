---
id: task-48-add-v2-route-docx-to-md-with-deterministic-normalization
title: Add v2 route docx to md with deterministic normalization
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
  - docx
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement `docx -> md` as a first-class v2 route with deterministic normalization and predictable errors.

## PR Scope

- Extend v2 source format and route validators for DOCX input.
- Implement converter execution path for DOCX to Markdown.
- Apply normalization profile and warnings semantics consistently.
- Add route docs and examples for API + CLI use.

## Deliverables

- [ ] `docx -> md` v2 route implemented end-to-end.
- [ ] Deterministic normalization + metadata output for DOCX conversions.
- [ ] Contract tests and fixture-based regression coverage.

## Acceptance Criteria

- [ ] DOCX input can be submitted via v2 and returns Markdown artifact/result deterministically.
- [ ] Invalid or corrupt DOCX inputs produce deterministic validation/input errors.
- [ ] Route is documented in v2 converter contract and CLI usage docs.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
