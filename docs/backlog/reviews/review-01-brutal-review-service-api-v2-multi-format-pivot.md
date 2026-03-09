---
id: review-01-brutal-review-service-api-v2-multi-format-pivot
title: 'Brutal review: service API v2 multi-format pivot'
type: review
status: completed
priority: critical
created: '2026-02-18'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
  - docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md
  - docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md
  - docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - review
  - v2
  - clean-break
  - prototype-to-prod
---
Structured review artifact for implementation or readiness checks.

## Review Scope

- Surfaces reviewed:
  - `scripts/sir_convert_a_lot/interfaces/http_api.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_app.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_routes.py`
  - `scripts/sir_convert_a_lot/interfaces/http_client.py`
  - `scripts/sir_convert_a_lot/interfaces/http_client_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`
  - `scripts/sir_convert_a_lot/infrastructure/resources_zip.py`
  - `scripts/sir_convert_a_lot/README.md`
  - `docs/converters/*.md` (v1/v2 + CLI usage)
  - `docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md`
- Validation evidence captured:
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
  - `pdm run run-local-pdm convert-a-lot routes`
  - `pdm run run-local-pdm convert-a-lot convert --help`

## Findings

TBD.

## Decision

TBD.

## Response

Review accepted as a corrective baseline for Epic 05 cleanup and v2-only delivery hardening.

## Follow-up Actions

1. Complete the linked Epic 05 tasks that remove v1 drift, publish the final v2 route registry, and harden the DOCX template contract.

## Completion

Review closed and retained as the implementation baseline for the Epic 05 v2-only clean-break sequence.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
