---
id: task-47-implement-docx-template-endpoints-validation-and-fixture-templates
title: Implement docx template endpoints validation and fixture templates
type: task
status: proposed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
labels:
  - template
  - api
  - validation
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement API-ready template catalog behavior with real reference templates and robust validation.

## PR Scope

- Add template catalog endpoints (list/get and selection-ready payloads).
- Add template ingestion/validation flow as allowed by contract.
- Add initial practical template fixtures for real production use.
- Integrate template selection into DOCX-producing conversion routes.

## Deliverables

- [ ] Working template catalog API surface.
- [ ] Validation logic + deterministic error mapping.
- [ ] Minimum three practical fixture templates available.
- [ ] Converter docs updated with template usage examples.

## Acceptance Criteria

- [ ] Template list/get routes are stable and typed.
- [ ] Template-selected conversions produce non-empty DOCX artifacts.
- [ ] Unknown template IDs return deterministic validation errors.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
