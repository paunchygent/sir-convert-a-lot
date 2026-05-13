---
id: task-277-implement-digiexam-exam-net-oriented-pdf-renderer-and-live-validation
title: Implement DigiExam Exam.net-oriented PDF renderer and live validation
type: task
status: completed
priority: high
created: '2026-05-11'
last_updated: '2026-05-11'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/tasks/task-276-implement-digiexam-dxe-embedded-asset-ir-support.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
labels:
  - exam-migration
  - digiexam
  - examnet
  - pdf-renderer
  - live-validation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement a modular Exam.net-oriented PDF renderer that consumes DigiExam IR v2,
materializes embedded assets, generates a real PDF through WeasyPrint, and
validates the output with live PDF inspection.

## PR Scope

- Add a thin domain coordinator for the Exam.net PDF target.
- Split renderer responsibilities into small SRP modules:
  - renderer contracts and typed warnings;
  - embedded asset payload validation and local asset-file planning;
  - prompt HTML sanitation and image-reference rewriting;
  - supported item section rendering;
  - final HTML document assembly;
  - infrastructure materialization through WeasyPrint.
- Extend the v2 embedded asset value object with canonical `content_base64`
  payload so renderers can carry assets instead of only auditing metadata.
- Keep manifest asset summaries metadata-only; they must not serialize payloads.
- Use the promoted Exam.net PDF-converter schemas from the research reference:
  Swedish-first point/free-text framing (`Poängvärde: N`, `Typ: Fritext`,
  Swedish free-text instruction), target-safe machine-marked type/key control
  lines, no-label indented options, and exact-text answer keys.
- Fail closed with typed target warnings for blocked IR, missing point values,
  empty prompts, missing machine answer keys, unsafe labelled options,
  item shapes without a governed Exam.net PDF-converter target, and missing or
  invalid embedded asset payloads.
- Update docs and validation evidence.

## Out Of Scope

- QTI/native import package generation.
- Exam.net browser automation or upload actions.
- Service/API routes and bulk migration workflow.
- Answer-key reconstruction when source evidence is absent.
- OCR or semantic analysis of embedded images.
- Rendering multi-gap items as weaker short-answer PDFs before a governed
  target decision approves the shape.

## Deliverables

- [x] `scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf*.py` modular
  renderer domain components under the repo LoC boundary.
- [x] `scripts/sir_convert_a_lot/infrastructure/digiexam_examnet_pdf_renderer.py`
  materializer that writes HTML/assets and calls the existing WeasyPrint
  wrapper.
- [x] Additive v2 IR asset payload field and tests proving payload hash/length
  identity.
- [x] Unit tests for promoted Exam.net PDF syntax and fail-closed target
  warnings.
- [x] Live WeasyPrint/PyMuPDF PDF generation test proving text markers and an
  embedded image are present.
- [x] Docs updates for Story 43, Task 277, EPIC-10, the IR converter contract,
  and the Exam.net PDF research reference.

## Acceptance Criteria

- [x] New and materially changed modules carry domain-purpose Google-style
  module docstrings and stay below the strict repo module-size boundary.
- [x] The domain renderer is pure and filesystem-free; only the infrastructure
  materializer writes HTML, asset files, and PDFs.
- [x] The renderer never reparses `.dxe` JSON. Tests build IR from the parser
  and pass that IR into the renderer.
- [x] Asset payload rendering is hash-verified against IR metadata before
  writing local files.
- [x] The live PDF test validates generated PDF text for `Fråga N`,
  `Poängvärde: N`, free-text `Typ: Fritext`, machine-marked type markers, and
  source prompt text, plus image presence through PyMuPDF.
- [x] Missing answer-key evidence and item shapes without a governed
  Exam.net PDF-converter target block rendering with exact typed warning codes.
- [x] The implementation does not add QTI/native import, service/API route, or
  bulk workflow behavior.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_examnet_pdf_renderer.py tests/sir_convert_a_lot/test_weasyprint_html_to_pdf.py tests/sir_convert_a_lot/test_digiexam_dxe_parser.py tests/sir_convert_a_lot/test_digiexam_intermediate_exam_ir.py -q`
- [x] `pdm run coverage-gate`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Stop Conditions

- Stop before automating an Exam.net upload or browser interaction.
- Stop before rendering multi-gap or matching items through a weaker PDF shape;
  this is a renderer target-proof boundary, not a parser/IR representation
  limit.
- Stop before removing asset payloads from IR without a replacement asset-store
  contract that renderers can consume.
- Stop before adding a new third-party PDF/image dependency; use the existing
  WeasyPrint/PyMuPDF stack for this task.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
