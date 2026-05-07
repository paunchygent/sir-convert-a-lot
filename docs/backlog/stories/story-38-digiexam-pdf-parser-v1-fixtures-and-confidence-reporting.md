---
id: story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting
title: DigiExam PDF parser v1 fixtures and confidence reporting
type: story
status: completed
priority: high
created: '2026-04-25'
last_updated: '2026-05-07'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
labels:
  - exam-migration
  - digiexam
  - pdf
  - parser
  - fixtures
  - confidence
---

Implementation slice with acceptance-driven scope.

## Objective

Deliver the first Sir Convert-owned DigiExam parser lane: deterministic
fixtures for the observed jsPDF exports, a parser v1 contract that emits a
structured item stream, and explicit confidence/warning evidence before any
Exam.net renderer or bulk workflow depends on the parser output.

## Scope

- Use the tracked sample corpus under `inputs/examples/digiexam-exports/` as
  the first regression fixture set.
- Parse DigiExam PDF exports into item blocks with stable source evidence:
  header, item number or title, item type, prompt text, optional point marker,
  options or matching structures when present, and extraction warnings.
- Preserve the two observed PDFs as legacy PDF regression fixtures:
  - ecology sample: 15 open-ended items with subpart handling;
  - chemistry sample: 12 ordered items with 3 multiple-choice, 1 matching, and
    8 open-ended items.
- Add confidence reporting that distinguishes high-confidence parsed fields,
  degraded extraction, unknown item shapes, and missing answer-key provenance.
- Keep answer-key reconstruction, Exam.net rendering, QTI/native import
  decisions, service API integration, and bulk migration orchestration outside
  this story.

## Acceptance Criteria

- [x] Parser v1 produces deterministic item counts and item-type breakdowns for
  both tracked DigiExam sample PDFs.
- [x] Every parsed item includes source-location evidence sufficient for a
  teacher or developer to trace the output back to the source PDF.
- [x] `Max poäng : N` markers are captured when present and absence is reported
  explicitly rather than inferred.
- [x] Multiple-choice and matching items report missing answer-key provenance
  instead of guessing correct answers.
- [x] Swedish diacritic extraction is checked and lossy extraction produces a
  warning or fail-closed confidence result.
- [x] Unknown item shapes fail closed with actionable warnings and do not
  silently enter a renderer-ready stream.

## Test Requirements

- [x] Regression tests cover the ecology and chemistry sample PDFs in
  `inputs/examples/digiexam-exports/`.
- [x] Tests assert item counts, item types, point marker extraction, and warning
  classes from the parser report.
- [x] Tests cover Swedish characters and the `Identity-H`/fallback-font risk
  called out in the reference docs.
- [x] Tests cover at least one synthetic or fixture-level unknown-shape case
  that must fail closed.

## Done Definition

Story 38 is done when Task 267 lands parser v1 fixtures and confidence
reporting under the Sir Convert code/test surfaces, EPIC-10 has a reviewed
parser contract for downstream representation work, and docs/validation evidence
is recorded without starting renderer or bulk workflow implementation.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
