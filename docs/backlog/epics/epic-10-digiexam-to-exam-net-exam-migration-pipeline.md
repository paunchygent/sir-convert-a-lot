---
id: epic-10-digiexam-to-exam-net-exam-migration-pipeline
title: DigiExam to Exam.net exam migration pipeline
type: epic
status: proposed
priority: high
created: '2026-04-24'
last_updated: '2026-05-13'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md
  - docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md
  - docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md
  - docs/backlog/tasks/task-274-implement-digiexam-dxe-parser-fixtures-and-result-pdf-answer-enrichment-gate.md
  - docs/backlog/tasks/task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract.md
  - docs/backlog/tasks/task-276-implement-digiexam-dxe-embedded-asset-ir-support.md
  - docs/backlog/tasks/task-277-implement-digiexam-exam-net-oriented-pdf-renderer-and-live-validation.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/backlog/tasks/task-281-classify-digiexam-dxe-validation-corpus-and-add-parser-regression-gate.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
labels:
  - epic
  - conversion-platform
  - exam-migration
  - pdf
  - parser
  - qti
  - docx
---

## Goal

Deliver Sir Convert-a-Lot exam migration and teacher-authoring lanes that
produce Exam.net-compatible artifacts. The first lane migrates old exams
exported from DigiExam as `.dxe` files, with optional PDF evidence. The second
lane handles normal teacher-owned Exam.net-compatible artifacts and produces
QTI packages, editable DOCX files, and Exam.net PDF-to-exam converter PDFs.

Both lanes preserve item boundaries, item types, point values, answer shapes,
and explicit manual follow-up so teachers can validate imported exams with
minimal re-authoring.

## In Scope

- Characterize DigiExam artifact and item-type evidence in
  `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`, with
  renderer/import research kept in
  `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`.
- Research Exam.net ingestion behavior and native import details before each
  renderer lane implements target-specific output.
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
- Preserve embedded `.dxe` question assets as renderer-neutral IR assets before
  any renderer decides how to place them in PDF, QTI, or Exam.net artifacts.
- Render Exam.net-targeted artifacts from that representation in separate
  target lanes: an Exam.net-oriented PDF lane and a QTI/native import lane.
- Maintain a shared Swedish Exam.net PDF-to-exam renderer profile for
  teacher-facing artifacts: `Fråga`, `Poängvärde`, `Typ`, `Svarsalternativ`,
  `Rätt svar`, `Rätta svar`, `Vänster sida`, `Höger sida`, and `Rätta par`.
- Define one shared service API v2 job lifecycle with separate route contracts:
  `digiexam_dxe -> examnet_migration_bundle` for legacy DigiExam migration and
  `examnet_artifact -> teacher_authoring_bundle` for teacher-owned Exam.net
  source PDFs or Word exports.
- Emit editable DOCX as a semantic authoring artifact from normalized exam IR,
  not as a generic visual PDF-to-DOCX conversion.
- Define QTI 2.1+ package generation and validation around Exam.net's
  vendor-reported import direction: at least multiple choice and free text,
  images where supported, and manual follow-up for unsupported audio, PDF, and
  tool resources.
- Provide a directory-level bulk CLI/API workflow that emits artifacts and a
  parity report under the normal Sir Convert artifact/manifest conventions.
- Expose the migration through Sir Convert service API v2 for authenticated
  Skriptoteket teacher workflows, with Skriptoteket owning UX and authenticated
  user-file persistence while Sir Convert owns conversion execution and
  artifact authorization.

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
- Treating Exam.net-origin teacher PDFs, Word exports, answer keys, or QTI
  packages as DigiExam `.dxe` migration inputs.
- Claiming production-ready QTI support for Exam.net item types that have not
  passed the governed validator ladder and Exam.net import proof.

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
1. `docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md`
   for `.dxe` embedded image extraction, asset binding, and manifest asset
   parity before renderer implementation.
1. Task 276 embedded asset support, completing IR v2 and manifest v2 before
   renderer implementation.
1. `docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md`
   for the Exam.net-oriented PDF renderer and live validation lane.
1. `docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md`
   for the completed authenticated API, artifact bundle, and Skriptoteket
   ownership contract gate.
1. `docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md`
   for Exam.net-origin teacher artifact authoring bundles, including QTI,
   editable DOCX, source-role classification, and the shared Swedish
   PDF-to-exam renderer profile.
