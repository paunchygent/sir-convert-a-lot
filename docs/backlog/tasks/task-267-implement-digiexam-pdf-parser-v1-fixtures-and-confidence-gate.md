---
id: task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate
title: Implement DigiExam PDF parser v1 fixtures and confidence gate
type: task
status: completed
priority: high
created: '2026-04-25'
last_updated: '2026-05-07'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
  - inputs/examples/digiexam-exports/README.md
labels:
  - exam-migration
  - digiexam
  - pdf
  - parser
  - tests
  - confidence
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first production-bound DigiExam parser slice: fixture-backed PDF
extraction for the two tracked jsPDF samples and a confidence gate that prevents
unknown or degraded item shapes from being treated as renderer-ready.

## PR Scope

- Add a small SRP-focused parser module under the Sir Convert code surface for
  DigiExam jsPDF exports. Keep module files below the repo size limit and add
  Google-style module docstrings.
- Own the parser contract in domain code under
  `scripts/sir_convert_a_lot/domain/`; add a narrow infrastructure extraction
  adapter under `scripts/sir_convert_a_lot/infrastructure/` only when the
  existing PDF extraction stack cannot be consumed directly from tests or
  application code.
- Use the existing PDF extraction stack where available; do not introduce an ad
  hoc converter script or a renderer-specific shortcut.
- Define typed parser result objects for:
  - source document metadata;
  - item blocks;
  - item type classification;
  - point marker evidence;
  - source spans or page/line evidence;
  - parse status, renderer readiness, confidence, and warning details;
  - answer-key provenance state.
- Keep HTTP/API routes, service integration, CLI bulk workflow, Exam.net
  rendering, QTI/native import, and answer-key reconstruction outside Task 267.
- Add regression fixtures/tests for:
  - `inputs/examples/digiexam-exports/_-25cEkologiprov51-55.pdf`;
  - `inputs/examples/digiexam-exports/_-Kemikapitel2ht2525dECA.pdf`.
- Assert the legacy PDF regression fixture expectations:
  - ecology sample has 15 open-ended items;
  - chemistry sample has 12 items in the exact order recorded by the artifact
    evidence reference;
  - chemistry item-type breakdown is 3 multiple-choice, 1 matching, and 8
    open-ended items;
  - `Max poäng : N` markers are captured where present;
  - multiple-choice and matching answer keys are reported as absent when the PDF
    does not contain them.
- Add a fail-closed confidence gate for unknown shapes, lossy Swedish text
  extraction, missing required anchors, or unsupported item structures.
- Update EPIC-10, Story 38, the research reference only if implementation
  changes the documented parser contract.

## Deliverables

- [x] DigiExam parser v1 module and typed result contract.
- [x] Fixture-backed parser tests for both tracked sample PDFs under
  `tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py`.
- [x] Confidence/warning model with typed parse status, renderer readiness,
  high-confidence parses, degraded extraction, unknown shapes, unsupported
  structures, missing anchors, and missing answer-key provenance.
- [x] Documentation closeout in the governing backlog/reference docs if the
  implementation changes accepted parser semantics.

## Acceptance Criteria

- [x] Parser output is deterministic for both tracked PDFs.
- [x] Ecology output contains exactly 15 open-ended items.
- [x] Chemistry output contains exactly 12 ordered items with headers/titles,
  type breakdown, and point-marker evidence matching the legacy PDF regression
  fixture expectations.
- [x] Parsed item results carry traceable source evidence.
- [x] Missing answer keys are represented as provenance state, not reconstructed
  from prompts or options.
- [x] Matching items preserve numbered left prompts, lettered right options, and
  blank-row evidence; DigiExam source PDFs without answer keys do not synthesize
  `Correct matches`.
- [x] Swedish diacritics are checked; degraded extraction produces a blocked
  parse status or `renderer_ready == false`.
- [x] Unknown item shapes do not proceed as renderer-ready output.
- [x] New code avoids `Any`, casts, `type: ignore`, lint ignores, and large
  god modules.
- [x] High-confidence, degraded extraction, missing-anchor, unknown-shape, and
  unsupported-structure cases are distinguishable by typed warning/status
  values.

## Parser Confidence Contract

Task 267 must define a machine-checkable parser result boundary before any
renderer consumes parser output:

- Successful parses expose `renderer_ready == true` or an equivalent typed
  success state.
- Degraded and blocked parses expose `renderer_ready == false` or make
  renderer-ready item access unavailable.
- Warning/status classes distinguish unknown source shape, lossy Swedish text
  extraction, missing required anchors, unsupported structures, and missing
  answer-key provenance.
- Missing answer-key provenance is allowed for observed DigiExam student-view
  multiple-choice and matching items, but it must remain explicit provenance and
  must not become reconstructed answer data.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
- [x] `pdm run coverage-gate`, or recorded rationale if the slice is not
  conversion-core-applicable.
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

Validation evidence after Review 07 follow-up on 2026-04-27:

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all` (`Success: no issues found in 571 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
  (`10 passed`)
- `pdm run coverage-gate` (`1061 passed, 5 skipped`, total coverage `95.55%`)
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
