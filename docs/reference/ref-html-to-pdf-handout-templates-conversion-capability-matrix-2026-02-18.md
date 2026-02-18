---
type: reference
id: REF-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18
title: html_to_pdf_handout_templates conversion capability matrix
status: active
created: 2026-02-18
updated: 2026-02-18
owners:
  - platform
tags:
  - planning
  - parity
  - capability-matrix
  - cli
links:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md
  - docs/converters/sir_convert_a_lot.md
---

## Purpose

Inventory the conversion capabilities currently present in the legacy repository
`html_to_pdf_handout_templates` and map each capability to a Sir Convert-a-Lot
target outcome:

- **migrate**: implement as a first-class Sir Convert-a-Lot route (CLI and, when appropriate,
  service support).
- **wrap**: keep legacy behavior but call it through the canonical Sir Convert-a-Lot CLI surface
  as a thin compatibility layer.
- **supersede**: replace legacy behavior with the Sir Convert-a-Lot service/CLI (canonical).
- **out_of_scope**: explicitly excluded from Epic 04 (but still accounted for).

This reference is normative input to Epic 04 planning.

## Capability Matrix

| Legacy surface (repo-local) | Operation | Inputs | Outputs | Key deps / runtime notes | Sir Convert-a-Lot target | Status | Planned story |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pdm run convert:pdf-md` (`scripts/converters/convert_pdf_to_md.py`) | `pdf -> md` | `.pdf` | `.md` | CPU-oriented; legacy heuristics | `convert-a-lot convert <pdf> --to md` via service v1 | supersede | `docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md` |
| `pdm run convert:pdf-md-advanced` (`scripts/converters/convert_pdf_to_md_advanced.py`) | `pdf -> md` | `.pdf` | `.md` | Docling-driven; GPU-first intent | `convert-a-lot convert <pdf> --to md` via service v1 | supersede | `docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md` |
| New (Sir Convert-a-Lot route) | `pdf -> docx` | `.pdf` | `.docx` | Hybrid: service `pdf -> md` then local `md -> html -> docx` | `convert-a-lot convert <pdf> --to docx` | migrate | `docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md` |
| `pdm run build:pdf` (`scripts/handout_builder.py` + `scripts/converters/convert_html_to_pdf.py`) | `html(template) -> pdf` (batch) | `handout_templates/**/*.html` | `build/pdf/**/*.pdf` | WeasyPrint + template meta flags for print CSS injection | `convert-a-lot handouts build --to pdf` (batch manifest) | migrate | `docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md` |
| `pdm run build:docx` (`scripts/handout_builder.py`) | `html(template) -> docx` (batch) | `handout_templates/**/*.html` | `build/docx/**/*.docx` | Pandoc; reference docx optional | `convert-a-lot handouts build --to docx` (batch manifest) | migrate | `docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md` |
| `scripts/converters/convert_html_to_pdf.py` | `html + css -> pdf` | `.html` (+ optional `.css`) | `.pdf` | WeasyPrint; CSS injection supported | `convert-a-lot convert <html> --to pdf --css <file>` | migrate | `docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md` |
| `scripts/converters/convert_md_to_pdf.py` | `md -> pdf` | `.md` | `.pdf` (+ optional `.html` intermediate) | Pandoc → HTML → WeasyPrint; CSS optional | `convert-a-lot convert <md> --to pdf` | migrate | `docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md` |
| `scripts/converters/convert_md_to_docx.py` / `pdm run build:md-docx` | `md -> html -> docx` | `.md` | `.docx` | Pandoc; reference docx optional; HTML intermediary default | `convert-a-lot convert <md> --to docx` | migrate | `docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md` |
| `scripts/converters/docx_to_markdown.py` | `docx -> md` | `.docx` | `.md` | Pandoc required | `convert-a-lot convert <docx> --to md` | migrate | `docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md` |
| `scripts/converters/md_to_txt.py` | `md -> txt` | `.md` | `.txt` | Pandoc or lightweight markdown stripping | `convert-a-lot convert <md> --to txt` | migrate | `docs/backlog/stories/story-06-pandoc-weasyprint-document-converters-parity-md-pdf-docx-txt.md` |
| `scripts/convert_md_to_written_exam.py` | `md(exam) -> html/pdf` | `.md` exam spec | `.html` (+ `.pdf`) | Uses a written-exam template + html->pdf converter | `convert-a-lot exams build <md> --to pdf` (template-specific) | migrate | `docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md` |
| `scripts/skriptoteket_html_to_pdf.py` | `html -> pdf` (repo-specific wrapper) | `.html` | `.pdf` | Wrapper around html->pdf converter | `convert-a-lot convert <html> --to pdf` | supersede | `docs/backlog/stories/story-09-template-driven-html-conversions-handout-builder-parity.md` |
| `scripts/converters/extract_text_from_image.py` | `image -> txt` | `.png/.jpg/...` | `.txt` | Requires system `tesseract` + `pytesseract` | `convert-a-lot convert <image> --to txt` (OCR mode) | migrate | `docs/backlog/stories/story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech.md` |
| `pdm run convert:tts` (`scripts/converters/text_to_speech.py`) | `text/md -> audio` | `.txt/.md` | `.mp3/.wav/...` | Requires API key; remote API dependency | `convert-a-lot speak <file> --voice <...>` | migrate | `docs/backlog/stories/story-07-auxiliary-converters-parity-image-ocr-extract-text-to-speech.md` |
| Generalize from `scripts/converters/export_nate_2026_feedback.py` | `student feedback md -> manifest + pdf/docx` | `*.md` feedback docs | per-student PDFs/DOCX + `feedback_manifest.csv` | Two-step layout-controlled pipeline: `md -> html -> pdf/docx` | `convert-a-lot feedback export <dir> --to pdf|docx|both` | migrate | `docs/backlog/stories/story-10-student-feedback-export-bundles-manifest-md-html-pdf-docx.md` |
| `pdm run export:nate-feedback` (`scripts/converters/export_nate_2026_feedback.py`) | `nate2026 feedback export + emails` | project-specific inputs | per-student PDFs + `manifest.csv` + `.eml` drafts | Org-/cohort-specific workflow and messaging | Explicitly excluded (keep as legacy-specific) | out_of_scope | N/A |

## Routing Policy (Draft)

1. Prefer the **service** (Hemma) for heavy workloads (e.g., PDF-to-MD) where GPU governance and
   retention/idempotency semantics matter.
1. Prefer **local CLI execution** for:
   - deterministic single-host transforms (Pandoc/WeasyPrint),
   - template builds where the templates/assets live in the caller repo,
   - conversions with external API keys (TTS) where callers already manage credentials.
1. Any introduction of **multi-format service routes** must be versioned and contract-documented
   (do not silently expand v1 beyond its locked PDF-to-MD contract).

## Known Risks / Gaps

- **System dependencies**: WeasyPrint, Pandoc, and Tesseract require non-Python OS packages.
  Docker and Hemma runbooks must be updated before claiming parity is complete.
- **Manifest semantics**: some legacy workflows produce multiple artifacts per source (e.g.,
  exam HTML + PDF). The CLI manifest may need a v2 shape or a well-defined “primary artifact”
  convention to remain deterministic.
