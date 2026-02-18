---
id: task-34-service-v2-job-store-runtime-for-multi-format-artifacts
title: Service v2 job store + runtime for multi-format artifacts
type: task
status: in_progress
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/backlog/tasks/task-41-harden-v2-resources-zip-extraction-limits.md
  - docs/backlog/tasks/task-42-split-oversized-cli-and-v2-job-store-cancel-cas.md
labels:
  - v2
  - service
  - persistence
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the **service-side runtime primitives** needed to support API v2 multi-format conversion
jobs (md/html/pdf -> pdf/docx) with durable persistence and binary artifacts.

## PR Scope

- Job store:
  - v2 on-disk manifest schema for job status + diagnostics + artifact metadata.
  - durable storage for:
    - uploaded input bytes,
    - optional `resources.zip`,
    - optional `reference.docx`,
    - produced artifacts (`output.pdf` / `output.docx`).
- Runtime engine:
  - async job supervisor (threaded) with max worker governance.
  - idempotency tracking for `POST /v2/convert/jobs`.
  - cancel semantics and recovery behavior on restart.
- HTTP surfaces required by v2 contract:
  - job status,
  - structured result metadata,
  - binary artifact download,
  - cancel endpoint.

## Deliverables

- [ ] v2 job store implementation exists (`jobs_v2/*` persistence).
- [ ] v2 runtime engine implementation exists (async execution + recovery).
- [ ] v2 HTTP routes exist for job lifecycle + artifact download.
- [ ] Deterministic error envelope reuse across v1/v2 is preserved.

## Acceptance Criteria

- [ ] Local quality gates pass:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
- [ ] Follow-up hardening tasks are explicitly linked (zip-bomb limits, cancel CAS, SRP split).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
