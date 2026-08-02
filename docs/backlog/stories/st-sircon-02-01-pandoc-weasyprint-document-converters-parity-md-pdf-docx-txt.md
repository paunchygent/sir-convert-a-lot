---
type: story
id: ST-SIRCON-02-01
title: Pandoc/WeasyPrint document converters parity (md<->pdf/docx/txt)
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-02
links:
  decisions: []
acceptance_criteria:
- Each route is supported via the canonical CLI surface and documented with examples.
- Missing dependency conditions are detected and mapped to deterministic error codes.
- Conversion outputs are deterministic for the same inputs, with no timestamped filenames
  by default.
- The Docker lane documents and validates OS dependencies for WeasyPrint and Pandoc,
  or clearly states which routes are local-only and why.
retired_ids:
- story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

Implementation slice with acceptance-driven scope.

### Objective

Bring the legacy Pandoc/WeasyPrint-based document converters into Sir Convert-a-Lot as
first-class CLI routes with deterministic outputs and predictable dependency behavior.

### Scope

- Implement (or port) the following conversion routes:
  - `md -> pdf` (Pandoc → HTML → WeasyPrint), with optional CSS input.
  - `md -> html -> docx` (Pandoc), with optional reference `.docx`.
  - `md -> txt` (deterministic plain-text export).
  - `docx -> md` (Pandoc).
- Dependency governance:
  - define what is required at runtime (Pandoc binary, OS packages for WeasyPrint),
  - fail with deterministic, user-actionable error codes when dependencies are missing.
- Integrate with the canonical CLI routing story:
  - no ad hoc entrypoints outside `convert-a-lot`,
  - consistent output-dir and manifest behavior for both single files and directory batches.

### Acceptance Criteria

- [ ] Each route is supported via the canonical CLI surface and documented with examples.
- [ ] Missing dependency conditions are detected and mapped to deterministic error codes.
- [ ] Conversion outputs are deterministic for the same inputs (no timestamped filenames by default).
- [ ] Docker lane has documented and validated OS deps for WeasyPrint + Pandoc (or clearly states
  which routes are “local-only” and why).

### Test Requirements

- [ ] Unit tests for route option validation (e.g., supported `--to` targets for `.md` and `.docx`).
- [ ] Smoke tests that create output files for minimal fixtures per route.
- [ ] Negative tests for missing Pandoc/WeasyPrint dependencies (deterministic error codes).

### Done Definition

Legacy document converters are usable through Sir Convert-a-Lot with stable behavior,
tests, and docs; no repo-specific converter scripts remain required for these routes.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
