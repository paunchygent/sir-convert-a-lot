---
id: task-36-service-v2-route-md-pdf-via-html-intermediary
title: 'Service v2 route: md -> pdf via html intermediary'
type: task
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md
  - docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0002-multi-format-service-api-v2.md
labels:
  - md
  - pdf
  - pandoc
  - weasyprint
  - v2
  - service
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Deliver the critical pipeline `md -> html -> pdf` as a **service-executed** conversion via service
API v2, where HTML is an internal intermediary stage used to control layout.

## PR Scope

- v2 job spec support:
  - `source.format="md"`, `conversion.output_format="pdf"`
  - optional `conversion.css_filenames` + optional `resources` zip bundle
- Service execution pipeline:
  - Markdown -> HTML via Pandoc
  - HTML(+CSS) -> PDF via WeasyPrint
- Error mapping:
  - missing Pandoc / missing WeasyPrint deps must surface deterministic error codes
  - missing CSS filenames must return a deterministic 422 (`css_not_found`)
- Determinism:
  - deterministic output paths and manifest entries (bit-for-bit PDF determinism not required)

## Deliverables

- [x] v2 conversion executor supports `md -> pdf` via HTML intermediary.
- [x] v2 routes accept `resources` and `css_filenames` and enforce CSS existence.
- [x] CLI routes `md -> pdf` via v2 (service-executed).

## Acceptance Criteria

- [x] Route exists and is exercised by the CLI via `/v2/convert/jobs/*`.
- [x] Local quality gates pass for the added v2 route implementation.
- [ ] Hemma docker-lane smoke evidence is captured (tracked under Task 39).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
