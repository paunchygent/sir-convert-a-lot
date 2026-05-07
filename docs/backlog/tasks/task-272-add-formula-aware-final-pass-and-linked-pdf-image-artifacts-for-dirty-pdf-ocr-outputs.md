---
id: task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs
title: Add formula-aware final pass and linked PDF/image artifacts for dirty PDF OCR outputs
type: task
status: proposed
priority: high
created: '2026-04-30'
last_updated: '2026-04-30'
related:
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md
  - docs/backlog/reviews/review-10-ruthless-review-of-story-39-follow-up-task-272-and-task-273-drafts.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py
  - scripts/sir_convert_a_lot/infrastructure/docling_formula_quality.py
labels:
  - ocr
  - pdf
  - formula
  - images
  - output-contract
  - dirty-data
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Improve dirty PDF OCR output quality by repairing unresolved Docling formula
placeholders, publishing a full OCR PDF companion artifact, and preserving
non-Markdown visual content as linked artifacts without turning the main OCR
path into repeated formula-model load/unload work.

The Task 271 Syntes long-document proof produced `168`
`<!-- formula-not-decoded -->` markers. Those markers appear in formula-heavy
chemistry equation sections and are unacceptable as the final quality shape for
dirty textbook OCR.

## PR Scope

- Choose this exact v2 public artifact contract before implementation:
  - `GET /v2/convert/jobs/{job_id}/artifact` remains the primary Markdown
    artifact and keeps content type `text/markdown`; existing clients do not
    need to change.
  - Add `GET /v2/convert/jobs/{job_id}/artifact/bundle` for successful
    PDF-to-Markdown jobs when companion artifacts exist.
  - The bundle response content type is `application/zip`.
  - The ZIP root contains:
    - `output.md`: the same Markdown bytes as the primary artifact,
    - `artifact-manifest.json`: the companion artifact manifest,
    - `companion/ocr-output.pdf`: a full generated OCR PDF companion,
    - `assets/images/page-<page>-image-<index>.<ext>` for extracted visual
      assets.
  - Markdown links point to relative bundle paths such as
    `assets/images/page-0007-image-0001.png`; they must be clickable after the
    bundle is unpacked.
  - `GET /v2/convert/jobs/{job_id}/result` adds only manifest summary fields,
    not raw file bytes:
    `companion_artifacts_available`, `companion_bundle_content_type`,
    `companion_bundle_manifest_sha256`, `companion_bundle_size_bytes`, and
    `companion_artifact_counts`.
  - No separate arbitrary path retrieval endpoint is introduced in this task;
    this avoids path traversal risk and keeps authorization identical to the
    existing job artifact route.
  - `/artifact/partial` and checkpoint payloads do not expose companion
    artifact references. Companion artifacts are terminal-only and are
    published only after finalization succeeds.
- Define companion artifact lifecycle and privacy semantics:
  - the companion PDF is a full generated OCR PDF deliverable, not a
    byte-for-byte copy of the original upload and not merely a Markdown support
    preview,
  - the companion PDF preserves all source pages in order, includes a searchable
    OCR text layer where supported by the selected implementation, and strips
    original document metadata, embedded files, annotations/comments,
    attachments, original filenames, and private paths,
  - the original upload filename, private source root, and local/Hemma operator
    paths must never appear in Markdown links, bundle member names, result
    fields, checkpoint payloads, or manifests,
  - bundle member names are deterministic, relative, and job-scoped,
  - companion artifacts inherit the same job ownership/auth checks as the
    primary artifact,
  - companion artifacts inherit the job retention policy, including pinning,
    cleanup, cancellation cleanup, deletion, and expiry,
  - if a companion artifact cannot be generated, the manifest records
    `status=unavailable` plus a safe reason code; it must not silently link a
    missing file.
- Define `artifact-manifest.json` schema before implementation:
  - `schema_version`,
  - `primary_artifact`: relative path, content type, size, sha256,
  - `companion_pdf`: relative path, content type, size, sha256, status,
  - `images`: page number, relative path, content type, size, sha256,
    markdown anchor/id, extraction status,
  - `residual_placeholders`: counts for `formula_not_decoded` and bare image
    markers,
  - `privacy`: booleans proving no source path, original filename, or OCR
    excerpt is included.
- Add a formula-aware final-pass strategy for PDF-to-Markdown jobs:
  - keep the first pass on the existing fast OCR path,
  - detect pages/chunks whose Markdown contains `<!-- formula-not-decoded -->`,
  - after the first pass completes, run one bounded formula-aware final pass for
    the affected page/chunk set using `table_mode=accurate` / Docling formula
    enrichment,
  - avoid per-chunk ping-pong where the formula model is repeatedly loaded and
    unloaded during the primary conversion loop,
  - merge improved formula-aware content back into the terminal Markdown with
    source/chunk provenance and deterministic warnings when placeholders remain.
- Preserve visual content and searchable OCR review output:
  - produce a retained full OCR PDF companion artifact for PDF-to-Markdown jobs,
  - extract image/object artifacts into a stable sibling folder or bundle
    subfolder,
  - replace bare `<!-- image -->` markers with deterministic relative links or
    Markdown image references to extracted artifacts,
  - include an output manifest that maps source pages, Markdown anchors,
    extracted artifacts, and retained full OCR PDF companion paths.
