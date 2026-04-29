---
id: epic-10-digiexam-to-exam-net-exam-migration-pipeline
title: DigiExam to Exam.net exam migration pipeline
type: epic
status: proposed
priority: high
created: '2026-04-24'
last_updated: '2026-04-26'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md
  - docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
labels:
  - epic
  - conversion-platform
  - exam-migration
  - pdf
  - parser
---

## Goal

Deliver a Sir Convert-a-Lot feature lane that migrates old exams exported from
DigiExam as jsPDF PDFs into Exam.net-compatible artifacts, preserving item
boundaries, item types, point values, and answer shapes with minimal manual
re-authoring per exam.

## In Scope

- Characterize DigiExam jsPDF export shape and maintain the research baseline in
  `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`.
- Research Exam.net ingestion behavior and any native import formats before
  locking the renderer target.
- Build a Sir Convert parser stage for DigiExam PDF exports that emits a stable
  structured item stream with explicit parse-confidence and unknown-shape
  reporting.
- Define an intermediate exam representation owned by Sir Convert, with fields
  for item type, prompt body, options/matching pairs, point values, source
  spans, and answer-key provenance when available.
- Render Exam.net-targeted artifacts from that representation, choosing PDF or a
  native import format based on ingestion research.
- Provide a directory-level bulk CLI/API workflow that emits artifacts and a
  parity report under the normal Sir Convert artifact/manifest conventions.

## Out of Scope

- Re-authoring exam content or adapting items to new curricula.
- Building a browser UI integration with Exam.net beyond supported file import.
- Treating HuleEduOS written-exam Markdown tags as the canonical internal
  representation. HuleEduOS can remain a downstream/source-material consumer,
  but this feature owns its conversion contract in Sir Convert.
- Reconstructing answer keys when they are absent from all available DigiExam
  exports. Those cases remain manual Exam.net marking steps unless a teacher
  answer-key export is supplied.

## Stories

The initial research baseline has been reviewed for the parser lane. Planned
lanes, in dependency order:

1. Exam.net ingestion research and target-format decision.
1. `docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md`
   for DigiExam PDF parser v1 with regression fixtures and confidence
   reporting.
1. Sir Convert intermediate exam representation and manifest schema.
1. Exam.net-targeted renderer.
1. Bulk migration CLI/API workflow and parity report.

## Acceptance Criteria

- [ ] The Exam.net target behavior is researched against official/current
  guidance and empirical trial uploads before implementation stories choose
  a renderer target.
- [ ] Parser v1 has regression coverage for the observed DigiExam jsPDF samples
  and fails closed on unknown item shapes.
- [ ] Intermediate representation stores item type, points, prompts,
  source-location evidence, and answer-key provenance separately from any
  rendered Exam.net artifact.
- [ ] Bulk conversion emits a deterministic artifact set plus a human-readable
  parity report for teacher review before upload.
- [ ] HuleEduOS sample/source paths are treated as fixtures or source inputs,
  not as the owning runtime for this feature.

## Risks

- Sample size is two PDFs; true/false, ordering, gap-fill, images, math, tables,
  and other DigiExam item shapes are not yet represented.
- Student-view DigiExam exports do not appear to include answer-key metadata for
  multiple-choice or matching items.
- Exam.net PDF-converter target behavior is documented in the linked reference
  from public research and empirical v2 student/key printout experiments. The
  renderer target must avoid source-side multiple-choice labels because
  Exam.net owns option labels and reshuffles alternatives by default.
- DigiExam's embedded `Identity-H` font can degrade text extraction on future
  exports; parser v1 must detect character loss and use OCR fallback policy
  when needed.

## Notes

- Original planning docs were moved from the HuleEduOS classroom-material repo
  on 2026-04-24 because this belongs to Sir Convert-a-Lot's conversion platform
  backlog.
- Story 38 and Task 267 were scaffolded on 2026-04-25 after reviewing the
  research baseline. They are the first parser implementation authority and do
  not approve renderer or bulk workflow changes.
- Task 267 completed on 2026-04-26 with a typed parser result contract, PyMuPDF
  text-line adapter, deterministic fixture tests for both tracked PDFs, and
  fail-closed synthetic coverage for lossy extraction, missing anchors, unknown
  shapes, and incomplete matching structures.
- Current sample files have been copied into the repo under
  `inputs/examples/digiexam-exports/` with a manifest README.
- The promoted Exam.net PDF-converter schemas are recorded in
  `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`.
  Production renderer work must use no-label indented multiple-choice
  alternatives with exact-text answer keys, not labelled fallback layouts.

## Checklist

- [x] Story lane scaffolded after research review.
- [ ] Exam.net ingestion target selected.
- [x] Parser fixtures and confidence gate defined.
- [ ] Renderer target and parity-report gate defined.
