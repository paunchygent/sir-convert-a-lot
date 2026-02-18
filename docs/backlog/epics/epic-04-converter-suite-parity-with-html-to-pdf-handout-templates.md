---
id: epic-04-converter-suite-parity-with-html-to-pdf-handout-templates
title: Converter suite parity with html_to_pdf_handout_templates
type: epic
status: in_progress
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md
  - docs/backlog/stories/story-10-student-feedback-export-bundles-manifest-md-html-pdf-docx.md
  - docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md
  - docs/backlog/stories/story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md
  - docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - parity
  - multi-format
  - cli
  - consolidation
---

Major capability increment managed through linked stories.

## Goal

Bring the full conversion capability set currently available in the legacy repository
`html_to_pdf_handout_templates` under the canonical Sir Convert-a-Lot surfaces, with a
single default UX that submits work to the Hemma-hosted dockerized service:

- `pdm run convert-a-lot convert <source> --to <target> --output-dir <dir>`

The v1 service contract remains locked to `pdf -> md` only. Multi-format conversion
is delivered via a versioned **service API v2**, with the CLI acting as a thin
remote submit/poll/download wrapper (no laptop-local Pandoc/WeasyPrint requirements).

Epic 04 is complete only when **every legacy converter surface is either**:

- migrated into Sir Convert-a-Lot,
- wrapped behind Sir Convert-a-Lot as a compatibility layer,
- superseded by the canonical service/CLI,
- or explicitly marked out of scope (with rationale).

## In Scope

- Capability inventory + classification:
  - Maintain the canonical capability matrix and mapping:
    `docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md`.
- CLI multi-format routing:
  - Route detection and/or explicit `--from/--to` selection across `pdf/md/html/docx/image/audio`.
  - Deterministic manifest semantics for both service-backed and local conversions.
- Converter parity for the legacy document-conversion set:
  - template-driven HTML conversions (handout builder + written-exam template flows),
  - Pandoc/WeasyPrint document transforms (md/docx/pdf/txt),
  - auxiliary conversions that are already shipped as “converters” (image OCR extract, text-to-speech).
- Docs-as-code and contract sync:
  - CLI guide updates (`docs/converters/sir_convert_a_lot.md`),
  - per-converter docs as needed under `docs/converters/`,
  - explicit scope boundaries for excluded legacy scripts (no ambiguity).
- Validation gates:
  - tests for routing/manifest behavior,
  - smoke conversion fixtures per route class where feasible.

## Out of Scope

- Any silent expansion of the **PDF-to-MD service v1** contract beyond its locked scope.
  - Multi-format service support must be delivered as an explicit v2 contract (docs + tests).
- Grading/assessment workflows from the legacy repository.
- Org-/project-specific export workflows (example: Nate feedback export bundle).
- Public internet exposure of conversion endpoints.

## Stories

1. `docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md`
1. `docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md`
1. `docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md`
1. `docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md`
1. `docs/backlog/stories/story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech.md`
1. `docs/backlog/stories/story-10-student-feedback-export-bundles-manifest-md-html-pdf-docx.md`

## Task Order (Synergy-Optimized)

The first milestone for this epic is a **service-executed critical pipeline set** via API v2:

- `pdf -> md` (service v1; already implemented and being hardened under Story 02-01 tasks)
- `pdf -> docx` (service v2)
- `md -> html -> pdf` (service v2)
- `md -> html -> docx` (service v2)
- `html + css -> pdf` (service v2)
- CLI pivot: use service v2 for all non-`pdf -> md` routes

Execution order is optimized to:

- define v2 contracts first (ADR + converter docs),
- build shared service primitives (v2 job store/runtime + artifact download),
- then layer per-route backends on top,
- and finally pivot the CLI to remote-only behavior.

Ordered tasks:

1. `docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md`
1. `docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md`
1. `docs/backlog/tasks/task-37-service-v2-route-html-css-pdf-weasyprint.md`
1. `docs/backlog/tasks/task-36-service-v2-route-md-pdf-via-html-intermediary.md`
1. `docs/backlog/tasks/task-38-service-v2-route-md-docx-via-html-intermediary.md`
1. `docs/backlog/tasks/task-29-pdf-to-docx-hybrid-pipeline-service-pdf-md-local-md-html-docx.md`
1. `docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md`
1. `docs/backlog/tasks/task-39-hemma-v2-conversion-smoke-verification.md` (verification)
1. `docs/backlog/tasks/task-40-service-api-v2-contract-tests-v1-v2-compatibility-policy.md` (contracts)
1. `docs/backlog/tasks/task-41-harden-v2-resources-zip-extraction-limits.md` (hardening)
1. `docs/backlog/tasks/task-42-split-oversized-cli-and-v2-job-store-cancel-cas.md` (hardening)

## Acceptance Criteria

- [ ] Capability matrix is complete and kept current for this epic:
  `docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md`.
- [ ] Every legacy converter is classified as migrate/wrap/supersede/out_of_scope, with no “unknowns”.
- [ ] Canonical CLI supports all **migrate** routes with deterministic outputs and manifests.
- [ ] CLI manifest remains deterministic across all supported routes (service-backed and local).
- [ ] Docs and examples are updated for new CLI routes and flags.
- [ ] Focused regression tests exist for route selection + manifest emission, and pass in CI/local gates.
- [ ] Any new OS-level dependencies needed for converters are documented and validated in the Docker lane.

## Checklist

### Epic Hygiene

- [ ] Stories linked
- [ ] Acceptance criteria defined
- [ ] Execution gate defined (quality gates + parity completion definition)

### Critical Pipeline Tasks (Execution Order)

- [x] `docs/backlog/tasks/task-31-cli-route-registry-for-local-and-hybrid-conversions.md` (foundational)
- [x] `docs/backlog/tasks/task-32-html-css-to-pdf-route-weasyprint-with-deterministic-manifest.md` (converter primitive)
- [x] `docs/backlog/tasks/task-28-markdown-to-pdf-via-html-intermediary-pandoc-weasyprint.md` (converter primitive)
- [x] `docs/backlog/tasks/task-30-markdown-to-docx-via-html-intermediary-pandoc.md` (converter primitive)
- [ ] `docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md`
- [ ] `docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md`
- [x] `docs/backlog/tasks/task-37-service-v2-route-html-css-pdf-weasyprint.md`
- [x] `docs/backlog/tasks/task-36-service-v2-route-md-pdf-via-html-intermediary.md`
- [x] `docs/backlog/tasks/task-38-service-v2-route-md-docx-via-html-intermediary.md`
- [ ] `docs/backlog/tasks/task-29-pdf-to-docx-hybrid-pipeline-service-pdf-md-local-md-html-docx.md`
- [ ] `docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md`
- [x] `docs/backlog/tasks/task-39-hemma-v2-conversion-smoke-verification.md`
- [x] `docs/backlog/tasks/task-40-service-api-v2-contract-tests-v1-v2-compatibility-policy.md`
- [x] `docs/backlog/tasks/task-41-harden-v2-resources-zip-extraction-limits.md`
- [x] `docs/backlog/tasks/task-42-split-oversized-cli-and-v2-job-store-cancel-cas.md`
