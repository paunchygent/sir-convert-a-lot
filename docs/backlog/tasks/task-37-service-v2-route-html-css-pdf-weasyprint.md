---
id: task-37-service-v2-route-html-css-pdf-weasyprint
title: 'Service v2 route: html + css -> pdf (WeasyPrint)'
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
  - html
  - pdf
  - css
  - weasyprint
  - v2
  - service
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Deliver the critical pipeline `html + css -> pdf` as a **service-executed** conversion via service
API v2, enabling template-driven HTML rendering on Hemma without laptop-local WeasyPrint.

## PR Scope

- v2 job spec support:
  - `source.format="html"`, `conversion.output_format="pdf"`
  - optional `conversion.css_filenames` referencing entries in the extracted resources root
  - optional `resources` zip bundle upload
- Service execution pipeline:
  - HTML(+CSS) -> PDF via WeasyPrint with a stable `base_url` for relative assets
- Error mapping:
  - missing CSS filenames: deterministic 422 (`css_not_found`)
  - missing WeasyPrint deps: deterministic error code surfaced via v2 error envelope

## Deliverables

- [x] v2 conversion executor supports `html -> pdf` with optional CSS injection.
- [x] v2 routes accept `resources` and enforce CSS existence.
- [x] CLI routes `html -> pdf` via v2 (service-executed).

## Acceptance Criteria

- [x] Route exists and is exercised by the CLI via `/v2/convert/jobs/*`.
- [x] Local quality gates pass for the added v2 route implementation.
- [ ] Hemma docker-lane smoke evidence is captured (tracked under Task 39).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
