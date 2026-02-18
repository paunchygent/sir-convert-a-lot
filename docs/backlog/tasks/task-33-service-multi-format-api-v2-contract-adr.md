---
id: task-33-service-multi-format-api-v2-contract-adr
title: Service multi-format API v2 contract + ADR
type: task
status: in_progress
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0002-multi-format-service-api-v2.md
labels:
  - docs-as-code
  - api
  - v2
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the normative docs-as-code contract for a multi-format conversion **service API v2** and
record the decision that v2 (not v1) is the expansion surface for server-side Pandoc/WeasyPrint
conversions on Hemma.

## PR Scope

- Create and populate:
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/decisions/0002-multi-format-service-api-v2.md`
- Document:
  - supported source/target routes,
  - resources bundle (zip) semantics,
  - binary artifact download endpoint requirement,
  - error envelope model for v2,
  - explicit v1 non-expansion statement.
- Update Epic 04 and related story/task links as needed.

## Deliverables

- [ ] Converter contract doc exists and is contract-valid
- [ ] ADR exists and is contract-valid
- [ ] Epic/story/task graph updated to reflect v2 pivot

## Acceptance Criteria

- [ ] `pdm run run-local-pdm validate-docs` passes
- [ ] `pdm run run-local-pdm validate-tasks` passes
- [ ] Contract explicitly preserves locked v1 scope while defining v2 expansion surface

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
