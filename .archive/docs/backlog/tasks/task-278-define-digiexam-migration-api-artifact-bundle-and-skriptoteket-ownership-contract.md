---
id: task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract
title: Define DigiExam migration API artifact bundle and Skriptoteket ownership contract
type: task
status: completed
priority: high
created: '2026-05-11'
last_updated: '2026-05-12'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
labels:
  - exam-migration
  - digiexam
  - examnet
  - api-v2
  - skriptoteket
  - contract
  - artifact-bundle
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the first accepted API and artifact-bundle contract for exposing
DigiExam migration through Sir Convert service API v2 to an authenticated
Skriptoteket app workflow.

This task is a contract gate. It must land before QTI/native package
implementation, service-runtime wiring, or Skriptoteket UI work claims a stable
public product surface.

## PR Scope

- Create or update a converter/API contract document for the DigiExam migration
  service surface. The contract must describe:
  - request shape for `.dxe` primary upload plus optional sanitized graded-result
    PDF and optional parity evidence;
  - accepted and rejected companion-file classes;
  - idempotency and correlation-header expectations for Skriptoteket adapters;
  - terminal result shape and named artifact bundle entries;
  - content types, deterministic filenames, sizes, hashes, and retention;
  - fail-closed errors for missing structure source, invalid source payload,
    unsafe companion evidence, blocked IR, missing target artifact, and
    unsupported target shapes.
- Define the artifact bundle as the contract between Sir Convert and
  Skriptoteket:
  - Exam.net-oriented PDF artifact;
  - QTI/native package placeholder contract, blocked until the QTI task lands;
  - IR and migration manifest artifacts;
  - manual-follow-up report for missing answer keys, unsupported target shapes,
    and teacher-required checks;
  - warnings report with typed codes and item references;
  - asset summary records without embedding private raw payloads in manifests.
- Define ownership semantics:
  - Sir Convert owns parsing, enrichment, rendering, artifact manifesting, and
    job/artifact authorization.
  - Skriptoteket owns authenticated teacher UI, progress presentation,
    downloads, and save-to-user-files persistence.
  - Skriptoteket adapters remain thin and must not fork conversion policy or
    inspect private Sir Convert work directories.
- Align the contract with `internal_adapter_contract_v2.md` and the
  InternalIdentityContextV1 authorization profile for user-originated calls.
- Update EPIC-10, Story 44, and handoff pointers so QTI/service/UI tasks are
  sequenced behind this accepted contract.
- Do not implement runtime code in this task unless a tiny schema/test probe is
  required to make the contract executable.

## Deliverables

- [x] DigiExam migration service API/artifact contract doc or section.
- [x] Artifact bundle schema with named entries, content types, hash/size
  metadata, retention, and privacy constraints.
- [x] Request/response examples for Skriptoteket: submit, poll, list result
  artifacts, download/save artifacts, and handle blocked/manual-follow-up
  outcomes.
- [x] Error-code table for invalid `.dxe`, unsafe companion result PDF, blocked
  IR, missing answer-key evidence, unsupported target shapes, QTI not yet
  available, and unauthorized artifact access.
- [x] Adapter conformance additions or explicit follow-up test requirements for
  Skriptoteket.
- [x] Updated EPIC-10 and Story 44 sequencing notes.

## Acceptance Criteria

- [x] The contract makes `.dxe` the required structure source and treats
  sanitized graded-result PDFs as optional correct-answer evidence only.
- [x] The contract explicitly forbids retaining wrong answers, free-text student
  answers, scores, identity markers, and student-performance history from
  result PDFs.
- [x] The terminal artifact bundle is deterministic and consumer-readable:
  Skriptoteket can display/download/save artifacts using named entries and
  metadata without reading Sir Convert internal directories.
- [x] The contract defines how partial target availability is represented:
  PDF may be present while QTI is blocked/not implemented, but missing QTI must
  be explicit and machine-readable.
- [x] Manual-follow-up semantics are first-class and item-addressable, including
  missing answer keys, unsupported target shapes, and teacher checks such as
  single-choice import validation.
- [x] Authenticated job and artifact access is owner-scoped and aligned with
  the current API key plus Gateway/InternalIdentityContextV1 transition plan.
- [x] The task does not expose a direct anonymous Sir Convert public conversion
  surface.
- [x] The contract states exactly which later tasks may implement QTI/native
  rendering, service-runtime exposure, and Skriptoteket UI/file persistence.

## Validation

- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Stop Conditions

- Stop before implementing QTI/native package generation.
- Stop before adding or changing service API runtime routes.
- Stop before changing Skriptoteket code or authenticated file storage.
- Stop before promising anonymous public access or direct Exam.net upload.
- Stop before weakening result-PDF privacy constraints or retaining student
  result data.

## Post-Completion Alignment

On 2026-05-12, Task 279 extended the EPIC-10 contract direction with a sibling
Exam.net-origin authoring route. Task 278 remains the completed authority for
the DigiExam `.dxe` migration route only.

The shared route family is:

- `digiexam_dxe -> examnet_migration_bundle`
- `examnet_artifact -> teacher_authoring_bundle`

Both routes may share named artifact concepts such as QTI packages, editable
DOCX, Swedish Exam.net PDF-to-exam converter PDFs, validation reports, and
manual-follow-up artifacts, but they do not share source-authority rules.

On 2026-05-13, Task 282 was scaffolded as the Sir Convert service-runtime
implementation authority for the DigiExam migration bundle route. The HuleEdu
auth-edge execution authority moved to:

`/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
