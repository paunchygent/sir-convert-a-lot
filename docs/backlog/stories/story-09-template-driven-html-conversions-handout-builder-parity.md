---
id: story-09-template-driven-html-conversions-handout-builder-parity
title: Template-driven HTML conversions (handout builder parity)
type: story
status: proposed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-32-html-css-to-pdf-route-weasyprint-with-deterministic-manifest.md
labels:
  - html
  - templates
  - pdf
  - docx
---

Implementation slice with acceptance-driven scope.

## Objective

Deliver parity for the legacy template-driven conversion workflows built around
`handout_templates/` and “written exam” templates by making them first-class
Sir Convert-a-Lot conversions.

## Scope

- HTML template batch builds:
  - `handout_templates/**/*.html` → PDF (`build/pdf`-style output layout).
  - `handout_templates/**/*.html` → DOCX (`build/docx`-style output layout).
- Standalone HTML-to-PDF:
  - `*.html` → PDF with explicit CSS support (`--css <file>`), for non-template use cases.
- Respect legacy template metadata where it is part of the workflow contract
  (example: supplementary print CSS injection flags).
- Provide a canonical Sir Convert-a-Lot CLI surface for template builds:
  - either as subcommands (`convert-a-lot handouts build …`) or via
    `convert-a-lot convert <dir> --from html --to pdf/docx`.
- Deterministic manifest emission for batch builds:
  - one entry per template file,
  - stable ordering and reproducible output paths.
- Document the “template contract” under `docs/converters/` as needed.

## Acceptance Criteria

- [ ] Batch template build to PDF works on a representative fixture set.
- [ ] Batch template build to DOCX works on a representative fixture set.
- [ ] Standalone HTML-to-PDF works with an explicit CSS file and produces deterministic output.
- [ ] CLI supports a stable, documented interface for template builds.
- [ ] Manifest is deterministic and captures failures per-template without aborting the whole batch.
- [ ] OS-level dependencies for chosen PDF/DOCX backends are documented and validated in Docker lane.

## Test Requirements

- [ ] Regression tests around template discovery and deterministic output layout.
- [ ] Smoke tests that produce non-empty PDF/DOCX artifacts for a minimal fixture template.

## Done Definition

Sir Convert-a-Lot can perform the legacy “handout builder” workflows through its
canonical CLI surface, with docs and deterministic manifests.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
