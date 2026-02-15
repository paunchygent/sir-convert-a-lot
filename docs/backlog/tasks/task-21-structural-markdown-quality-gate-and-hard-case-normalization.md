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
- Harden strict normalization for inline display-math marker lines and
  deterministic leakage cleanup for known parser control-sentinel lines near
  math contexts.
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
- [ ] Standalone parser-control leakage lines (e.g. `/negationslash`) are
  removed only under math-adjacent structural conditions.
- [ ] Regression tests cover hard excerpts and pass.
- [ ] CLI run of hard corpus succeeds with reduced malformed output signatures.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