1. Completed Task 280 for deterministic QTI sample packages and
   validation-report gate: MCQ, free text, image-bearing MCQ/free text,
   unsupported-resource omission, and proof-gated matching before any service
   runtime exposure.
1. `docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md`
   for the governed cleanup tranche that must precede more Exam.net runtime
   work: docs-state reconciliation, route-handler registry, runtime/CLI hotspot
   extraction, experiment-surface demotion, Task 200 scaffold closeout, and a
   validated onboarding map.
1. Full QTI/native import lane, implemented behind the accepted API/artifact
   contracts and Task 280 validation foundation.
1. Service API exposure and Skriptoteket adapter/UI workflow.
1. Bulk migration workflow and parity report.

## Acceptance Criteria

- [x] Renderer target lanes are selected as separate Exam.net-oriented PDF and
  QTI/native import workstreams.
- [ ] Each renderer target behavior is researched against official/current
  guidance and empirical trial uploads before implementation lands
  target-specific output.
- [ ] Parser v1 has regression coverage for the observed DigiExam jsPDF samples
  and fails closed on unknown item shapes.
- [x] Intermediate representation stores item type, points, prompts,
  source-location evidence, and answer-key provenance separately from any
  rendered Exam.net artifact.
- [x] Embedded `.dxe` question images are extracted as renderer-neutral assets,
  bound to `data-image-id` prompt references, and reported through ordered v2
  manifest asset summaries before any renderer consumes them.
- [ ] PDF and QTI/native import renderers consume the completed IR, including
  embedded assets, and either carry referenced assets correctly or fail closed
  with typed blocking warnings.
- [x] The Exam.net-oriented PDF renderer generates a live PDF proof from IR,
  carries embedded image assets, and blocks unsupported target shapes with typed
  warnings.
- [ ] Authenticated Skriptoteket teacher workflows submit DigiExam migration
  jobs through a governed Sir Convert API contract, then download or save named
  artifact bundle entries without duplicating conversion policy.
- [ ] Exam.net-origin teacher artifact workflows use a separate governed route
  contract from the DigiExam `.dxe` migration route, while sharing artifact
  bundle and validation semantics where compatible.
- [ ] QTI packages are generated only for the supported Exam.net target profile,
  include validation reports, and fail closed or emit manual follow-up for
  unsupported resource classes such as audio, PDF attachments, and tools.
- [x] Deterministic QTI sample packages exist for MCQ, free text,
  image-bearing MCQ/free text, and proof-gated matching before QTI is exposed
  as a service runtime target.
- [ ] More Exam.net service runtime work is gated behind Story 46's
  active-surface cleanup and route-handler registry, so `create_job` remains a
  generic lifecycle endpoint rather than a route-specific branch knot.
- [ ] Matching items are first-class in the IR and authoring route, but rendered
  with exact pairings only when source evidence provides the answer-key
  provenance.
- [ ] Editable DOCX output is generated from normalized exam authoring IR and
  preserves editable item structure, not just visual PDF layout.
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
  committed 7-question mixed exam plus a duplicate export, one local
  colleague-provided export with an embedded image, and legacy PDF evidence
  covers two student-view PDFs. True/false, ordering, table-based, math-heavy,
  attachment, and additional DigiExam item shapes are not yet represented.
- DigiExam artifact containment and absence claims must stay linked to the
  evidence files in
  `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`; do not
  generalize from one export shape without adding a fixture-backed evidence row.
- The 2026-05-12 OneDrive `.dxe` validation package is useful parser evidence
  but is not yet a tracked fixture authority. Treat it as local raw corpus until
  Task 281 produces metadata-only manifests and any required sanitized fixtures.
- Exam.net PDF-converter target behavior is documented in the linked reference
  from public research and empirical v2 student/key printout experiments. The
  renderer target must avoid source-side multiple-choice labels because
  Exam.net owns option labels and reshuffles alternatives by default.
- Exam.net QTI import is vendor-reported but still under development. The QTI
  lane must separate standards validation from Exam.net import proof and must
  not promote item types beyond the available evidence.
- The Exam.net artifact authoring route has a different source authority than
  DigiExam migration. Source-role classification must fail closed so a
  student-view PDF is not mistaken for an answer-key source.
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
- Story 42 and Task 276 completed on 2026-05-11 after a
  colleague-provided `.dxe` export showed `question.images[]` base64 image
  payloads bound from `bodyHTML` through `data-image-id`. The implementation
  adds renderer-neutral asset extraction, v2 IR/schema versioning, typed asset
  warnings, and ordered manifest asset summaries, not PDF/QTI/Exam.net
  rendering.
