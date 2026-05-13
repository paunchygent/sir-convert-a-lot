---
id: task-285-introduce-service-v2-route-policy-handler-registry-before-exam-net-authoring-runtime
title: Introduce service v2 route policy handler registry before Exam.net authoring runtime
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md
labels:
  - service-api-v2
  - route-registry
  - examnet
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Introduce a route policy/handler registry keyed by `(source_format, output_format)` before implementing `examnet_artifact -> teacher_authoring_bundle`. The generic service job endpoint should own generic
request mechanics, while route handlers own route-specific validation,
companion reads, target normalization, and job-spec construction.

The registry must become the single route-authority boundary. The current
`JobSpecV2._validate_route` hardcoded allowed-route set and route-specific
DigiExam option guards must be removed or replaced by delegation to shared
route-policy metadata so model validation, HTTP create-job handling, and future
route implementation cannot drift.

## PR Scope

- Define a typed service API v2 route policy/handler contract for route
  validation, companion artifact handling, target selection, and job-spec
  preparation.
- Register route handlers by `(source_format, output_format)` instead of adding
  route-specific branches to generic job creation.
- Define shared route metadata as the only source for supported v2 route pairs
  and route-specific job-spec option rules. `JobSpecV2` may keep generic shape
  validation, but must not keep its own hardcoded route allowlist or
  DigiExam-specific option matrix.
- Keep generic `create_job` responsibilities limited to multipart parsing,
  authentication/authorization context, idempotency calculation, generic
  request validation, route lookup, and shared job persistence.
- Move existing DigiExam-specific upload/companion behavior behind the registry
  without changing the `digiexam_dxe -> examnet_migration_bundle` contract.
- Prepare the registry for the draft `examnet_artifact -> teacher_authoring_bundle` route by keeping registration additive and
  route-owned, but do not add a disabled placeholder route or runtime behavior
  for that draft route in this task.

## Deliverables

- [x] Route handler protocol or equivalent domain contract.
- [x] Registry composition for existing production routes.
- [x] Shared route metadata consumed by both `JobSpecV2` validation and HTTP
  route lookup, replacing duplicate hardcoded route truth.
- [x] DigiExam migration route policy extracted from generic job creation.
- [x] Unsupported or unregistered route failures remain typed and fail closed.
- [x] Documentation notes the registry as the prerequisite boundary for future
  Exam.net authoring runtime work.

## Acceptance Criteria

- [x] No new `examnet_artifact -> teacher_authoring_bundle` runtime behavior
  ships in this task, and no disabled placeholder handler is registered for the
  draft route.
- [x] Generic job creation no longer contains route-specific DigiExam or
  Exam.net validation branches beyond route lookup and handler invocation.
- [x] `JobSpecV2._validate_route` no longer owns a hardcoded allowed-route set
  or DigiExam-specific option guards; route-policy metadata is the shared source
  for allowed routes and route-specific option validation.
- [x] Existing DigiExam service-route tests still pass unchanged in externally
  visible behavior.
- [x] New tests cover route lookup, missing route rejection, DigiExam companion
  validation through the handler, `JobSpecV2` route-policy delegation, and
  idempotency preservation.
- [x] New or materially changed Python modules have Google-style module
  docstrings that describe domain purpose and relationships.
- [x] Close-out validation includes format, lint, typecheck, focused service API
  tests, docs-sync, docs-validate, skills-validate, handoff-validate, and
  `git diff --check`.

## Implementation Notes

- Added `domain.service_routes_v2` as the shared service API v2 route-policy
  metadata surface.
- Added `interfaces.http_create_job_routes_v2` as the create-job route handler
  registry and preparation boundary.
- `JobSpecV2._validate_route` now delegates to route-policy metadata instead of
  owning route pairs or DigiExam option guards.
- `interfaces.http_routes_jobs_v2` resolves a route handler, applies the
  route-policy auth grant requirement, and persists the prepared companion
  bytes without DigiExam-specific branches.
- The draft `examnet_artifact -> teacher_authoring_bundle` route is not
  registered and no runtime behavior ships in this task.
- Review 14 remediation keeps the public v2 "ignored otherwise" contract for
  non-PDF `pdf_options` and `execution`: route policy marks them as ignored,
  `JobSpecV2` strips them before nested Pydantic validation and normalizes them
  to `None`, create-job idempotency removes the raw ignored keys before
  fingerprinting, and terminal metadata reports
  `acceleration_policy_requested=null` for non-applicable routes.
- Review 14 remediation also makes handler registration explicit:
  `DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2` plus the DigiExam migration
  handler are registered intentionally; adding route-policy metadata alone no
  longer gives a route the default handler.

## Validation Evidence

- `pdm run format-all` -> 3 files reformatted on the first pass; final pass left
  674 files unchanged.
- `pdm run lint-fix` -> All checks passed; 674 files left unchanged; validated
  docs=422 rules=11 and 363 backlog files.
- `pdm run typecheck-all` -> Success: no issues found in 625 source files.
- `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`
  -> 45 passed.
- `pdm run coverage-gate` -> 1147 passed, 5 skipped; total coverage 95.30%.
- `pdm run docs-sync` -> refreshed generated docs indexes.
- `pdm run docs-validate` -> Validated 363 backlog files; Validated docs=422
  rules=11.
- `pdm run skills-validate` -> ok.
- `pdm run handoff-validate` -> ok.
- `git diff --check` -> clean.

## Review 14 Remediation Evidence

- `pdm run format-all` -> 2 files reformatted on first remediation pass; final
  pass left 687 files unchanged.
- `pdm run lint-fix` -> Found 3 errors (3 fixed, 0 remaining); final pass left
  687 files unchanged and validated docs=424 rules=11 plus 365 backlog files.
- `pdm run typecheck-all` -> Success: no issues found in 638 source files.
- Focused Review 14 regression tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_specs_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_api_contract_v2.py::test_non_pdf_pdf_runtime_options_are_ignored_for_idempotency_and_metadata tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py::test_execute_v2_job_conversion_html_to_md_ignores_non_pdf_execution_spec tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`
  -> 76 passed.
- Reviewer probe with malformed ignored `pdf_options` and `execution` on an
  `md -> pdf` route -> `spec.pdf_options=None`, `spec.execution=None`.
- `pdm run coverage-gate` -> 1159 passed, 5 skipped; total coverage 95.93%.
- Review 14 accepted on the third re-review.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
