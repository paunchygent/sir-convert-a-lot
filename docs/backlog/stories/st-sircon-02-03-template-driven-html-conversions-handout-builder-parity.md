---
type: story
id: ST-SIRCON-02-03
title: Template-driven HTML conversions (handout builder parity)
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
- Batch template build to PDF works on a representative fixture set.
- Batch template build to DOCX works on a representative fixture set.
- Standalone HTML-to-PDF works with an explicit CSS file and produces deterministic
  output.
- CLI supports a stable, documented interface for template builds.
- Manifest is deterministic and captures failures per template without aborting the
  whole batch.
- OS-level dependencies for chosen PDF and DOCX backends are documented and validated
  in the Docker lane.
retired_ids:
- story-09-template-driven-html-conversions-handout-builder-parity
---
## Context

Source record: docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md

### Objective

> Deliver parity for the legacy template-driven conversion workflows built around
> `handout_templates/` and “written exam” templates by making them first-class
> Sir Convert-a-Lot conversions.

## Epic Contract Slice

### Scope

> - HTML template batch builds:
>   - `handout_templates/**/*.html` → PDF (`build/pdf`-style output layout).
>   - `handout_templates/**/*.html` → DOCX (`build/docx`-style output layout).
> - Standalone HTML-to-PDF:
>   - `*.html` → PDF with explicit CSS support (`--css <file>`), for non-template use cases.
> - Respect legacy template metadata where it is part of the workflow contract
>   (example: supplementary print CSS injection flags).
> - Provide a canonical Sir Convert-a-Lot CLI surface for template builds:
>   - either as subcommands (`convert-a-lot handouts build …`) or via
>     `convert-a-lot convert <dir> --from html --to pdf/docx`.
> - Deterministic manifest emission for batch builds:
>   - one entry per template file,
>   - stable ordering and reproducible output paths.
> - Document the “template contract” under `docs/converters/` as needed.

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review
