---
type: converter
id: CONV-docx-template-catalog-contract-v2
title: DOCX Template Catalog Contract v2
status: active
created: 2026-02-28
updated: 2026-02-28
owners:
  - platform
tags:
  - v2
  - docx
  - templates
  - contract
links:
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/converters/multi_format_conversion_service_api_v2.md
---

## Purpose

Define the normative v2 contract for governed DOCX templates used by conversion routes that produce
DOCX artifacts.

This document locks:

- typed template metadata,
- selection semantics in conversion requests,
- template storage and integrity requirements,
- validation/error behavior for template selection,
- audit metadata required in conversion results/manifests.

## Scope

In scope:

- `md -> docx`, `html -> docx`, `pdf -> docx` template selection behavior.
- Template catalog listing/discovery contract for GUI consumers.
- Template artifact governance (versioning, status, integrity, provenance).

Out of scope:

- Runtime implementation details of Pandoc/HTML conversion internals.
- Non-DOCX output template systems.

## Normative Template Metadata Schema

Each template version record MUST include:

- `template_id`: stable slug identifier (for example `academic-report`).
- `version`: semver-like version string (`major.minor.patch`).
- `name`: display name for GUI selection.
- `description`: short functional intent.
- `domain_tags`: array of canonical tags (`skriptoteket`, `hule`, `projektveckor`, `general`).
- `language_tags`: optional array (`sv-SE`, `en-US`).
- `status`: `active | deprecated | disabled`.
- `artifact_filename`: canonical file name (`template.docx`).
- `artifact_sha256`: lowercase SHA256 hex for artifact bytes.
- `artifact_size_bytes`: non-zero size.
- `created_at`: RFC3339 timestamp.
- `updated_at`: RFC3339 timestamp.
- `provenance`: object with at least:
  - `source`: `internal_curated | migrated | external_provided`,
  - `owner`: team or service owner id,
  - `change_note`: short change rationale.

## Selection Contract in v2 JobSpec

For routes with `conversion.output_format="docx"`, callers SHOULD provide a template selector.

Normative selector shape:

```json
{
  "conversion": {
    "output_format": "docx",
    "template": {
      "template_id": "academic-report",
      "version": "1.0.0"
    }
  }
}
```

Rules:

- `template.template_id` is required for DOCX outputs once template APIs are enabled.
- `template.version` is optional:
  - omitted means “latest active version” resolution at request time,
  - provided means strict version pinning.
- Unknown `template_id` MUST return `422 validation_error` with
  `details.field="conversion.template.template_id"`.
- Unknown version for a known template MUST return `422 validation_error` with
  `details.field="conversion.template.version"`.
- Disabled templates MUST return `409 template_unavailable`.
- Requests that specify template selection for non-DOCX outputs MUST return `422 validation_error`.

Compatibility note:

- Existing `conversion.reference_docx_filename` remains an internal implementation bridge during
  migration, but external callers SHOULD use `conversion.template` as the canonical contract.

## Template Catalog API Contract (Discovery)

The following read surfaces are reserved for GUI integrations:

- `GET /v2/templates/docx`
  - returns active/deprecated template summaries for selection UIs.
- `GET /v2/templates/docx/{template_id}`
  - returns template metadata + available versions.
- `GET /v2/templates/docx/{template_id}/versions/{version}`
  - returns one resolved version metadata record.

Response metadata MUST include `template_id`, `version`, `status`, `domain_tags`,
`artifact_sha256`, and `artifact_size_bytes`.

## Storage and Integrity Model

Canonical storage layout:

```text
<data_root>/templates/docx/<template_id>/<version>/template.docx
<data_root>/templates/docx/<template_id>/<version>/metadata.json
```

Integrity invariants:

- Stored artifact bytes MUST hash to `artifact_sha256`.
- Stored artifact size MUST equal `artifact_size_bytes`.
- Metadata writes MUST be atomic and version-addressed.
- Mutating an existing version in place is forbidden; publish a new version instead.

## Governance Rules

- Template lifecycle: `active -> deprecated -> disabled`.
- `active` templates are eligible for default resolution.
- `deprecated` templates remain selectable when explicitly pinned.
- `disabled` templates are never selectable.
- New templates/versions require:
  - metadata completeness,
  - integrity verification,
  - changelog/provenance note.

## Result/Manifest Audit Requirements

Successful DOCX conversions MUST expose selected template audit fields in result metadata and/or
CLI manifest entries:

- `template_id`
- `template_version`
- `template_artifact_sha256`

This guarantees deterministic traceability for downstream GUIs and incident triage.

## Initial Curated Template Set (Minimum)

The first implementation slice MUST ship at least three practical templates:

- `academic-report` (formal academic document defaults)
- `classroom-handout` (teaching/worksheet style)
- `project-week-summary` (project-week report layout)
