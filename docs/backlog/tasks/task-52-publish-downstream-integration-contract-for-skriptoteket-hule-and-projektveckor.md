---
id: task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor
title: Publish downstream integration contract for Skriptoteket Hule and Projektveckor
type: task
status: proposed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - integration
  - downstream
  - api
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish a clear API integration contract for downstream GUI consumers in Skriptoteket, HuleEdu, and Projektveckor.

## PR Scope

- Define canonical request/response examples for key v2 routes and template selection.
- Define polling/result/artifact handling patterns for GUI clients.
- Define deterministic error-handling guidance for user-facing products.
- Provide integration guidance for route capability discovery and version assumptions.

## Deliverables

- [ ] Integration contract document with practical route examples.
- [ ] Error-handling and polling guidance suitable for frontend/backend integrators.
- [ ] Linked references from converter docs and runbooks.

## Acceptance Criteria

- [ ] Downstream teams can implement conversion GUI flows without reverse-engineering backend assumptions.
- [ ] Integration guide covers Markdown ingress + DOCX template selection pathways.
- [ ] Guidance stays aligned with active v2 contract and test evidence.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
