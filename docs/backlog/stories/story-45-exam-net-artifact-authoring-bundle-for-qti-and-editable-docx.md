---
id: story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx
title: Exam.net artifact authoring bundle for QTI and editable DOCX
type: story
status: proposed
priority: high
created: '2026-05-12'
last_updated: '2026-05-13'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/tasks/task-285-introduce-service-v2-route-policy-handler-registry-before-exam-net-authoring-runtime.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - examnet
  - qti
  - docx
  - authoring
  - artifact-bundle
---

Implementation slice with acceptance-driven scope.

## Objective

Define the Sir Convert product/API lane for normal teacher-owned Exam.net
artifacts: teachers upload Exam.net-compatible PDFs or downloaded Exam.net
Word/PDF exports and receive reusable authoring artifacts, especially QTI
packages and editable DOCX files.

This story is separate from DigiExam migration. It serves teachers who want to
own, edit, archive, and reuse Exam.net-compatible exams outside Exam.net while
still being able to recreate Exam.net exams through PDF-to-exam conversion.

## Scope

- Define `examnet_artifact -> teacher_authoring_bundle` as a route contract
  separate from `digiexam_dxe -> examnet_migration_bundle`, using
  `docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md`
  as the proposed contract surface.
- Classify teacher-owned Exam.net source artifacts by role, for example
  student-view PDF, key/solution PDF, Word export, teacher export, or manually
  supplied answer source.
- Define a normalized exam authoring IR shared by QTI, editable DOCX, and
  Exam.net PDF-to-exam renderer outputs.
- Promote the Swedish PDF-to-exam renderer profile for Exam.net converter PDFs,
  including `Typ: Flerval`, `Typ: Kort svar`, `Typ: Fritext`, and
  `Typ: Matcha ihop`.
- Treat matching questions as supported when source evidence includes left
  prompts, right options, and exact-text correct pairs. Preserve matching
  structure with `manual_answer_key_required` when correct pairs are absent.
- Define QTI package generation and validation expectations using the QTI
  validation strategy reference.
- Implement the first QTI package slice through Task 280: deterministic sample
  packages for MCQ, free text, image-bearing MCQ/free text, and proof-gated
  matching with validation reports.
- Define editable DOCX as semantic authoring output from exam IR, not generic
  visual PDF-to-DOCX conversion.
- Keep service runtime implementation, Skriptoteket UI, and Exam.net browser
  automation out of this story unless later tasks authorize them.
- Treat Story 46 and Task 285 as prerequisites before this route gains service
  runtime behavior: generic job creation must delegate route-specific
  validation and companion reads to a route policy/handler registry.

## Acceptance Criteria

- [ ] A governed route contract names `examnet_artifact -> teacher_authoring_bundle` and distinguishes it from the DigiExam migration
  route.
- [ ] Source role classification is explicit and fail-closed when the uploaded
  PDF/Word artifact cannot be identified safely.
- [ ] The Swedish Exam.net PDF-to-exam renderer profile is linked as the shared
  PDF renderer authority.
- [ ] QTI support is scoped to Exam.net's reported future support: QTI 2.1 and
  later, at least MCQ and free text, with images where supported and
  unsupported audio/PDF/tool resources reported for manual follow-up.
- [ ] A QTI validator ladder is defined before QTI generation lands, including
  local package/XML checks, 1EdTech validator or certification-suite validation,
  optional local semantic smoke, and Exam.net import proof.
- [x] The first QTI implementation emits deterministic sample packages and
  `qti_validation_report` artifacts before service runtime exposure.
- [ ] Service runtime implementation waits for the Story 46 route-handler
  registry so `examnet_artifact -> teacher_authoring_bundle` does not add
  route-specific branching to generic job creation.
- [ ] Editable DOCX output is generated from normalized exam authoring IR and
  preserves item semantics teachers can edit.
- [ ] Matching items are first-class in the authoring IR and supported target
  outputs only when answer-key provenance exists.

## Test Requirements

- [ ] Fixture set includes representative Exam.net-compatible PDF/Word source
  artifacts for MCQ, multiple response, free text, short answer, matching, and
  image-bearing items.
- [ ] Contract tests cover source-role classification and rejected ambiguous
  source uploads.
- [x] QTI tests validate package structure, manifest/resource references, item
  XML, QTI validation report shape, and unsupported-resource manual follow-up.
- [x] QTI sample-package tests cover MCQ, free text, image-bearing MCQ,
  image-bearing free text, and proof-gated matching.
- [ ] DOCX tests verify semantic headings, item boundaries, editable answer
  areas, and matching tables/lists without relying on a visual-only PDF
  conversion.
- [ ] Exam.net converter PDF tests verify the Swedish canonical labels and
  exact-text answer-key profile.

## Done Definition

Story 45 is done when Sir Convert has a governed Exam.net-origin teacher
authoring bundle contract that can later be implemented as QTI, editable DOCX,
and Exam.net PDF-to-exam converter outputs without reusing the DigiExam route or
weakening source-provenance rules.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
