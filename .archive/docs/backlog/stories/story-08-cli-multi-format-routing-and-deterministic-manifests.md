---
id: story-08-cli-multi-format-routing-and-deterministic-manifests
title: CLI multi-format routing and deterministic manifests
type: story
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md
  - docs/backlog/tasks/task-31-cli-route-registry-for-local-and-hybrid-conversions.md
  - docs/backlog/tasks/task-29-pdf-to-docx-hybrid-pipeline-service-pdf-md-local-md-html-docx.md
  - docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md
  - docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md
  - docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - cli
  - routing
  - manifest
---

Implementation slice with acceptance-driven scope.

## Objective

Evolve the canonical Sir Convert-a-Lot CLI (`convert-a-lot`) from “PDF-to-MD only”
to a multi-format conversion router while preserving:

- the existing default UX (“convert x to y”),
- deterministic manifest semantics,
- and the locked PDF-to-MD service v1 contract.

This story is the CLI “spine” that all converter parity work plugs into.

Historical note:

- The original “locked v1 pdf->md” compatibility language in this story has been superseded by
  Epic 05 v2-only clean-break execution. Route unification is now fully v2.

## Scope

- Define and document a conversion **route taxonomy** (source kind → target format):
  - explicit `--to` (required),
  - optional `--from` override (otherwise inferred from file extension),
  - optional “engine/backend” selection per route where multiple implementations exist.
- Support single-step and multi-step routes:
  - **service-backed** (`pdf -> md` via v1),
  - **service-backed v2** (multi-format: `md/html/pdf -> pdf/docx`),
  - internal multi-step pipelines where required (example: `pdf -> docx` as `pdf -> md -> html -> docx`),
    executed inside the service runtime on Hemma.
- Extend CLI to route primarily to service execution:
  - **service v1** for `pdf -> md`,
  - **service v2** for all other in-scope routes.
- Manifest semantics:
  - keep `CliManifestEntry` deterministic (`source_file_path`, `job_id`, `status`, `output_path`, `error_code`),
  - define a clear convention for routes that produce multiple artifacts (primary artifact or manifest v2).
- CLI UX primitives:
  - `convert-a-lot routes` (or equivalent) to list supported routes and engines.
  - `--dry-run` for route selection transparency (no conversion execution).
- Backwards compatibility:
  - existing `convert-a-lot convert <pdfs> --to md` must remain stable.

## Acceptance Criteria

- [x] Critical pipeline set is implemented and documented:
  - `pdf -> md`
  - `pdf -> docx`
  - `md -> html -> pdf`
  - `md -> html -> docx`
  - `html + css -> pdf`
- [x] CLI supports at least the full set of **planned** routes from the capability matrix
  (even if some executors are initially stubbed behind “not yet implemented” errors).
- [x] PDF-to-MD route remained stable through Epic 04 delivery and was later unified under v2 in
  Epic 05 clean-break execution.
- [x] Route selection is deterministic and transparent (documented and test-covered).
- [x] Manifest conventions for non-PDF-to-MD routes are specified and validated by tests.
- [x] CLI documentation is updated with examples for each route group.

## Test Requirements

- [x] Unit tests for route inference (`--from` override, file extension inference, directory scans).
- [x] Unit tests for manifest emission ordering and error-code mapping.
- [x] CLI golden tests for `--dry-run` output (stable).

## Done Definition

Default CLI surface can act as the single entrypoint for converter parity work, with
stable routing, documented semantics, and regression coverage.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
