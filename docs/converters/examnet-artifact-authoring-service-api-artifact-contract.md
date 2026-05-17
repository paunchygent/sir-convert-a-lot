---
type: converter
id: CONV-examnet-artifact-authoring-service-api-artifact-contract
title: Exam.net Artifact Authoring Service API Artifact Contract
status: draft
created: 2026-05-12
updated: 2026-05-12
owners:
  - platform
tags:
  - examnet
  - qti
  - docx
  - exam-migration
  - api
  - v2
  - artifact-bundle
  - skriptoteket
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
---

## Purpose

Define the proposed service API v2 route for normal teacher-owned Exam.net
authoring artifacts.

This contract is separate from the DigiExam `.dxe` migration route. It covers
teacher workflows where Skriptoteket uploads Exam.net-compatible PDFs, Word
exports, solution/key artifacts, or manually supplied answer sources and
receives reusable authoring artifacts:

- QTI package;
- editable DOCX;
- Exam.net PDF-to-exam converter PDF;
- normalized exam authoring IR;
- validation reports;
- manual-follow-up reports.

This document is draft route authority. It does not approve runtime route
implementation, QTI generation, DOCX generation, or Skriptoteket UI work.

## Relationship To The Shared V2 API Family

Sir Convert should expose one shared service API v2 job lifecycle and separate
route contracts for different source authorities:

| Source route | Output route | Source authority |
| --- | --- | --- |
| `digiexam_dxe` | `examnet_migration_bundle` | DigiExam `.dxe` is the required structure source; sanitized result PDFs may enrich correct answers only. |
| `examnet_artifact` | `teacher_authoring_bundle` | Teacher-owned Exam.net-compatible artifacts are the source and must be classified before conversion. |

The route key for this contract is:

```json
{
  "source.format": "examnet_artifact",
  "conversion.output_format": "teacher_authoring_bundle"
}
```

The route may reuse v2 job creation, polling, terminal result, named artifact,
idempotency, correlation, ownership, and retention semantics from the DigiExam
contract where compatible. It must not reuse DigiExam-specific `.dxe` source
rules or graded-result privacy assumptions.

## Request Contract

`POST /v2/convert/jobs` uses multipart form data.

| Part | Required | Content type | Rules |
| --- | --- | --- | --- |
| `file` | yes | `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, or `application/octet-stream` | Primary teacher-owned source artifact. |
| `job_spec` | yes | `application/json` string | Canonical v2 job spec with the route key below. |
| `answer_key_file` | no | `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`, or `application/json` | Optional teacher-owned answer source. Must be classified before it can provide machine-marked answer provenance. |
| `resource_archive` | no | `application/zip` | Optional image/resource companion for teacher-owned content. Unsupported resource classes are omitted from Exam.net QTI and reported for manual follow-up. |

Initial job spec shape:

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "examnet-export.pdf",
    "format": "examnet_artifact"
  },
  "conversion": {
    "output_format": "teacher_authoring_bundle",
    "targets": ["qti_package", "editable_docx", "examnet_pdf"],
    "artifact_language": "sv"
  },
  "examnet_authoring_options": {
    "source_role": "auto_detect",
    "manual_follow_up_policy": "emit_item_addressable_report",
    "pdf_renderer_profile": "examnet_pdf_to_exam_swedish_v1",
    "qti_profile": "examnet_qti_2_1_initial"
  },
  "retention": {
    "pin": false
  }
}
```

## Source Role Classification

Source classification is required before machine-marked output can be trusted.

| Role | May provide structure | May provide answer key | Notes |
| --- | --- | --- | --- |
| `student_view_pdf` | yes | no | Used for prompt, item order, point value, and visible options when parse confidence is sufficient. |
| `key_or_solution_pdf` | yes | yes | May provide exact answer text only when answers can be bound to item structure. |
| `teacher_export_pdf` | yes | maybe | Must be classified by visible key markers before answer provenance is accepted. |
| `word_export_docx` | yes | maybe | Preferred when it preserves editable semantic structure. |
| `manual_answer_source` | no | yes | May be supplied as structured JSON/text or a teacher-authored key. |
| `unknown` | no | no | Blocks target generation except diagnostics. |

