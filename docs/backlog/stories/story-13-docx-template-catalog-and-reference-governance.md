---
id: story-13-docx-template-catalog-and-reference-governance
title: DOCX template catalog and reference governance
type: story
status: in_progress
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - template
  - docx
  - governance
---
Implementation slice with acceptance-driven scope.

## Objective

Provide a complete and reusable DOCX template model for conversion outputs, enabling multiple
practical reference templates that downstream GUI products can select without ad hoc file uploads.

## Scope

- Define template contract fields and lifecycle:
  - `template_id`, `name`, `description`, `domain_tags`, `version`, `status`, `artifact_sha256`.
- Define template selection semantics in v2 conversion job specs (typed and deterministic).
- Add API surfaces for template discovery and selection-ready metadata.
- Ship an initial curated template set (minimum three practical templates) for real usage.
- Define validation and governance rules for adding/updating templates.

## Acceptance Criteria

- [ ] V2 conversion contract includes typed template-selection semantics.
- [ ] Template catalog API supports list/get use cases needed by downstream GUIs.
- [ ] At least three practical reference DOCX templates are available and validated.
- [ ] Template usage is deterministic and auditable in result metadata and/or manifest fields.

## Test Requirements

- [ ] API contract tests for template list/get and conversion selection semantics.
- [ ] Validation tests for malformed templates and unsupported template IDs.
- [ ] Integration tests confirming template-selected conversions produce non-empty DOCX artifacts.

## Done Definition

DOCX template handling is productized as a governed API contract, not an ad hoc per-request file path.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
