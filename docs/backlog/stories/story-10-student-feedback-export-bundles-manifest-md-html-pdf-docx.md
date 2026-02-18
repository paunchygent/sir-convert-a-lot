---
id: story-10-student-feedback-export-bundles-manifest-md-html-pdf-docx
title: Student feedback export bundles (manifest + md->html->pdf/docx)
type: story
status: proposed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-28-markdown-to-pdf-via-html-intermediary-pandoc-weasyprint.md
  - docs/backlog/tasks/task-30-markdown-to-docx-via-html-intermediary-pandoc.md
labels:
  - feedback
  - manifest
  - md
  - html
  - pdf
  - docx
---

Implementation slice with acceptance-driven scope.

## Objective

Provide a general, cohort-agnostic capability for exporting per-student feedback
Markdown files into layout-controlled PDF and DOCX artifacts, along with a
student/contact manifest derived from the documents.

Key requirements:

1. Parse **student name** and **email address** from each feedback Markdown document.
1. Use a **two-step** conversion flow for controlled layout:
   - `md -> html -> pdf`
   - `md -> html -> docx`

## Scope

- CLI surface:
  - Add a dedicated, stable CLI surface (preferred):
    `convert-a-lot feedback export <input-dir> --to pdf|docx|both --output-dir <dir>`.
  - Keep this workflow separate from the service-backed `convert` command to preserve the
    PDF-to-MD v1 service contract and existing CLI manifest semantics.
- Input discovery:
  - Discover `*.md` files in the input directory (non-recursive by default; recursive flag optional).
  - Deterministic ordering and stable `source_file_path` values (relative paths).
- Student metadata parsing:
  - YAML frontmatter is the canonical metadata source:
    - `student.name`
    - `student.email`
    - optional: `student.id`
  - Provide a compatibility fallback for legacy “header + bullet list” patterns
    (H1 title + `- **Email:** ...` lines) to support migration of older documents.
  - Fail fast with deterministic, user-actionable error codes when required metadata is missing.
- Export document shaping:
  - Allow template selection for export HTML rendering (minimum: one default template).
  - Support minimal sanitization so exported artifacts do not leak raw IDs/emails unless explicitly
    requested (default: include student name, exclude email).
- Rendering pipeline (two-step):
  - Step 1: Markdown → standalone HTML (Pandoc or a documented markdown renderer).
  - Step 2a: HTML → PDF (WeasyPrint) with configurable CSS.
  - Step 2b: HTML → DOCX (Pandoc) with optional reference `.docx`.
- Manifest:
  - Write a `feedback_manifest.csv` (or equivalent) containing at least:
    - `student_name`
    - `student_email`
    - `student_id` (optional)
    - `artifact_pdf_filename` / `artifact_docx_filename`
    - `source_md`
    - optional `share_url` column for manual upload workflows.
  - Deterministic row ordering and stable filename policy (reusable tokens optional).

## Acceptance Criteria

- [ ] Export command converts a fixture set of feedback markdown files to PDF and/or DOCX
  using the two-step pipeline (`md -> html -> pdf/docx`).
- [ ] Manifest contains parsed `student_name` + `student_email` for every successfully exported entry.
- [ ] Missing metadata or failed conversions are recorded deterministically (no partial silent failure).
- [ ] Export outputs are deterministic in naming and folder layout for the same inputs.
- [ ] Workflow is documented under `docs/converters/` (either as an extension of
  `docs/converters/sir_convert_a_lot.md` or a dedicated converter doc).

## Test Requirements

- [ ] Unit tests for student metadata parsing (frontmatter-first, legacy fallback).
- [ ] Unit tests for manifest emission stability and sorting.
- [ ] Smoke tests for HTML rendering and PDF/DOCX artifact creation on minimal fixtures.
- [ ] Negative tests for missing Pandoc/WeasyPrint dependencies (deterministic error codes).

## Done Definition

Sir Convert-a-Lot provides a cohort-agnostic “student feedback export” capability with
deterministic outputs and a manifest derived from the documents, suitable for downstream
distribution workflows.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
