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

## Markdown Lint Normalization (Addendum 2026-02-15)

### Problem Statement

Converted markdown output triggers common linter complaints that reduce output
quality and downstream tooling compatibility. These are deterministic issues that
should be addressed in the `strict` normalization mode.

### Research: Markdownlint Rules

Reference: [davidanson/markdownlint](https://github.com/davidanson/markdownlint)

| Rule | Name | Issue | Fix Strategy |
| ---- | ---- | ----- | ------------ |
| MD034 | no-bare-urls | Bare URLs not converted to links by some parsers | Wrap URLs in angle brackets `<https://...>` |
| MD040 | fenced-code-language | Fenced code blocks without language specifier | Add default language identifier (e.g. `text`) |
| MD004 | ul-style | Inconsistent unordered list markers (`*`, `+`, `-`) | Normalize to single marker (prefer `-`) |
| MD041 | first-line-heading | First line should be top-level heading | Document-level concern, not line normalization |
| MD060 | table-column-style | Inconsistent table pipe spacing | Normalize to compact style |

### Research: Python Formatting Libraries

**mdformat** (<https://github.com/hukkin/mdformat>):

- CommonMark compliant markdown formatter with Python API
- Plugin architecture: `mdformat-gfm` for GFM tables/autolinks
- `mdformat.text(content, options={...}, extensions={...})` API
- Handles: word wrap, list numbering, consistent formatting
- Does NOT handle: MD034 bare URL wrapping, MD040 fence language defaults

**Conclusion**: mdformat is already a project dependency but doesn't cover all lint
rules. Empirical testing (2026-02-15) shows:

- MD034 (bare URLs): NOT handled by mdformat
- MD040 (fence language): NOT handled by mdformat
- MD004 (list markers): Partially handled but inconsistent
- MD060 (tables): NOT handled without `mdformat-gfm` extension

### Implementation Decision

1. **Add `mdformat-gfm` dependency** for GFM table formatting
1. **Custom lint normalization module** for rules mdformat doesn't cover:
   - `markdown_lint_normalizer.py` in `infrastructure/`
   - State-machine approach respecting code fences and math blocks
   - Each rule implemented as a discrete, testable function

### Implementation Strategy

1. **Dependency addition**:

   - Add `mdformat-gfm>=0.4.1` to `pyproject.toml`
   - Verify compatibility with existing `mdformat>=1.0.0`

1. **Custom lint rule handlers**:

   - MD034: Regex-based URL detection with state tracking to exclude:
     - Code fences (track fence open/close state)
     - Inline code spans (`` `...` ``)
     - Existing markdown links (`[text](url)`)
     - Already-wrapped URLs (`<url>`)
   - MD040: Match bare fence openings (```` ^(\s*)(```|~~~)\s*$ ````) and append `text`
   - MD004: Normalize `*`/`+` list markers to `-` (line-start only)
   - MD060: Delegate to mdformat with GFM extension for table normalization

1. **Testing requirements**:

   - Unit tests for each lint rule with edge cases
   - Integration tests with real converter output
   - Regression tests for false-positive prevention (code blocks, links, etc.)

### Risks and Mitigations

- **False positives in code blocks**: Must exclude fenced code block content
  from URL/list marker normalization
- **Math content interference**: Must preserve math delimiters and content
- **Performance**: mdformat parsing overhead; benchmark before adoption
- **Link syntax preservation**: Must not double-wrap already-formatted links

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
