---
id: review-12-ruthless-review-of-task-282-digiexam-migration-service-runtime-artifact-bundle-routes
title: Ruthless review of Task 282 DigiExam migration service runtime artifact bundle routes
type: review
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - scripts/sir_convert_a_lot/application/contracts_v2.py
  - scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py
  - scripts/sir_convert_a_lot/interfaces/http_digiexam_migration_request_v2.py
  - scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py
  - tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py
labels:
  - review
  - task-282
  - digiexam
  - service-runtime
  - artifact-bundle
  - accepted
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: post-implementation retained review of
  `docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md`.
- Governing authority:
  - `docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md`
  - `docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md`
  - `docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md`
  - `docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`
- Files reviewed:
  - `docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md`
  - `docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `scripts/sir_convert_a_lot/application/contracts_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_migration_bundle_contracts.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`
  - `scripts/sir_convert_a_lot/interfaces/http_auth_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_digiexam_migration_request_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_internal_identity_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
  - `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
- Public surfaces affected:
  - `POST /v2/convert/jobs` for
    `digiexam_dxe -> examnet_migration_bundle`.
  - `GET /v2/convert/jobs/{job_id}`.
  - `GET /v2/convert/jobs/{job_id}/result`.
  - `GET /v2/convert/jobs/{job_id}/artifact`.
  - `GET /v2/convert/jobs/{job_id}/artifacts`.
  - `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`.
  - Signed HuleEdu `InternalIdentityContextV1` ownership and grant checks.
  - Terminal `digiexam_migration_bundle_v1` manifest entries and named
    artifact availability.
- Compatibility posture:
  - The new named artifact routes are additive to existing v2 routes.
  - The route-specific bundle/result shapes are public product contracts for
    the HuleEdu/Skriptoteket cutover and must match the accepted Task 278
    contract before approval.
- Evidence reviewed:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`
  - `rg "normalized_digiexam_targets|conversion.targets|ExamMigrationTargetV2|NOT_REQUESTED|NOT_IMPLEMENTED|NOT_SUPPORTED_BY_EXAMNET|not_requested|not_implemented|not_supported_by_examnet" scripts tests docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `rg "route_key|bundle_schema_version|target_availability|manual_follow_up_required|warning_count|artifact_count" scripts tests docs/converters/digiexam-migration-service-api-artifact-contract.md`

## Findings

1. [x] `blocker` - Explicit `conversion.targets` are accepted and normalized, but
   ignored by bundle execution, so the runtime publishes artifacts the caller
   did not request.

   - Evidence:
     The contract allows `conversion.targets` to include `examnet_pdf` and
     `qti_package` and only defaults both when targets are omitted at
     `docs/converters/digiexam-migration-service-api-artifact-contract.md:237`
     and
     `docs/converters/digiexam-migration-service-api-artifact-contract.md:246`.
     The request helper preserves explicit targets in
     `scripts/sir_convert_a_lot/interfaces/http_digiexam_migration_request_v2.py:58`,
     but execution never consumes that value. Instead,
     `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:217`
     always renders the Exam.net PDF, `:250` always builds the QTI package, and
     `:300` always publishes the full fixed target/report set. The `rg`
     evidence shows `normalized_digiexam_targets(...)` is only used inside
     request validation and that `not_requested` is defined in the domain
     contract but not emitted by runtime or tests.
   - Why it matters:
     This breaks the product contract for selective target requests. A caller
     requesting only `examnet_pdf` still gets QTI generation, QTI validation
     report availability, QTI warnings/follow-ups, and bundle status influenced
     by QTI. That can waste runtime, expose misleading availability, and make
     Skriptoteket save or present artifacts the teacher did not ask for.
   - Required fix:
     Carry the normalized target set from request validation into the bundle
     builder or derive it from `job.spec.conversion.targets` at execution time.
     Default to both targets only when the request omitted targets. Emit
     `availability=not_requested` for unrequested target artifacts and skip the
     corresponding generator work. Keep always-on support artifacts such as IR,
     migration manifest, warnings, manual follow-up, and asset summary available
     when parsing reaches that stage.
   - Proof requirement:
     Add API tests that submit explicit `targets=["examnet_pdf"]` and
     `targets=["qti_package"]`, then assert manifest availability,
     `bundle_status`, named artifact errors for unrequested artifacts, and that
     target-specific warnings/follow-ups do not come from skipped generators.
     Rerun
     `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`
     plus `pdm run typecheck-all`.

   Resolved on 2026-05-13. Runtime execution now derives the effective target
   set from `job.spec.conversion.targets`, defaults to both governed targets
   only when omitted, skips unrequested target generators, emits
   `availability=not_requested`, and returns
   `digiexam_artifact_not_requested` for named downloads of skipped targets.
   Focused API tests cover both `targets=["examnet_pdf"]` and
   `targets=["qti_package"]`.

1. [x] `blocker` - `GET /result` omits the route-specific conversion metadata that
   the accepted Task 278/282 API contract publishes for bundle consumers.

   - Evidence:
     The contract states that
     `GET /v2/convert/jobs/{job_id}/result` returns normal v2 result semantics
     with route-specific conversion metadata at
     `docs/converters/digiexam-migration-service-api-artifact-contract.md:308`,
     and the example requires `route_key`, `bundle_schema_version`,
     `bundle_status`, `source_sha256`, `target_availability`,
     `manual_follow_up_required`, `warning_count`, and `artifact_count` at
     `docs/converters/digiexam-migration-service-api-artifact-contract.md:325`.
     The actual result route constructs the generic `ConversionMetadataV2` at
     `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py:113`,
     and that model has no bundle-specific fields in
     `scripts/sir_convert_a_lot/application/contracts_v2.py`. The focused Task
     282 API tests never call `/result`; they only verify `/artifacts`, named
     artifact downloads, and singular `/artifact`.
   - Why it matters:
     Strict Skriptoteket/HuleEdu clients following the published result
     contract cannot discover bundle status or target availability from
     `/result`. They must make an undocumented second manifest call or infer
     semantics from generic `pipeline_used`, which is exactly the product
     contract ambiguity Task 278/282 was supposed to remove.
   - Required fix:
     Add a typed route-specific metadata branch for
     `examnet_migration_bundle` results. Populate it from the persisted
     `artifact-bundle.json` manifest rather than recomputing loosely, and keep
     the generic conversion metadata fields where they remain part of v2
     compatibility. If the intended contract is now manifest-only, amend the
     accepted converter contract and Task 282 before marking this implementation
     approved.
   - Proof requirement:
     Add an API test that posts a successful DigiExam migration job, calls
     `/v2/convert/jobs/{job_id}/result`, and asserts the exact route-specific
     metadata keys and values match the terminal bundle manifest. Rerun
     `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`
     plus `pdm run docs-validate`.

   Resolved on 2026-05-13. `/result` now returns typed
   `DigiExamMigrationConversionMetadataV2` for `examnet_migration_bundle`
   results and populates route key, schema version, bundle status, source hash,
   target availability, manual-follow-up state, warning count, and artifact
   count from the persisted bundle manifest. Focused API coverage asserts that
   `/result` metadata matches the manifest.

## Decision

approved

## Response

Task 282 has good bones: the signed identity path is separated from transport
API-key auth, cross-owner artifact reads fail closed, named artifact downloads
resolve through the persisted manifest, and the QTI/PDF/embedded-image happy
paths are covered by service-route tests.

The two retained public-contract blockers are resolved. Selective
`conversion.targets` now affect runtime artifact generation and manifest
availability, and `/result` publishes manifest-backed route-specific metadata
for bundle consumers.

## Follow-up Actions

1. [x] Fix explicit `conversion.targets` handling and add selective-target API
   tests.
1. [x] Add the route-specific `/result` metadata branch or amend the accepted
   contract before approval.

## Completion

Review opened and retained on 2026-05-13 with `changes_requested`.

Review closed as `approved` on 2026-05-13 after remediation.

Validation run during review:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`:
  `9 passed`.

Remediation validation:

- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`:
  `12 passed`.
- `pdm run typecheck-all`: `Success: no issues found in 622 source files`.
- `pdm run docs-validate`: `Validated 353 backlog files`;
  `Validated docs=412 rules=11`.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
