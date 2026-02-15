---
id: task-21-structural-markdown-quality-gate-and-hard-case-normalization
title: Structural markdown quality gate and hard-case normalization
type: task
status: in_progress
priority: high
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-20-harden-markdown-normalization-for-math-artifacts-and-docling-export-escaping.md
labels:
  - markdown
  - quality
  - normalization
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Harden conversion output quality using structure-aware checks and normalization
against real difficult markdown artifacts from production CLI runs, without
adding brittle ad hoc replacements.

## PR Scope

- Add structural quality scoring for Docling formula-enrichment candidate
  selection (primary/fallback).
- Prefer Docling native markdown export options when available (e.g.
  `compact_tables=True`) to reduce ultra-wide markdown table rows and improve
  downstream processing compatibility.
- Harden strict normalization for inline display-math marker lines and
  deterministic leakage cleanup for reserved parser/control tokens (e.g.
  `/negationslash`, `<formula>`, `<loc_...>`), excluding code-fence blocks.
- Add deterministic quality-contract checks (reserved-token count, malformed-tag
  count, extreme line-length count) surfaced as warnings in results metadata.
- Add regression tests using hard problematic markdown excerpts derived from
  actual service output.
- Validate end-to-end with canonical CLI against the three hard PDFs.

## Deliverables

- [ ] Structural markdown quality scoring in
  `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
- [ ] Marker-line sanitation in
  `scripts/sir_convert_a_lot/infrastructure/markdown_normalizer.py`
- [ ] Hard-case regression tests under `tests/sir_convert_a_lot/`
- [ ] Production-surface CLI evidence in `build/manual-validation-quality-control`

## Acceptance Criteria

- [ ] Candidate selection prefers structurally cleaner formula output when
  placeholders are tied.
- [ ] Inline display-math lines with pathological trailing slash padding are
  normalized deterministically.
- [ ] Reserved protocol/control tokens (e.g. `/negationslash`, `<formula>`,
  `</formula`, `<loc_...>`) are stripped deterministically in `strict` mode,
  regardless of math adjacency, while preserving code-fence blocks.
- [ ] Regression tests cover hard excerpts and pass.
- [ ] CLI run of hard corpus succeeds with reduced malformed output signatures.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
