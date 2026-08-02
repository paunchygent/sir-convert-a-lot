---
id: task-46-design-docx-template-contract-storage-and-selection-model
title: Design docx template contract storage and selection model
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/docx-template-catalog-contract-v2.md
labels:
  - template
  - contract
  - docx
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the canonical DOCX template contract and storage/governance model for conversion styling.

## PR Scope

- Specify typed template metadata and versioning rules.
- Define template selection fields in v2 conversion spec.
- Define storage layout and integrity fields (sha256, size, provenance).
- Define governance for adding/updating/removing templates.

## Deliverables

- [x] Contract document for DOCX template catalog and selection.
- [x] ADR or converter-doc update that locks template model decisions.
- [x] Backlog links for implementation and downstream integration tasks.

## Acceptance Criteria

- [x] Template contract is precise enough for API implementation without ambiguity.
- [x] Selection model supports multiple practical templates and domain tagging.
- [x] Validation rules cover unknown IDs, invalid files, and version drift.

## Execution Plan (Slice 46A, 2026-02-28)

1. Publish a dedicated v2 template contract document with normative schema and storage invariants.
1. Lock selection semantics (`conversion.template`) and error behavior for unknown ID/version/state.
1. Define read-only template discovery routes for downstream GUI domains.
1. Wire the template contract into the v2 converter API document and backlog links.
1. Run docs-as-code validation gates.

## Execution Outcome (Slice 46A, 2026-02-28)

- Published template contract:
  - `docs/converters/docx-template-catalog-contract-v2.md`
- Locked design decisions in docs:
  - canonical template metadata schema and lifecycle (`active|deprecated|disabled`),
  - v2 template selector shape and deterministic validation error expectations,
  - storage/integrity invariants (`sha256`, size, immutable version directories),
  - result/manifest audit metadata requirements (`template_id`, `template_version`, hash),
  - minimum initial curated template set (three practical templates).
- Synced the v2 converter contract surface:
  - linked the new template contract and documented selector and catalog route expectations.
- Preserved clean-break policy:
  - no v1 shim/deprecation language introduced.

### Validation Evidence

- `pdm run run-local-pdm validate-tasks` (pass; `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass; `Validated docs=103 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