- On 2026-05-11, the target sequencing decision was accepted: complete Task 276
  first, then implement Exam.net-oriented PDF and QTI/native import as separate
  renderer lanes. Both renderer lanes must consume the completed IR including
  assets and must fail closed when referenced assets cannot be carried.
- Story 43 and Task 277 started on 2026-05-11 for the Exam.net-oriented PDF
  renderer. The renderer is target-specific but still consumes IR; it does not
  reopen `.dxe` parsing, implement QTI/native import, add service/API routes,
  or automate Exam.net upload.
- Story 44 and Task 278 were scaffolded on 2026-05-11 after the product access
  boundary was clarified: teachers interact through a public authenticated
  Skriptoteket app, while Sir Convert owns authenticated service API execution
  and artifact bundles. QTI/native rendering and service exposure must land
  behind the accepted Task 278 API/artifact contract.
- Task 278 completed on 2026-05-11 with
  `docs/converters/digiexam-migration-service-api-artifact-contract.md` as the
  active contract for `.dxe`-required requests, sanitized result-PDF companion
  rules, named artifact bundles, owner-scoped job/artifact access, deterministic
  metadata, privacy constraints, and follow-on QTI/service/Skriptoteket gates.
- Task 279 was scaffolded on 2026-05-12 after the product direction was widened
  to include normal teacher-owned Exam.net artifacts, QTI packages, and
  editable DOCX. It records that Sir Convert should use one shared service API
  v2 lifecycle with separate route contracts for DigiExam migration and
  Exam.net artifact authoring.
- The canonical Swedish Exam.net PDF-to-exam renderer profile is now recorded
  in `docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md`.
  Future renderer work should use Swedish labels and exact-text answer keys for
  `Flerval`, `Kort svar`, `Fritext`, and `Matcha ihop` where the profile is
  fixture-backed.
- The QTI direction is now recorded in
  `docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md`.
  Exam.net has reported future QTI 2.1+ support with at least MCQ and free text;
  unsupported resources such as audio, PDFs, and tools require manual follow-up
  instead of silent package inclusion.
- Task 280 was scaffolded on 2026-05-12 as the first QTI implementation slice.
  It must create deterministic QTI 2.1 sample packages and
  `qti_validation_report` output before any service runtime or Skriptoteket
  exposure. Matching remains proof-gated until Exam.net import proof exists.
- Task 281 completed on 2026-05-12 after a 23-file local DigiExam `.dxe`
  validation package was added. The raw OneDrive exports remain ignored and
  local-only; the tracked artifact is a metadata-only corpus manifest proving
  23 successful parses, 317 total items, 8 embedded assets, and only expected
  missing answer-key-provenance warnings.
- Task 282 was scaffolded on 2026-05-13 as the Sir Convert service-runtime
  implementation slice for the DigiExam migration artifact bundle. It owns
  request validation, job execution, bundle persistence, named artifact routes,
  QTI integration, owner-scoped reads, and Sir-side auth rejection behavior.
  HuleEdu `ST-01-07` owns the Gateway/auth-edge route and signer plumbing that
  makes the product flow reachable from Skriptoteket.
- Legacy PDF sample files live under `inputs/examples/digiexam-exports/`.
  The current `.dxe`, blank-PDF, and sanitized result-PDF evidence lives under
  `inputs/examples/digiexam-evidence/2026-05-07-mixed-question-types/`.
- The promoted Exam.net PDF-converter schemas are recorded in
  `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`.
  That reference now preserves the earlier Task 277 evidence, while
  `docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md` owns the
  forward Swedish renderer profile for Exam.net-oriented authoring artifacts.

## Checklist

- [x] Story lane scaffolded after research review.
- [x] Renderer target lanes selected: Exam.net-oriented PDF and QTI/native
  import.
- [x] Parser fixtures and confidence gate defined.
- [x] `.dxe` parser and answer-key provenance lane defined.
- [x] Renderer-neutral IR and manifest schema defined.
- [x] Renderer-neutral embedded asset support defined.
- [x] Exam.net-oriented PDF renderer defined.
- [x] API/artifact bundle contract gate defined.
- [x] Exam.net Swedish PDF-to-exam renderer profile defined.
- [x] QTI validation strategy defined.
- [x] Exam.net teacher-authoring bundle story scaffolded.
- [ ] QTI sample package and validation-report gate implemented.
- [ ] QTI/native renderer defined.
- [ ] Service exposure and Skriptoteket artifact workflow defined.
