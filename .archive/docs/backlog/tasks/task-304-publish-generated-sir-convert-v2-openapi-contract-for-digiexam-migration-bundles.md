---
id: task-304-publish-generated-sir-convert-v2-openapi-contract-for-digiexam-migration-bundles
title: Publish generated Sir Convert v2 OpenAPI contract for DigiExam migration bundles
type: task
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - openapi
  - api-contract
  - digiexam
  - skriptoteket
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish a deterministic Sir Convert v2 OpenAPI contract so Skriptoteket can
generate or validate consumer types before Docker/live service tests.

## PR Scope

- Add a canonical `pdm run openapi-export-v2` command that exports OpenAPI from
  the same FastAPI app factory used by the service runtime.
- Commit the generated v2 OpenAPI snapshot under `docs/_generated/openapi/`.
- Include typed DigiExam migration schemas that FastAPI cannot infer from
  multipart `Form`/`UploadFile` signatures:
  `JobSpecV2`, `DigiExamIngestionOverlay`,
  `DigiExamMigrationBundleManifestV2`, `DigiExamTargetReadinessReportV1`,
  `DigiExamEffectiveExamV1`, and `DigiExamIngestionOverlayReportV1`.
- Mark `job_spec` and `digiexam_ingestion_overlay` as multipart JSON parts in
  OpenAPI.
- Add a focused test that fails when the committed OpenAPI snapshot drifts from
  the runtime-generated schema.

## Out Of Scope

- Generating Skriptoteket TypeScript in this repo.
- Changing the runtime request parser or adding compatibility shims.
- Broadening the public grant/read-lease lane beyond existing v2 routes.

## Deliverables

- [x] Runtime OpenAPI includes typed v2 job-create responses.
- [x] Runtime OpenAPI includes DigiExam migration bundle/overlay/readiness
  components.
- [x] Deterministic OpenAPI export command and committed snapshot.
- [x] Contract tests for snapshot freshness and required consumer schemas.
- [x] Docs and generated indexes refreshed.

## Acceptance Criteria

- [x] `/v2/convert/jobs` exposes typed 200/202 create-job responses.
- [x] The multipart body documents `job_spec` and
  `digiexam_ingestion_overlay` as JSON parts with schema references.
- [x] The generated snapshot contains schemas required by Skriptoteket for
  overlay submission, named artifact inspection, effective IR review, and
  target readiness.
- [x] Tests fail if the committed OpenAPI snapshot is stale.
- [x] Standard code/docs validation gates pass.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