Ambiguous source roles fail closed. The converter must not infer correct answers
from a student-view-only PDF.

## Target Artifacts

The bundle schema name is `teacher_authoring_bundle_v1`.

Required named entries for terminal bundles:

| Artifact key | Filename | Content type | Availability rules |
| --- | --- | --- | --- |
| `bundle_manifest` | `artifact-bundle.json` | `application/json` | Always available for terminal bundles. |
| `qti_package` | `qti-package.zip` | `application/zip` | Available only after QTI generation and validation pass the governed profile. |
| `qti_validation_report` | `qti-validation-report.json` | `application/json` | Always present when QTI is requested or defaulted. |
| `editable_docx` | `editable-exam.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Generated from normalized exam authoring IR, not from visual PDF layout. |
| `examnet_pdf` | `examnet-import.pdf` | `application/pdf` | Uses the Swedish PDF-to-exam renderer profile. |
| `authoring_ir_json` | `exam-authoring-ir.json` | `application/json` | Normalized semantic source shared by QTI, DOCX, and Exam.net PDF outputs. |
| `manual_follow_up_report` | `manual-follow-up.md` | `text/markdown; charset=utf-8` | Always available for terminal bundles. |
| `warnings_report` | `warnings.json` | `application/json` | Always available for terminal bundles. |

Availability values match the DigiExam bundle contract and add
`not_supported_by_examnet` for QTI/resource shapes outside the governed Exam.net
profile.

Task 280 defines the reusable package/report generator and deterministic sample
artifacts for `qti_package` and `qti_validation_report`. This draft route still
requires a later service-runtime implementation before teacher-uploaded
`examnet_artifact` jobs can produce those named artifacts.

## Renderer And QTI Profiles

Exam.net PDF-to-exam converter PDFs must use
`docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md`.

QTI packages must use
`docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md`:

- QTI 2.1 is the initial package floor.
- MCQ and free text are the vendor-reported minimum supported areas.
- Images may be packaged when source IR has renderer-neutral assets and the
  manifest references them deterministically.
- Matching, short answer, and gap fill require explicit target-profile proof
  before production promotion. Matching IR and Exam.net PDF readiness allow
  repeated source or target associations when the item-level matching bounds
  allow them. Exam.net QTI readiness stays vendor-unproven until Exam.net
  exposes a QTI import test path.
- Audio files, PDF attachments, GeoGebra, and tool resources are omitted from
  the Exam.net QTI target and reported for manual follow-up.

## Manual Follow-Up Semantics

Manual follow-up must be item-addressable and teacher-facing. Initial reason
codes:

- `source_role_unknown`
- `manual_answer_key_required`
- `ambiguous_answer_key_binding`
- `single_choice_import_validation_required`
- `unsupported_examnet_qti_resource`
- `not_supported_by_examnet`
- `qti_validation_failed`
- `editable_docx_semantic_structure_incomplete`

Matching is supported for Exam.net PDF when source evidence contains source
prompts, target options, exact directed pairings, and valid matching bounds.
Repeated source or target associations are valid when those bounds allow them.
Unmatched target options may be preserved as distractors. If the source has
matching structure but no correct pairs, preserve the structure and emit
`manual_answer_key_required`.

## Follow-On Gates

Later implementation tasks must add:

- deterministic QTI sample packages and validation reports through Task 280
  before service runtime exposure;
- source-role classification fixtures for PDF, key PDF, DOCX, and manual keys;
- normalized exam authoring IR tests;
- Swedish Exam.net PDF renderer tests for MCQ, multiple response, short answer,
  free text, matching, and images;
- QTI package tests, validation reports, and selected validator integration;
- editable DOCX structure tests;
- owner-scoped named artifact route tests when the service runtime lands.

No runtime implementation is approved by this contract until Story 45 receives
implementation-task authority.
