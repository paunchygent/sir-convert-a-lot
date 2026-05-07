---
id: epic-10-digiexam-to-exam-net-exam-migration-pipeline
title: DigiExam to Exam.net exam migration pipeline
type: epic
status: proposed
priority: high
created: '2026-04-24'
last_updated: '2026-05-08'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md
  - docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md
  - docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md
  - docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md
  - docs/backlog/tasks/task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate.md
  - docs/backlog/tasks/task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
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
DigiExam as `.dxe` files, with optional PDF evidence, into
Exam.net-compatible artifacts, preserving item boundaries, item types, point
values, and answer shapes with minimal manual re-authoring per exam.

## In Scope

- Characterize DigiExam artifact and item-type evidence in
  `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`, with
  renderer/import research kept in
  `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`.
- Research Exam.net ingestion behavior and any native import formats before
  locking the renderer target.
- Build a Sir Convert parser stage for DigiExam `.dxe` exports that emits a
  stable structured item stream with explicit parse-confidence and
  unknown-shape reporting.
- Accept graded DigiExam student-result PDFs as optional companion evidence for
  correct machine-marked answers only.
- Use blank/student-view DigiExam PDFs as optional visual parity evidence, not
  as the preferred structure source when `.dxe` is available.
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
  exports. Free-text answers, rubrics, marking matrices, and assessment guides
  remain manual Exam.net marking steps unless a teacher-provided source supplies
  them.
- Preserving incorrect student answers from graded result PDFs. Result PDFs may
  enrich correct-answer data only.

## Stories

The initial PDF research evidence has been reviewed for the completed PDF
fallback parser lane. Planned lanes, in dependency order:

1. `docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md`
   for DigiExam PDF parser v1 with regression fixtures and confidence
   reporting.
1. `docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md`
   for `.dxe` source parsing and optional graded-result PDF answer-key
   enrichment.
1. `docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md`
   for the Sir Convert intermediate exam representation and manifest schema.
1. Exam.net ingestion research and target-format decision before renderer
   implementation.
1. Exam.net-targeted renderer.
1. Bulk migration CLI/API workflow and parity report.

## Acceptance Criteria

- [ ] The Exam.net target behavior is researched against official/current
  guidance and empirical trial uploads before implementation stories choose
  a renderer target.
- [ ] Parser v1 has regression coverage for the observed DigiExam jsPDF samples
  and fails closed on unknown item shapes.
- [x] Intermediate representation stores item type, points, prompts,
  source-location evidence, and answer-key provenance separately from any
  rendered Exam.net artifact.
- [ ] `.dxe` is treated as the required structure source, while graded
  student-result PDFs can only enrich correct machine-marked answers.
- [ ] Incorrect student answers are discarded from the migration model.
- [x] Story 40 / Task 274 parse the observed `.dxe` fixtures into a
  renderer-neutral item stream before the intermediate representation or
  Exam.net renderer work starts. Story 40 and Task 274 closed on 2026-05-08
  after the required backend coverage gate passed.
- [ ] Bulk conversion emits a deterministic artifact set plus a human-readable
  parity report for teacher review before upload.
- [ ] HuleEduOS sample/source paths are treated as fixtures or source inputs,
  not as the owning runtime for this feature.

## Risks

- Fixture coverage remains narrow: the `.dxe` evidence currently covers one
  7-question mixed exam plus a duplicate export, and legacy PDF evidence covers
  two student-view PDFs. True/false, ordering, image-based, table-based,
  math-heavy, attachment, and additional DigiExam item shapes are not yet
  represented.
- DigiExam artifact containment and absence claims must stay linked to the
  evidence files in
  `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`; do not
  generalize from one export shape without adding a fixture-backed evidence row.
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
  initial PDF research evidence. They are legacy PDF fallback parser authority
  and do not approve renderer, `.dxe`, or bulk workflow changes.
- Task 267 completed on 2026-04-26 with a typed parser result contract, PyMuPDF
  text-line adapter, deterministic fixture tests for both tracked PDFs, and
  fail-closed synthetic coverage for lossy extraction, missing anchors, unknown
  shapes, and incomplete matching structures.
- Story 40 and Task 274 were scaffolded on 2026-05-07 after the `.dxe` source
  policy decision. They are the implementation authority for parsing `.dxe`
  structure and optional correct-answer enrichment from sanitized graded-result
  PDFs; they do not approve Exam.net rendering, generic IR, service routes, or
  bulk workflow changes.
- Task 274 completed on 2026-05-08 with a typed `.dxe`
  parser, result-PDF correct-answer enrichment extractor, exact fixture tests
  for both `.dxe` files, fail-closed malformed/unsupported `.dxe` coverage,
  duplicate/unmatched MCQ label rejection, and gap-answer count/order binding.
  The closeout passed `coverage-gate` after stale generated docs indexes were
  regenerated and revalidated.
- Story 41 and Task 275 completed on 2026-05-08 with
  `digiexam_intermediate_exam_v1`, `digiexam_ir_manifest_v1`, fixture-backed
  mappings from the completed `.dxe` and PDF parser lanes, explicit manual
  follow-up records, and no Exam.net renderer/import syntax.
- Legacy PDF sample files live under `inputs/examples/digiexam-exports/`.
  The current `.dxe`, blank-PDF, and sanitized result-PDF evidence lives under
  `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/`.
- The promoted Exam.net PDF-converter schemas are recorded in
  `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`.
  Production renderer work must use no-label indented multiple-choice
  alternatives with exact-text answer keys, not labelled fallback layouts.

## Checklist

- [x] Story lane scaffolded after research review.
- [ ] Exam.net ingestion target selected.
- [x] Parser fixtures and confidence gate defined.
- [x] `.dxe` parser and answer-key provenance lane defined.
- [x] Renderer-neutral IR and manifest schema defined.
- [ ] Renderer target and parity-report gate defined.
