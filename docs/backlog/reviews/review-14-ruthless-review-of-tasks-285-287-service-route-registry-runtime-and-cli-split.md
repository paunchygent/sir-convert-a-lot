---
id: review-14-ruthless-review-of-tasks-285-287-service-route-registry-runtime-and-cli-split
title: Ruthless review of Tasks 285-287 service route registry runtime and CLI split
type: review
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/tasks/task-285-introduce-service-v2-route-policy-handler-registry-before-exam-net-authoring-runtime.md
  - docs/backlog/tasks/task-286-extract-service-v2-runtime-supervision-telemetry-and-checkpoint-planning-modules.md
  - docs/backlog/tasks/task-287-split-cli-route-submission-and-manifest-construction-responsibilities.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - review
  - task-285
  - task-286
  - task-287
  - service-api-v2
  - accepted
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless post-implementation review of Tasks 285-287.
- Governing authority:
  - `docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md`
  - `docs/backlog/tasks/task-285-introduce-service-v2-route-policy-handler-registry-before-exam-net-authoring-runtime.md`
  - `docs/backlog/tasks/task-286-extract-service-v2-runtime-supervision-telemetry-and-checkpoint-planning-modules.md`
  - `docs/backlog/tasks/task-287-split-cli-route-submission-and-manifest-construction-responsibilities.md`
  - `AGENTS.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
- Primary files reviewed:
  - `scripts/sir_convert_a_lot/domain/service_routes_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_job_runner_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_capacity_telemetry_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_supervision_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpoint_chunk_runner.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpoint_planning.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpoint_state.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_app.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_manifest_writer_v2.py`
  - `tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
  - `tests/sir_convert_a_lot/test_runtime_supervision_v2.py`
  - `tests/sir_convert_a_lot/test_v2_pdf_checkpoint_planning_and_state.py`
  - `tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py`
- Public surfaces affected:
  - Service API v2 `POST /v2/convert/jobs` route validation and idempotency.
  - Terminal result metadata for conversion policy fields.
  - CLI route submission and manifest writing behavior.
- Compatibility posture:
  - Route-boundary cleanup may refactor internals, but must not make
    non-applicable API fields influence idempotency or terminal metadata.
  - Future route policies must not silently become runtime handlers without an
    explicit route-owned handler.
- Evidence reviewed:
  - `git status --short --branch`
  - `git diff --stat`
  - Focused code reads with line-numbered inspection.
  - `pdm run python` probes for `JobSpecV2` non-PDF option acceptance and
    current route-policy keys.
  - `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_v2_pdf_checkpoint_planning_and_state.py -q`
    -> 10 passed.

## Findings

1. **high - Non-applicable PDF/execution options are not actually ignored for non-PDF routes.**

   Evidence:

   - `scripts/sir_convert_a_lot/domain/service_routes_v2.py:113`
     defaults `allows_pdf_options=True`.
   - `scripts/sir_convert_a_lot/domain/service_routes_v2.py:115`
     defaults `allows_execution=True`.
   - `_generic_route_policy(...)` only sets `requires_pdf_options` and
     `requires_execution` from `source_is_pdf` at
     `scripts/sir_convert_a_lot/domain/service_routes_v2.py:138` and
     `scripts/sir_convert_a_lot/domain/service_routes_v2.py:139`; it does not
     set `allows_*` false for `docx`, `md`, or `html` sources.
   - HTTP idempotency still fingerprints the raw submitted spec at
     `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:248`.
   - Terminal metadata persists any submitted execution policy at
     `scripts/sir_convert_a_lot/infrastructure/runtime_job_runner_v2.py:208`
     via
     `scripts/sir_convert_a_lot/infrastructure/runtime_capacity_telemetry_v2.py:179`.
   - The public v2 contract says `pdf_options` is ignored for non-PDF sources
     and `execution.acceleration_policy` is ignored otherwise, with terminal
     `acceleration_policy_requested` null where execution policy is not
     applicable (`docs/converters/multi_format_conversion_service_api_v2.md`).

   Why it matters:
   A caller can submit `md -> pdf` or `html -> docx` with `pdf_options` and
   `execution`. Those fields are not used by the converter, but they change the
   idempotency fingerprint and can make terminal metadata report an
   `acceleration_policy_requested` value for a route where the policy is
   supposed to be non-applicable. That is not "ignored"; it is contract-visible
   drift and misleading runtime evidence.

   Required fix:
   Make route-policy metadata encode non-applicability explicitly. Either reject
   `pdf_options` and `execution` on non-PDF routes with typed validation errors,
   or normalize them out consistently before idempotency and terminal metadata.
   The repo's fail-closed posture favors rejection unless the public contract is
   intentionally amended to preserve an "accepted but ignored" compatibility
   window.

   Proof requirement:
   Add focused `JobSpecV2` and HTTP create-job tests for `md -> pdf`,
   `html -> pdf`, and `docx -> md` with supplied `pdf_options`/`execution`.
   Prove the selected corrected behavior and run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py -q`
   plus the standard backend gates for the touched code.

1. **high - The registry auto-registers every supported policy with the default handler, so future route metadata can accidentally ship runtime behavior.**

   Evidence:

   - `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py:192`
     iterates every `supported_route_keys_v2()`.
   - `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py:196`
     special-cases only the DigiExam migration route.
   - `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py:198`
     attaches `DefaultCreateJobRouteHandlerV2` to every other supported route.
   - `tests/sir_convert_a_lot/test_create_job_route_registry_v2.py:45` locks in
     `registry.registered_route_keys() == supported_route_keys_v2()`, so tests
     currently require every policy to have a handler automatically.

   Why it matters:
   Task 285 exists specifically to create a route-owned handler boundary before
   `examnet_artifact -> teacher_authoring_bundle` runtime work. With the
   current builder, adding a future non-generic route to shared policy metadata
   is enough to register the default handler and let `POST /v2/convert/jobs`
   accept jobs through generic companion handling. That is a false fallback:
   metadata addition becomes runtime exposure without an explicit handler,
   tests, or route-owned validation.

   Required fix:
   Replace the catch-all registration loop with explicit handler composition.
   Generic document routes can still share one handler, but the mapping must be
   explicit and fail closed when policy metadata has no handler factory. Add a
   test that a policy key without a registered handler makes registry build or
   lookup fail with a typed `unsupported_v2_route`/configuration error instead
   of defaulting to generic behavior.

   Proof requirement:
   Add a regression test that monkeypatches an extra policy key without a
   handler factory and proves the default registry does not auto-enable it.
   Keep the existing DigiExam and generic route tests, then run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py -q`.

