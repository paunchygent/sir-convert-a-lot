---
id: task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile
title: Define Exam.net artifact source contract and Swedish PDF-to-exam renderer profile
type: task
status: completed
priority: high
created: '2026-05-12'
last_updated: '2026-05-12'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - examnet
  - qti
  - docx
  - authoring
  - contract
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Persist the Exam.net-origin teacher authoring direction before QTI or DOCX
implementation starts.

The task defines the source-artifact contract, Swedish Exam.net PDF-to-exam
renderer profile, QTI validation strategy, and separation from the existing
DigiExam migration route.

## PR Scope

- Promote the Swedish Exam.net PDF-to-exam format profile into durable
  reference docs:
  - `Fråga N`;
  - `Poängvärde: N`;
  - `Typ: Flerval`;
  - `Typ: Kort svar`;
  - `Typ: Fritext`;
  - `Typ: Matcha ihop` / `Typ: Para ihop`;
  - exact-text `Rätt svar`, `Rätta svar`, and `Rätta par`.
- Define the authoring API direction as one shared v2 job family with two
  route contracts:
  - `digiexam_dxe -> examnet_migration_bundle`;
  - `examnet_artifact -> teacher_authoring_bundle`.
- Add a proposed converter contract for
  `examnet_artifact -> teacher_authoring_bundle`, including source role
  classification, named artifacts, QTI validation report, editable DOCX, and
  manual-follow-up semantics.
- Define source-role classes for Exam.net-origin artifacts:
  student-view PDF, key/solution PDF, teacher export PDF, Word export, and
  manually supplied answer source.
- Define QTI support boundaries from current Exam.net vendor-reported
  direction:
  - QTI 2.1 and later;
  - at least MCQ and free text;
  - images where supported;
  - no automatic carry-over for audio, PDFs, or tool resources such as
    GeoGebra.
- Define a QTI validation ladder:
  local package/XML validation, 1EdTech validator or certification-suite
  validation, optional QTIWorks semantic smoke for QTI 2.1, and Exam.net import
  proof.
- Define editable DOCX as semantic authoring output from normalized exam IR,
  not generic visual PDF-to-DOCX conversion.
- Update EPIC-10, Task 278 links/notes, and handoff so QTI work starts from the
  correct broader route-family direction.
- Do not implement QTI generation, DOCX generation, service runtime routes, or
  Skriptoteket UI in this task.

## Deliverables

- [x] Exam.net PDF-to-exam Swedish renderer profile reference.
- [x] Exam.net QTI import contract and validation strategy reference.
- [x] Story 45 scaffolded as the Exam.net-origin authoring bundle lane.
- [x] Exam.net artifact authoring route contract scaffolded.
- [x] EPIC-10 updated to distinguish DigiExam migration from Exam.net artifact
  authoring.
- [x] Task 278/DigiExam API contract cross-linked without overloading the
  DigiExam route.
- [x] Handoff updated with the next governed direction.

## Acceptance Criteria

- [x] The docs clearly recommend one shared service API v2 job lifecycle with
  separate route contracts, not two unrelated APIs and not one overloaded route.
- [x] The Exam.net-origin route names QTI and editable DOCX as first-class
  target artifacts.
- [x] Matching is documented as supported when exact pair provenance exists and
  manual-follow-up when pair provenance is absent.
- [x] The QTI direction reflects Exam.net's reported future support and does
  not claim shipped/import-proven Exam.net support before live proof.
- [x] The QTI validator strategy names 1EdTech validation as the authority and
  local/QTIWorks checks as provisional support gates.
- [x] Unsupported QTI resources are documented as omitted from the Exam.net
  target with manual follow-up, not silently carried.
- [x] The task does not implement runtime code.

## Validation

- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Follow-On

Task 280 is the next implementation authority: deterministic QTI 2.1 sample
packages and `qti_validation_report` output for MCQ, free text, image-bearing
MCQ/free text, and proof-gated matching.
