---
type: decision
id: ADR-0008
title: Curated App-Owned PDF Exports Stay Out of Sir Convert V2
status: accepted
created: 2026-03-26
updated: 2026-03-26
owners:
  - platform
tags:
  - adr
  - api
  - boundary
  - downstream
  - html
  - pdf
  - v2
links:
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/backlog/tasks/task-249-add-trusted-app-bundle-mode-for-internal-html-to-pdf-exports.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

Define the service boundary for app-owned downstream PDF artifacts so Sir
Convert-a-Lot stays focused on general conversion workloads rather than taking
on renderer-owned export artifacts from products such as Klassrumskartan.

## Status

- Accepted
- Date: 2026-03-26

## 1. Problem and Context

Task 249 was opened to make Klassrumskartan-owned `html -> pdf` bundles work
through Sir Convert-a-Lot without losing bundled local assets.

That diagnosis was correct about the immediate seam, but it pointed at the
wrong long-term solution. The hard part was not missing authorization
machinery; it was that Klassrumskartan’s teacher-facing PDF artifacts are
renderer-owned exports that already live naturally inside Skriptoteket.

Running those artifacts through Sir Convert-a-Lot adds distributed-system
complexity that the downstream app does not need:

- extra job orchestration,
- callback/poll reconciliation,
- additional auth/config coupling,
- service-boundary latency for a controlled local renderer.

Sir Convert-a-Lot still makes sense for:

- public/general-purpose `html/css -> pdf`,
- `pdf -> md`,
- `pdf -> docx`,
- `docx -> pdf`,
- and other cross-format conversion surfaces exposed through dedicated
  conversion UIs such as Conversion Hub.

## 2. Decision

Keep curated app-owned downstream PDF exports **out of Sir Convert v2**.

### 2.1 Service boundary

Sir Convert-a-Lot v2 remains the canonical async conversion service for
general-purpose conversion workloads and public conversion surfaces.

It is not the preferred final-rendering boundary for app-owned curated-app
artifacts that:

- are generated from a controlled local presentation model,
- already have an in-process renderer,
- and do not need cross-format service orchestration.

### 2.2 Downstream rule

Downstream products such as Skriptoteket must render their own curated
app-owned PDF export artifacts locally when those artifacts are owned by the
product renderer.

Examples:

- Klassrumskartan seating PDF: local in Skriptoteket
- Klassrumskartan grouping PDF: local in Skriptoteket

### 2.3 What stays in Sir Convert

Sir Convert keeps:

- public/general-purpose `html/css -> pdf`
- `pdf -> md`
- `pdf -> docx`
- `docx -> pdf`
- `html -> docx`
- `html -> md`
- and similar conversion workloads where the service boundary adds real value

## 3. Consequences

### Positive

- Sir Convert stays simpler and more focused.
- Downstream apps avoid unnecessary async service orchestration for their own
  renderer-owned exports.
- Ownership, latency, and verification get easier for local artifact lanes.

### Costs

- If trusted-bundle code exists in the runtime, it becomes a cleanup/removal
  target rather than a surface to expand.
- Downstream docs that previously steered app-owned PDF exports into Sir Convert
  must be updated together with the owning app docs.

## 4. Follow-up

- Update Task 249 to reflect that the original trusted-bundle direction is
  superseded for Klassrumskartan.
- Track runtime cleanup separately in Task 251 so the dead curated-app path is
  deleted rather than quietly retained.
- Update converter contracts so they no longer present app-owned downstream PDF
  exports as a Sir Convert integration target.
- Keep public/general-purpose `html/css -> pdf` as a supported Sir Convert
  route.
