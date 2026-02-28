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
  - Updated async push planning docs to require adapter non-GPU E2E updates in the same PR as push
    logic changes:
    - `docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md`
    - `docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md`
    - `docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md`
  - Rewrote `review-01-brutal-review-service-api-v2-multi-format-pivot` as the active code-review
    authority, including mandatory v2-only, no-deprecation execution constraints.
  - Created Epic 05 and linked stories/tasks for prototype-to-production execution:
    - Epic:
      - `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md`
    - Stories:
      - `docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md`
      - `docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md`
      - `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md`
      - `docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md`
    - Tasks:
      - `docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md`
      - `docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md`
      - `docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md`
      - `docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md`
      - `docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md`
      - `docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md`
      - `docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md`
      - `docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md`
      - `docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md`
  - Added the next Epic 05 production-integration slice for async push channels on v2:
    - Story:
      - `docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md`
    - ADR:
      - `docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md`
    - Tasks:
      - `docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md`
      - `docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md`
      - `docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md`
      - `docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md`
      - `docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md`
      - `docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md`
      - `docs/backlog/tasks/task-59-enforce-90-percent-test-coverage-gate-for-conversion-core.md`

- 2026-02-18:

  - Epic 04 delivered service API v2 multi-format runtime and CLI remote-only pivot
    for non-PDF->MD routes.
  - Follow-up hardening tasks 40-42 completed (contract tests, resources zip hardening,
    cancellation CAS and module splits).

## Next Actions

- Proceed in epic listed order for Story 13 and Story 11 scope:
  - `docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md`
  - `docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md`
- Complete legacy/runtime cleanup after markdown/template pathways:
  - `docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md`
  - `docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md`
- Execute async-push production slice after above sequencing:
  - `docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md`
  - `docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md`
  - `docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md`
  - `docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md`
  - `docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md`
  - `docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md`
