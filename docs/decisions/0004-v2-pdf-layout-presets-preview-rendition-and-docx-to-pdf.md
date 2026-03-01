---
type: decision
id: ADR-0004
title: V2 PDF Layout Presets, Preview Rendition, and DOCX to PDF
status: proposed
created: 2026-03-01
updated: 2026-03-01
owners:
  - platform
tags:
  - v2
  - pdf
  - presets
  - preview
  - docx
links:
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
---
## Status

- Proposed
- Date: 2026-03-01

## 1. Problem and Context

Downstream products (Skriptoteket, Projektveckor, and later HuleEdu) are moving to a curated,
GUI-driven conversion interface that must treat Sir Convert-a-Lot **v2** as the canonical
multi-format conversion engine.

Today, v2 has two gaps for that GUI:

1. PDF outputs lack a first-class, typed layout control surface.
   - Only `conversion.css_filenames` exists, which pushes basic page setup (paper size, orientation,
     margins, page-break ergonomics) into ad hoc CSS conventions per client.
2. v2 does not support `docx -> pdf`.
   - Downstream GUIs need an authoritative PDF artifact output from DOCX inputs without relying on
     repo-local scripts or sidecar conversion tools.

Additionally, “preview” behavior needs to be defined so downstream UIs do not invent parallel
conversion systems. “Preview” here means “produce a PDF suitable for immediate UI display” and is
not a separate “partial output” format.

## 2. Decision

1. Add **PDF layout presets** to the v2 JobSpec as a typed, PDF-only contract surface:
   `conversion.pdf_layout`.
2. Add a v2 conversion route: `docx -> pdf`, implemented as `docx -> html (pandoc) -> pdf (weasyprint)`.
3. Define “preview rendition” as a **normal v2 job** producing a PDF artifact:
   - no new output format,
   - no v1 surfaces,
   - downstream UIs use existing job creation + polling/push to obtain artifacts,
   - preview jobs should be unpinned (`retention.pin: false`) unless the UI explicitly wants to keep
     the artifact.

## 3. Scope and Versioning

- Applies to **service API v2 only**.
- No v1 behavior, endpoints, or shims are introduced.
- Contract additions are backward compatible for existing v2 clients:
  - `conversion.pdf_layout` is optional,
  - `docx -> pdf` is an additive route.

## 4. Chosen Approach

### 4.1 PDF Layout Presets via Deterministic Generated CSS

- `conversion.pdf_layout` is compiled into a deterministic CSS stylesheet generated inside the job
  workdir, and passed into the existing WeasyPrint path as an additional stylesheet.
- The generated stylesheet is produced from **typed fields only** (no raw CSS injection surface).

### 4.2 DOCX to PDF via Pandoc HTML + WeasyPrint

- Avoid `pandoc -> pdf` directly to prevent a TeX/LaTeX toolchain dependency.
- Use Pandoc to produce standalone HTML and extract embedded media into the job workdir.
- Use the existing WeasyPrint wrapper with restricted `url_fetcher` so the pipeline is workdir-only.

## 5. Contract Rules

### 5.1 New Field: `conversion.pdf_layout`

Rules:

- Only valid when `conversion.output_format == "pdf"`.
- Schema (v2):
  - `paper_size`: `"a5" | "a4" | "a3"` (default: `"a4"`)
  - `orientation`: `"portrait" | "landscape"` (default: `"portrait"`)
  - `margins_mm`: integer millimeters (default: `12`; bounds defined in spec)
  - (Optional extension reserved): future fields for “page-break ergonomics” and “page numbers”.

Precedence:

- When `conversion.pdf_layout` is present, the generated preset stylesheet is applied as the
  **authoritative page setup**.
- `conversion.css_filenames` remains supported for additional styling, but clients must not depend
  on overriding the preset’s `@page size` semantics.

### 5.2 New Route: `docx -> pdf`

Rules:

- Route is supported for `source.kind == "upload"`.
- `reference_docx_filename` and `template` are not supported for PDF outputs and must remain
  rejected deterministically by v2 spec validation.
- `conversion.css_filenames` and `conversion.pdf_layout` are both supported for PDF output styling.

### 5.3 Preview Rendition

Rules:

- “Preview” is not a distinct output format and is not a separate conversion engine.
- UIs must use the same v2 job lifecycle and artifact download endpoint(s).
- Preview jobs should use `retention.pin: false` by default.

## 6. Security Model

- WeasyPrint must continue to enforce a restricted `url_fetcher`:
  - block external network schemes (`http/https/...`),
  - block `file://` access outside the job workdir.
- Pandoc stages used by v2 must be invoked with `--sandbox`.
- Any extracted media (DOCX images) must be written under the job workdir only.

## 7. Operational Model

- No new infrastructure is introduced.
- All stages must remain bounded by `execution.document_timeout_seconds` (or the route’s explicit
  default timeout policy).
- Pipelines must emit `pipeline_used` and `backend_used` strings for downstream observability and
  operational triage.

## 8. Rollout and Rollback

Rollout:

- Land contract + docs first (Task 64), then implement presets (Task 65), then implement `docx -> pdf`
  (Task 66).
- Verify on Hemma using the existing v2 verification harness and smoke fixture conversions.

Rollback:

- If the new route/preset behavior causes regressions, rollback is performed via standard deploy
  rollback to the prior container image (no partial “compat shims” in the API surface).

## 9. Consequences

Positive:

- Downstream UIs get a small, typed, stable surface for common PDF layout needs (A5/A4/A3,
  portrait/landscape, standard margins).
- `docx -> pdf` becomes a canonical v2 route, eliminating ad hoc conversion tooling in downstream
  repos.
- “Preview” is defined as the canonical v2 lifecycle (no parallel engines).

Tradeoffs:

- Presets are opinionated; clients needing exotic layout control still use additional CSS, but the
  platform remains the source of truth for page setup.
- Some DOCX fidelity differences may exist vs other DOCX renderers; this is accepted in exchange
  for a deterministic, sandboxed pipeline under one platform.
