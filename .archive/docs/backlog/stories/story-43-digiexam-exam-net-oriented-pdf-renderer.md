---
id: story-43-digiexam-exam-net-oriented-pdf-renderer
title: DigiExam Exam.net-oriented PDF renderer
type: story
status: completed
priority: high
created: '2026-05-11'
last_updated: '2026-05-11'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/tasks/task-277-implement-digiexam-exam-net-oriented-pdf-renderer-and-live-validation.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
labels:
  - exam-migration
  - digiexam
  - examnet
  - pdf-renderer
  - weasyprint
---

Implementation slice with acceptance-driven scope.

## Objective

Implement the first target-specific renderer in EPIC-10: a local
Exam.net-oriented PDF artifact generated from the completed DigiExam IR. The
renderer must use the promoted Exam.net PDF-converter shape from the research
reference, carry embedded image assets into the rendered PDF, and fail closed
when source evidence cannot produce a safe target artifact.

## Scope

- Consume `digiexam_intermediate_exam_v2` IR, including item structure,
  source-proven answer keys, manual follow-up state, and embedded asset records.
- Correct the v2 asset record shape additively so renderers have a canonical
  base64 payload to materialize, while keeping manifest summaries metadata-only.
- Render supported item types into the promoted Exam.net PDF-converter syntax:
  free text, single-answer multiple choice, multiple response, and one-gap
  short answer.
- Preserve the no-label multiple-choice invariant: options are indented text,
  never source-side `A.`, `B.`, `a)`, `1.`, bullets, or list items.
- Use Swedish-first framing where the import boundary is proven:
  `Poängvärde: N` for point values and `Typ: Fritext` with Swedish writing
  instructions for free-text items.
- Keep machine-marked item type and answer-key control lines in the promoted
  English wording until a later import proof promotes Swedish equivalents.
- Materialize embedded assets as local files under a renderer work directory
  and generate a real PDF through the existing WeasyPrint infrastructure.
- Decompose renderer logic into small SRP modules for contracts, asset
  preparation, prompt HTML sanitation, item rendering, final HTML assembly, and
  infrastructure materialization.
- Keep QTI/native import, service/API routes, bulk workflow orchestration,
  browser automation into Exam.net, and answer-key synthesis out of this story.

## Acceptance Criteria

- [x] Renderer code is modular, reusable, and testable, with every new or
  materially changed Python module carrying a Google-style domain-purpose
  module docstring and staying under the repo LoC boundary.
- [x] The renderer consumes the completed IR rather than reparsing `.dxe`
  structure inside the PDF target.
- [x] Asset-bearing IR items can render to a PDF with the referenced image
  embedded, and asset payloads fail closed when missing, malformed, or
  inconsistent with hash/length metadata.
- [x] Machine-marked items without source-proven answer keys fail closed with
  typed target warnings rather than rendering as weaker manual items.
- [x] Multiple-choice and multiple-response output uses no source-side option
  labels and uses exact source option text for `Correct answer(s)`.
- [x] Item shapes without a governed Exam.net PDF-converter target, including
  multi-gap short answer and matching, fail closed at this renderer with typed
  warnings while remaining representable in parser/IR contracts where source
  evidence exists.
- [x] Live validation generates a real PDF artifact and inspects it with a PDF
  reader to confirm Swedish point/free-text markers, target-safe machine-marked
  type markers, and embedded image presence.

## Test Requirements

- [x] Unit tests cover promoted Exam.net PDF syntax for free text,
  single-answer multiple choice, multiple response, and one-gap short answer.
- [x] Unit tests cover fail-closed target warnings for missing answer keys,
  source-labelled options, missing asset payloads, and parser-blocked IR.
- [x] Live test renders a real PDF through WeasyPrint and validates the
  generated artifact with PyMuPDF text/image inspection.
- [x] Existing embedded-asset parser and IR tests prove asset payloads remain
  hash-verifiable and manifest summaries remain deterministic metadata.
- [x] Existing WeasyPrint resource-boundary tests remain green.

## Done Definition

Story 43 is done when Task 277 lands the modular Exam.net-oriented PDF
renderer, the live PDF proof passes locally, generated docs are synchronized,
and EPIC-10 still reserves QTI/native import and bulk migration for separate
governed lanes.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
