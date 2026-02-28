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
labels:
  - session-log
  - active-work
---

## Context

Active focus has shifted to Epic 05: a prototype-to-production hardening track that enforces a
**v2-only conversion architecture** with explicit Markdown ingress routes and template-governed DOCX
outputs.

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

  - Rebased the active planning context from Epic 04 coexistence assumptions to Epic 05 clean-break
    requirements from the latest brutal review directive.
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

- 2026-02-18:

  - Epic 04 delivered service API v2 multi-format runtime and CLI remote-only pivot
    for non-PDF->MD routes.
  - Follow-up hardening tasks 40-42 completed (contract tests, resources zip hardening,
    cancellation CAS and module splits).

## Next Actions

- Start Story 14 implementation and remove v1 conversion routes in a single migration slice:
  - `docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md`
- Lock the unified v2 route/manifest contract before downstream integrations:
  - `docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md`
- Design and implement template catalog + Markdown ingress routes for GUI consumers:
  - `docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md`
  - `docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md`
  - `docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md`
  - `docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md`
- Remove eval topology and stale documentation/code references:
  - `docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md`
  - `docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md`
- After Story 14 + Task 45/50/51 stabilization, execute async push slice for production readiness:
  - `docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md`
  - `docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md`
  - `docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md`
  - `docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md`
  - `docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md`
  - `docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md`
