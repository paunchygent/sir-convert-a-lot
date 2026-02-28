---
id: story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md
title: Markdown ingestion routes docx to md and html to md
type: story
status: in_progress
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md
  - docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - markdown
  - routes
  - downstream-api
---

Implementation slice with acceptance-driven scope.

## Objective

Complete the v2 route graph for Markdown-oriented ingestion so downstream GUIs can convert
DOCX/HTML/PDF inputs into normalized Markdown through one clear API surface.

## Scope

- Add v2 `docx -> md` route with deterministic normalization and stable error mapping.
- Add v2 `html -> md` route with resource-root resolution and deterministic normalization.
- Ensure `pdf -> md` remains available through v2 in the unified route taxonomy.
- Define route contract language that is explicit for downstream parent/child domains:
  Skriptoteket, HuleEdu, and Projektveckor.
- Ensure route metadata is sufficiently explicit for GUI orchestration (route key, source format,
  target format, status lifecycle, and artifact/result retrieval rules).

## Acceptance Criteria

- [ ] V2 supports all required Markdown pathways: `pdf -> md`, `docx -> md`, `html -> md`.
- [ ] Route behavior is deterministic and documented in converter/API docs.
- [ ] Downstream integration contract is published with request/response examples.
- [ ] CLI route listing and error messaging reflect the expanded Markdown ingress set.

## Test Requirements

- [ ] Contract tests for each Markdown ingress route (queued/running/succeeded/failed transitions).
- [ ] Normalization regression tests on representative fixtures for DOCX/HTML/PDF sources.
- [ ] Negative tests for unsupported combinations and resource/template mismatches.

## Done Definition

Markdown ingestion is complete and coherent under v2, with no ambiguous route behavior for UI integrators.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