- Keep API and artifact behavior explicit:
  - document the selected ZIP bundle contract in the v2 API docs,
  - do not silently break existing clients that expect the primary artifact to
    be Markdown,
  - no private PDFs, raw OCR excerpts, or PII-bearing source paths may be
    committed as test or evidence artifacts.
- Keep module boundaries small:
  - formula detection/selection logic belongs outside the core backend class,
  - linked artifact manifest generation belongs outside checkpoint assembly,
  - bundle creation and manifest validation belong in a dedicated artifact
    module, not inside `v2_pdf_checkpointed_executor.py`,
  - new or materially changed Python modules need Google-style module
    docstrings.
- Execute in this required internal order:
  1. Update API docs and tests for the selected bundle/manifest contract.
  1. Add a small companion-artifact manifest/bundle module.
  1. Add formula-placeholder page/chunk selection and final-pass merge modules.
  1. Wire the terminal artifact route and result metadata.
  1. Run the Hemma dirty-corpus quality probe.

## Out Of Scope

- Replacing EasyOCR or Docling with a new OCR engine.
- Running the Task 271 performance proof again.
- Claiming performance improvement from this quality slice.
- Committing private Syntes source PDFs or raw OCR excerpts.

## Review Gate

- Review 10 re-reviewed and approved this draft on 2026-04-30.
- Implementation must preserve the selected ZIP bundle contract, companion
  PDF/image privacy and lifecycle semantics, and the required internal execution
  order below.

## Deliverables

- [ ] Formula-placeholder detection and one-shot final-pass orchestration.
- [ ] Deterministic merge/provenance behavior for formula-aware replacement
  content.
- [ ] ZIP bundle endpoint with full OCR PDF companion, linked image/object
  extraction, and artifact manifest.
- [ ] API/converter docs describing the multi-artifact output shape.
- [ ] Focused tests with synthetic or generated fixtures only.
- [ ] Hemma dirty-corpus quality probe showing reduced unresolved formula
  placeholders and linked image/object outputs without private artifact commits.

## Acceptance Criteria

- [ ] A PDF-to-Markdown job that emits `<!-- formula-not-decoded -->` after the
  fast pass schedules one final formula-aware pass for all affected pages/chunks
  together, not one load/unload cycle per marker or per normal chunk.
- [ ] If formula enrichment improves output, terminal Markdown contains the
  improved formula-aware content and records which chunks/pages were replaced.
- [ ] If formula enrichment cannot decode some formulas, the remaining
  placeholder count is surfaced in warnings/metadata and the job does not
  silently look clean.
- [ ] Bare `<!-- image -->` markers are replaced by deterministic relative links
  or Markdown image references when extractable image/object artifacts exist.
- [ ] Full OCR PDF companion and extracted image/object artifacts are retained
  in `GET /v2/convert/jobs/{job_id}/artifact/bundle` with content type
  `application/zip`.
- [ ] The OCR PDF companion contains all source pages in original order,
  strips original metadata/attachments/comments/private filenames, and exposes
  a searchable OCR text layer where the selected implementation supports one.
- [ ] `GET /v2/convert/jobs/{job_id}/artifact` remains Markdown-only and
  byte-compatible with the primary `output.md` member in the bundle.
- [ ] `artifact-manifest.json` contains only relative bundle paths, content
  types, sizes, sha256 digests, page numbers, extraction statuses, safe reason
  codes, and privacy booleans.
- [ ] Existing `/v2` clients can still retrieve the primary Markdown artifact;
  the new bundle route is documented and tested.
- [ ] Tests prove artifact paths are relative, stable, and do not leak private
  source roots or original private filenames.
- [ ] Tests prove companion artifacts inherit primary artifact authorization and
  job retention/pinning/deletion behavior.
- [ ] Tests prove checkpoint payloads do not expose terminal companion artifact
  paths before finalization.
- [ ] Tests prove the final-pass strategy is disabled for clean documents and
  bounded for documents with many markers.
- [ ] Dirty-corpus quality evidence reports before/after counts for
  `formula-not-decoded`, image placeholders, remaining warnings, and Swedish
  diacritic counts without storing OCR excerpts in git.

## Entry Points

- `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
- `scripts/sir_convert_a_lot/infrastructure/docling_formula_fallback.py`
- `scripts/sir_convert_a_lot/infrastructure/docling_formula_quality.py`
- new SRP-focused companion artifact manifest/bundle module
- `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
- `docs/converters/multi_format_conversion_service_api_v2.md`

## Test Requirements

- [ ] Unit tests for formula-placeholder detection, affected chunk/page
  selection, bounded final-pass scheduling, and merge behavior.
- [ ] API/contract tests for primary Markdown retrieval plus companion
  bundle retrieval.
- [ ] Regression tests for relative linked image/object paths and no private
  path leakage.
- [ ] Regression tests for auth/ownership, retention cleanup, deletion cleanup,
  and no checkpoint companion-artifact leakage before terminal finalization.
- [ ] Focused dirty-corpus Hemma probe may use private inputs, but committed
  evidence must be sanitized counts and artifact locations only.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
