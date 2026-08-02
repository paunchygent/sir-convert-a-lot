---
type: story
id: ST-SIRCON-07-01
title: Exam.net artifact authoring bundle for QTI and editable DOCX
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-07
links:
  decisions: []
acceptance_criteria:
- A governed route contract names `examnet_artifact -> teacher_authoring_bundle` and
  distinguishes it from the DigiExam migration route.
- Source role classification is explicit and fail-closed when the uploaded PDF/Word
  artifact cannot be identified safely.
- The Swedish Exam.net PDF-to-exam renderer profile is linked as the shared PDF renderer
  authority.
- 'QTI support is scoped to Exam.net''s reported future support: QTI 2.1 and later,
  at least MCQ and free text, with images where supported and unsupported audio/PDF/tool
  resources reported for manual follow-up.'
- A QTI validator ladder is defined before QTI generation lands, including local package/XML
  checks, 1EdTech validator or certification-suite validation, optional local semantic
  smoke, and Exam.net import proof.
- The first QTI implementation emits deterministic sample packages and `qti_validation_report`
  artifacts before service runtime exposure.
- Service runtime implementation waits for the Story 46 route-handler registry so
  `examnet_artifact -> teacher_authoring_bundle` does not add route-specific branching
  to generic job creation.
- Editable DOCX output is generated from normalized exam authoring IR and preserves
  item semantics teachers can edit.
- Matching items are first-class in the authoring IR and supported target outputs
  only when answer-key provenance exists.
- New source parser implementation remains blocked until Task 307 defines the first
  `ExamAuthoringIR v1` matching slice, documents the parser-adapter-neutral-IR architecture,
  and blocks target exporters from consuming source-specific parse DTOs directly.
retired_ids:
- story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx
---
## Context

Source record: docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md

### Objective

> Define the Sir Convert product/API lane for normal teacher-owned Exam.net
> artifacts: teachers upload Exam.net-compatible PDFs or downloaded Exam.net
> Word/PDF exports and receive reusable authoring artifacts, especially QTI
> packages and editable DOCX files.
>
> This story is separate from DigiExam migration. It serves teachers who want to
> own, edit, archive, and reuse Exam.net-compatible exams outside Exam.net while
> still being able to recreate Exam.net exams through PDF-to-exam conversion.

## Epic Contract Slice

### Scope

> - Define `examnet_artifact -> teacher_authoring_bundle` as a route contract
>   separate from `digiexam_dxe -> examnet_migration_bundle`, using
>   `docs/reference/ref-sircon-general-exam-net-artifact-authoring-service-api-artifact-contract-exam-net-artifact-authoring-service-api-artifact-contract.md`
>   as the proposed contract surface.
> - Classify teacher-owned Exam.net source artifacts by role, for example
>   student-view PDF, key/solution PDF, Word export, teacher export, or manually
>   supplied answer source.
> - Define a normalized exam authoring IR shared by QTI, editable DOCX, and
>   Exam.net PDF-to-exam renderer outputs.
> - Treat Task 307 as a hard architectural blocker before implementing any new
>   Exam.net PDF, teacher-authored DOCX, or teacher-authored Markdown source
>   parser. Those sources must map through a source-adapter-to-`ExamAuthoringIR`
>   boundary rather than reusing DigiExam-specific parser/IR contracts or
>   duplicating DigiExam parsing logic.
> - Promote the Swedish PDF-to-exam renderer profile for Exam.net converter PDFs,
>   including `Typ: Flerval`, `Typ: Kort svar`, `Typ: Fritext`, and
>   `Typ: Matcha ihop`.
> - Treat matching questions as supported when Exam.net or teacher-authored
>   source evidence includes source prompts, target options, and exact-text
>   correct pairs. Preserve matching structure with
>   `manual_answer_key_required` when correct pairs are absent.
> - Define QTI package generation and validation expectations using the QTI
>   validation strategy reference.
> - Implement the first QTI package slice through Task 280: deterministic sample
>   packages for MCQ, free text, image-bearing MCQ/free text, and proof-gated
>   matching with validation reports.
> - Define editable DOCX as semantic authoring output from exam IR, not generic
>   visual PDF-to-DOCX conversion.
> - Keep service runtime implementation, Skriptoteket UI, and Exam.net browser
>   automation out of this story unless later tasks authorize them.
> - Treat Story 46 and Task 285 as prerequisites before this route gains service
>   runtime behavior: generic job creation must delegate route-specific
>   validation and companion reads to a route policy/handler registry.

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review
