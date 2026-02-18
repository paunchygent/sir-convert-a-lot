---
id: task-29-pdf-to-docx-hybrid-pipeline-service-pdf-md-local-md-html-docx
title: PDF to DOCX service pipeline (API v2)
type: task
status: in_progress
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md
  - docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md
  - docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - pdf
  - docx
  - service
  - v2
  - cli
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Deliver the critical pipeline `pdf -> docx` as a **service-executed** workflow via a
new multi-format **service API v2**, while keeping the locked PDF-to-MD **service v1**
contract unchanged.

The DOCX artifact must be produced on Hemma (dockerized service runtime), so the
client CLI is a thin remote submit/poll/download wrapper rather than a Pandoc/
WeasyPrint runtime.

## PR Scope

- Service v2 support:
  - `POST /v2/convert/jobs` accepts a PDF upload and a v2 job spec that requests `output_format="docx"`.
  - Job orchestration executes:
    - PDF -> Markdown using the existing backend routing + GPU governance rules (Docling-first),
    - Markdown -> HTML -> DOCX using Pandoc inside the service runtime.
  - Result retrieval supports binary artifacts (DOCX download).
- CLI support:
  - `convert-a-lot convert <pdf> --to docx --output-dir <dir>` uses service API v2.
  - Optional styling: `--reference-docx` is uploaded/attached to the v2 job.
- Determinism:
  - deterministic route selection, manifest semantics, and output path mapping,
  - bit-for-bit determinism of produced DOCX is **not** required.
- Error behavior:
  - Missing Pandoc in the service runtime must surface a deterministic error code (should not happen
    in properly built Hemma images, but must be diagnosable).
- Tests:
  - v2 route orchestration + artifact download tests (service-side and client-side).
- Docs:
  - explicitly document that this is a v2 route and does not change v1.

## Implementation Notes

- API contract:
  - Service v1 remains `pdf -> md` only.
  - Multi-format conversions are exposed via service API v2.
- Artifact retrieval:
  - DOCX is retrieved via a dedicated download endpoint (recommended) rather than JSON inline payloads.

## Deliverables

- [ ] Service API v2 `pdf -> docx` route implementation.
- [ ] Deterministic manifest emission for `pdf -> docx` via v2 from the CLI.
- [ ] Tests covering orchestration, error mapping, and manifest stability.
- [ ] CLI docs updated with `pdf -> docx` v2 usage.

## Acceptance Criteria

- [ ] Converting a fixture PDF to DOCX completes through the v2 service pipeline and produces a non-empty
  DOCX artifact downloaded by the CLI.
- [ ] Service v1 PDF-to-MD behavior and contract remain unchanged.
- [ ] Route manifest entries include the service `job_id` and final DOCX `output_path`.
- [ ] Missing Pandoc in the service runtime surfaces deterministic error codes and actionable messages.
- [ ] Tests and docs-as-code gates pass.

## Validation Evidence

- Local quality gates:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
