---
id: task-238-repair-exam-net-docx-paragraph-fidelity-in-docx-to-markdown-v2-route
title: Repair Exam.net DOCX paragraph fidelity in docx-to-markdown v2 route
type: task
status: proposed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - scripts/sir_convert_a_lot/infrastructure/pandoc_docx_to_markdown.py
  - tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py
labels:
  - docx
  - markdown
  - exam-net
  - conversion-quality
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Repair a real `docx -> md` quality gap for Exam.net-exported writing submissions where multiple
visible paragraphs are serialized into one DOCX paragraph with repeated hard breaks, causing the v2
service to emit collapsed Markdown with literal `\ \` artifacts after strict normalization.

## PR Scope

- Inspect the canonical v2 `docx -> md` path and confirm whether the defect is present in the
  service, not just in downstream local tooling.
- Patch the converter so the repair is narrow and signature-based rather than a blanket
  all-DOCX behavior change.
- Keep the route inside canonical Sir Convert-a-Lot surfaces; no downstream ad hoc converters.
- Add focused unit coverage for both the raw repair and the post-normalization service output.

## Deliverables

- [ ] `pandoc_docx_to_markdown.py` updated for better paragraph fidelity on Exam.net-style DOCX
  exports.
- [ ] Focused tests covering the repaired block structure and v2 strict-normalization survival.
- [ ] Task note updated with the implementation/validation outcome.

## Acceptance Criteria

- [ ] The v2 `docx -> md` path no longer collapses Exam.net-style paragraph blocks into single
  paragraphs with literal `\ \` artifacts.
- [ ] Ordinary DOCX conversions are not broadly reinterpreted; the repair is guarded by a strong
  content signature.
- [ ] Focused tests pass for the converter wrapper and repaired output path.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