## Decision

Initial decision: `changes_requested`.

Final re-review decision: `approved`.

## Response

Re-review on 2026-05-13:

- Finding 2 is resolved. `build_create_job_route_registry_v2()` now registers
  `DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2` explicitly plus the DigiExam
  migration handler, and
  `test_create_job_registry_does_not_auto_register_supported_policy_without_handler`
  proves route-policy metadata alone does not auto-enable a handler.
- Finding 1 is only partially resolved. Valid ignored `pdf_options` and
  `execution` values are normalized off `JobSpecV2`, removed from create-job
  fingerprint payloads, and no longer surface as terminal
  `acceleration_policy_requested`. However, malformed ignored values still fail
  Pydantic field validation before `JobSpecV2._validate_route` can strip them.
  The public contract and Task 285 remediation note both say these fields are
  ignored for non-PDF routes, not "validated when present but ignored later".
  Probe:
  `JobSpecV2.model_validate({"source":{"format":"md"}, "conversion":{"output_format":"pdf"}, "pdf_options":{"backend_strategy":"not-a-backend"}, "execution":{"acceleration_policy":"not-a-policy"}})`
  still reports `pdf_options.*` and `execution.acceleration_policy` validation
  errors.

## Follow-up Actions

1. Remediate the non-PDF `pdf_options`/`execution` semantics so ignored fields
   cannot affect idempotency or terminal runtime metadata.
1. Make create-job route-handler registration explicit and fail closed when a
   supported route policy lacks a route-owned handler.
1. Finish the ignored-field remediation by stripping route-ignored top-level
   runtime options before nested Pydantic field validation, or amend the public
   contract to say ignored fields must still be schema-valid when present.

## Completion

Review 14 is retained as `changes_requested` on 2026-05-13.

Second re-review on 2026-05-13 remains `changes_requested`.

Additional validation:

- `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_specs_v2.py tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py -q`
  -> 78 passed.
- `pdm run python` probe above reproduced the remaining ignored-field validation
  drift.

Remediation update after the second re-review:

- `JobSpecV2` now strips route-ignored top-level `pdf_options` and `execution`
  before nested Pydantic validation, so malformed ignored values on non-PDF
  routes are ignored instead of rejected.
- The same probe now returns `spec.pdf_options=None` and `spec.execution=None`.
- Focused regression tests passed with `76 passed`; `pdm run coverage-gate`
  passed with 1159 passed, 5 skipped, and total coverage 95.93%.
- Review 14 remained `changes_requested` until the separate reviewer acceptance
  pass below.

Third re-review on 2026-05-13:

- Finding 1 is resolved. The route-ignored `pdf_options` and `execution` keys
  are stripped in a `mode="before"` `JobSpecV2` validator, before nested
  Pydantic field validation can reject malformed ignored values.
- Reviewer probe:
  - `md -> pdf` with malformed `pdf_options` and `execution` now validates with
    `spec.pdf_options=None` and `spec.execution=None`.
  - `pdf -> md` with malformed `pdf_options` and `execution` still fails field
    validation, so PDF-source runtime options remain strict.
  - unsupported `digiexam_dxe -> pdf` remains rejected rather than becoming a
    supported route.
- Finding 2 remains resolved from the prior pass: route-policy metadata alone
  does not auto-register a create-job handler.
- All Review 14 follow-up actions are resolved.

Review 14 is closed as `approved` on 2026-05-13.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
