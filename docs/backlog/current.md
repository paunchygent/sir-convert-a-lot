---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
  - docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md
  - docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md
  - docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/backlog/tasks/task-59-enforce-90-percent-test-coverage-gate-for-conversion-core.md
labels:
  - session-log
  - active-work
---

## Context

Active focus has shifted to Epic 05: a prototype-to-production hardening track that enforces a
**v2-only conversion architecture** with explicit Markdown ingress routes and template-governed DOCX
outputs.

This file is the canonical long-term memory index for session progress; session handoff summaries
must be archived here when `handoff.md` is pruned.

Entrypoints:

- `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md`
- `docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md`

Primary implementation stories:

- `docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md`
- `docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md`
- `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md`
- `docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md`
- `docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md` (next
  slice after clean-break gates)

## Worklog

- 2026-02-28:

  - Shifted the active planning context from Epic 04 coexistence assumptions to Epic 05 clean-break
    requirements from the latest brutal review directive.
  - Completed coverage hardening gate task (`T01` / Task 59):
    - conversion-core coverage gate is passing at `92.77%` with enforced fail-under `90%`,
    - strict typing cleanup completed for v2 edge-case test modules with file-size compliance
      (`<500` LoC per file after split).
  - Activated first real implementation slice for Epic 05 clean-break execution:
    - `docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md`
      moved to `in_progress` with an ordered Slice 44A implementation plan.
  - Completed Slice 44B and terminalized Task 44:
    - removed v1 conversion route registration from service API wiring,
    - removed CLI v1 conversion branching and locked `pdf -> md` to v2,
    - migrated contract tests to assert v1 conversion route absence + v2 `pdf -> md` lifecycle,
    - passed full gates including `coverage-gate` at `96.10%`,
    - checked `T04` in Epic 05 after task status reached `completed`.
  - Completed Slice 45A and terminalized Task 45:
    - hardened v2 route-option validation parity (API rejects `resources` and `reference_docx` for
      `output_format="md"`),
    - extended CLI manifest contract with deterministic route metadata
      (`source_format`, `target_format`, `pipeline_used`),
    - strengthened v2 contract/CLI tests (strict no-op status expectations, route-table v1 absence,
      artifact content-type assertions, idempotency/correlation propagation checks),
    - added deterministic non-GPU adapter E2E submit/poll/fetch + idempotent replay lane,
    - passed full gates including `coverage-gate` at `96.14%`,
    - checked `T05` and Story `S01` in Epic 05 after task/story terminalization.
  - Completed Slice 46A and terminalized Task 46:
    - published the normative DOCX template catalog contract:
      - `docs/converters/docx-template-catalog-contract-v2.md`
    - synced v2 converter contract doc with template selector and template discovery rollout
      contract references:
      - `docs/converters/multi_format_conversion_service_api_v2.md`
    - checked `T06` in Epic 05 after task status reached `completed`.
  - Completed Slice 47A and terminalized Task 47:
    - implemented v2 DOCX template catalog store + integrity checks and discovery endpoints
      (`/v2/templates/docx*`),
    - integrated `conversion.template` selector validation + deterministic create-job errors for
      unknown template ids/versions,
    - shipped three curated DOCX fixture templates (`academic-report`, `classroom-handout`,
      `project-week-summary`),
    - added template audit metadata to successful result contracts
      (`template_id`, `template_version`, `template_artifact_sha256`),
    - passed full gates including `coverage-gate` at `95.41%`,
    - checked `T07` and Story `S02` in Epic 05 after task/story terminalization.
  - Activated Task 48 planning slice (`docx -> md`):
    - moved Task 48 to `in_progress`,
    - added an ordered execution plan, risk controls, test matrix, and validation command block.
  - Completed Slice 48A and terminalized Task 48:
    - implemented v2 `docx -> md` route path across domain contract, HTTP create validation, client
      content-type inference, CLI route registry, and runtime executor branch,
    - added dedicated converter + normalization modules:
      - `scripts/sir_convert_a_lot/infrastructure/pandoc_docx_to_markdown.py`
      - `scripts/sir_convert_a_lot/infrastructure/markdown_normalization_v2.py`
    - added deterministic contract coverage for lifecycle, executor behavior, and CLI route flow:
      - `tests/sir_convert_a_lot/test_api_contract_v2_docx_to_md.py`
      - `tests/sir_convert_a_lot/test_v2_conversion_executor_docx_to_md.py`
      - `tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py`
    - synchronized converter docs for `docx -> md` route matrix, route semantics, and deterministic
      error mapping.
    - passed full gates including `coverage-gate` (`332 passed, 5 skipped`; total coverage `95.08%`),
      then checked Epic `T08` after task terminalization.
  - Activated Task 49 planning slice (`html -> md` with resources + deterministic normalization):
    - moved Task 49 to `in_progress`,
    - added ordered Slice 49A execution plan, explicit resources-policy decision, risk controls,
      test matrix, and validation command block.
  - Completed Slice 49A and terminalized Task 49:
    - implemented v2 `html -> md` route across domain contract, route validations, executor
      branching, and CLI route/payload handling,
    - added deterministic local-resource validation for HTML markdown ingress
      (`html_resource_not_found`, `html_resource_invalid`),
    - added dedicated Pandoc wrapper for HTML->Markdown conversion:
      - `scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_markdown.py`,
    - updated converter/CLI docs with `html -> md` route semantics, examples, and deterministic
      error contracts,
    - added lifecycle/executor/converter/CLI tests for `html -> md`:
      - `tests/sir_convert_a_lot/test_api_contract_v2_html_to_md.py`
      - `tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py`
      - `tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py`
    - passed full gates including `coverage-gate` (`347 passed, 5 skipped`; total coverage
      `95.21%`), then checked Epic `T09` after task terminalization.
  - Updated async push planning docs to require adapter non-GPU E2E updates in the same PR as push
    logic changes:
    - `docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md`
    - `docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md`
    - `docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md`
  - Rewrote `review-01-brutal-review-service-api-v2-multi-format-pivot` as the active code-review
    authority, including mandatory v2-only, no-deprecation execution constraints.
  - Epic 05 planning surfaces are established and now tracked by the epic/story/task files directly.
  - Async push planning stack is in place (`Story 15`, ADR `0003`, Tasks `53-59`) and queued after
    completed clean-break slices.
  - Performed a careful planning hardening pass for upcoming cleanup/integration tasks:
    - Task 52 now has explicit sequencing/dependency guidance for downstream contract publication.
    - Task 50 now includes a concrete single-runtime cutover plan, risk controls, and validation
      matrix tied to eval-container removal.
    - Task 51 now includes explicit active-surface hygiene scope, v2-only purge steps, and
      deterministic validation commands.
  - Completed Slice 52A and terminalized Task 52 (`T10`):
    - published downstream v2 integration contract:
      - `docs/converters/downstream_integration_contract_v2.md`
    - linked active converter/runbook docs to downstream contract authority.
    - checked Epic `T10` and Story `S03` after task/story terminalization.
  - Completed Slice 50A and terminalized Task 50 (`T11`):
    - removed eval runtime topology from compose/docker/script/runtime/test surfaces,
    - removed eval entrypoint module and eval readiness branches,
    - verified single-runtime docker and v2 conversion probes.
  - Completed Slice 51A and terminalized Task 51 (`T12`):
    - purged stale active-surface v1/local-hybrid docs and code references,
    - removed inactive v1 job-router module from interfaces,
    - converted compatibility client transport to v2 endpoints only,
    - simplified CLI route kind semantics to service-only.
  - Synchronized status/checkoff order:
    - Task 50 -> `completed` -> Epic `T11` checked,
    - Task 51 -> `completed` -> Epic `T12` checked,
    - Story 12 -> `completed` -> Epic `S04` checked.
  - Validation evidence for T10-T12 + S04 closeout:
    - `pdm run run-local-pdm format-all` (pass)
    - `pdm run run-local-pdm lint-fix` (pass)
    - `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 142 source files`)
    - `pdm run run-local-pdm coverage-gate` (pass: `347 passed, 5 skipped`; coverage `94.94%`)
    - targeted T11 test matrix (pass: `17 passed`)
    - targeted T12 test matrix (pass: `37 passed, 3 skipped`)
    - `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
    - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=104 rules=9`)
    - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
  - Hardened async-push planning/docs for slices `T02/T03/T13-T16` and validated contracts.
  - Completed async-push docs implementation slice for `T02` and `T03`:
    - ADR `0003` accepted and cross-linked to Story 15 + Tasks 54-58 (`T02` complete),
    - published normative async push contract doc:
      `docs/converters/multi_format_conversion_service_api_v2_async_push.md` (`T03` complete),
    - synchronized tracking order: Task 54 terminalized, Epic `T02/T03` checked, Story 15 moved to
      `in_progress`.
    - docs validators/index + ADR/contract grep checks pass.
  - Applied ruthless-review remediation on T03 contract:
    - added onboarding update/rotate/delete examples, added signature/timestamp/replay error codes,
      normalized async KPI target to `100%` within first 3 attempts across epic/story/ADR/contract,
      and defined explicit auth capability + rate-limit contract (`429 rate_limited` + `Retry-After`)
      for SSE and webhook onboarding surfaces.
  - Completed Task 55 (`T13`) event/SSE implementation slice:
    - added lifecycle event persistence (`event_id`, `sequence`, replay cursor) and v2 SSE stream route
      with deterministic `410 cursor_expired`,
    - updated adapter non-GPU E2E lane and passed full quality + coverage + docs validators,
    - synchronized status/checkoff: Task 55 `completed`, Epic `T13` checked.

- 2026-02-18:

  - Epic 04 delivered service API v2 multi-format runtime and CLI remote-only pivot
    for non-PDF->MD routes.
  - Follow-up hardening tasks 40-42 completed (tests, zip-hardening, cancellation CAS).

## Next Actions

- Execute async-push production slice in epic listed order:
  - `docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md`
  - `docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md`
  - `docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md`
