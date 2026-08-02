---
id: story-40-digiexam-dxe-source-parser-and-answer-key-provenance
title: DigiExam .dxe source parser and answer-key provenance
type: story
status: completed
priority: high
created: '2026-05-07'
last_updated: '2026-05-08'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/tasks/task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/README.md
labels:
  - exam-migration
  - digiexam
  - dxe
  - parser
  - answer-key-provenance
---

Implementation slice with acceptance-driven scope.

## Objective

Deliver the first `.dxe`-first DigiExam parser lane for EPIC-10. The story
establishes `.dxe` as the canonical source for exam structure and defines how a
sanitized graded student-result PDF may optionally enrich only correct
machine-marked answers.

## Scope

- Parse observed DigiExam `.dxe` JSON exports into a stable typed item stream
  with source evidence and explicit parser status.
- Cover the 2026-05-07 mixed-question fixture under
  `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/`.
- Preserve question order, titles, prompt HTML/body, question type codes,
  maximum scores, alternatives, gap identifiers, and observed grading-policy
  fields.
- Support the observed `.dxe` item types:
  - free text / open-ended (`type 0`);
  - single-choice multiple choice (`type 1`);
  - multiple-response multiple choice (`type 2`);
  - gap-fill / lucktext (`type 3`).
- Represent missing answer keys and missing rubrics as provenance states rather
  than synthesized content.
- Optionally enrich correct machine-marked answer data from the sanitized
  graded-result PDF when labels prove correct alternatives or gap values.
- Explicitly discard wrong student selections, student free-text answers,
  per-student scores, student identity, and student-performance history.
- Keep blank/student-view PDFs as visual parity and legacy fallback evidence
  only.
- Keep Exam.net rendering, QTI/native import, service/API routes, and bulk
  migration orchestration outside this story.

## Acceptance Criteria

- [x] `.dxe` fixture parsing produces exactly 7 ordered items with observed type
  sequence `0, 1, 1, 2, 2, 2, 3`.
- [x] The parser preserves item title, prompt/body HTML or text, maximum score,
  and source evidence for every observed item.
- [x] Single-choice and multiple-response items preserve ordered alternatives
  while treating the observed all-`right:false` `.dxe` values as absent
  answer-key provenance, not as a negative answer key.
- [x] Gap-fill parsing preserves `dxWordGap` spans, gap identifiers, and empty
  `validations` arrays as missing accepted-answer provenance.
- [x] Optional result-PDF enrichment extracts only correct machine-marked answer
  data proven by labels such as `(Korrekt svar)` or `(Korrekt alternativ)` and
  any proven correct gap values.
- [x] Result-PDF MCQ enrichment fails closed when a correct label cannot bind to
  exactly one observed `.dxe` alternative.
- [x] Result-PDF gap enrichment binds accepted values to observed `.dxe` gap
  identifiers and fails closed on count/order mismatch.
- [x] Result-PDF enrichment discards `(Fel svar)`, student free-text responses,
  scores, student identity, and student-performance history.
- [x] Unsupported or unobserved `.dxe` item types fail closed with typed
  warnings and do not become renderer-ready output.
- [x] Parser output remains renderer-neutral and does not encode Exam.net
  import syntax.

## Test Requirements

- [x] Fixture-backed tests cover
  `DXE-2026-05-07-structure` and the duplicate `.dxe` schema/content fixture
  recorded in the evidence reference.
- [x] Tests assert the exact 7-item order, observed type sequence, max scores,
  MCQ alternative order, and gap identifier structure.
- [x] Tests assert answer-key provenance states for absent `.dxe` keys,
  result-PDF correct-answer enrichment, and discarded wrong student answers.
- [x] Tests cover duplicate/unmatched result-PDF MCQ labels and gap-answer count
  mismatch as blocking fail-closed enrichment cases.
- [x] Tests cover one unknown or unsupported `.dxe` shape that must fail closed.
- [x] Tests cover malformed or missing required `.dxe` JSON sections without
  raising untyped exceptions.

## Done Definition

Story 40 is done when Task 274 lands a `.dxe` parser and optional
graded-result enrichment gate under the Sir Convert code/test surfaces, the
parser output is safe for the later renderer-neutral intermediate exam
representation, EPIC-10 docs record that `.dxe` structure precedes Exam.net
renderer/import decisions, and Task 274 either passes the required backend
`coverage-gate` or records an explicit governed waiver for the unrelated suite
failures. Task 274 passed `coverage-gate` on 2026-05-08.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
