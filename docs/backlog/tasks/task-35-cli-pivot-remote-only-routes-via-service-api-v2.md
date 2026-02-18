---
id: task-35-cli-pivot-remote-only-routes-via-service-api-v2
title: 'CLI pivot: remote-only routes via service API v2'
type: task
status: in_progress
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related: []
labels: []
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Pivot the CLI from local/hybrid Pandoc/WeasyPrint execution to **remote-only**
multi-format conversion via **service API v2**, keeping service API v1 locked
to `pdf -> md`.

## PR Scope

- Route registry:
  - classify all multi-format routes as service-backed (`v2`),
  - keep `pdf -> md` as service v1.
- CLI conversion behavior:
  - `html -> pdf` via v2 (with optional CSS resources),
  - `html -> docx` via v2,
  - `md -> pdf` via v2 (HTML intermediary in service),
  - `md -> docx` via v2 (HTML intermediary in service),
  - `pdf -> docx` via v2 (service pipeline: `pdf -> md -> html -> docx`).
- Client transport:
  - add a v2 HTTP client that supports submit/poll/download semantics.
- Tests:
  - replace local Pandoc/WeasyPrint route tests with v2-client stubs to avoid
    requiring laptop-local converter binaries.
- Docs:
  - update CLI guide and `docs/backlog/current.md` to reflect the pivot.

## Deliverables

- [ ] `convert-a-lot routes` reflects v2-backed multi-format routes.
- [ ] CLI submits v2 jobs for `html/md/pdf -> pdf/docx` conversions and downloads artifacts.
- [ ] `--css`, `--reference-docx`, and optional `--resources` are supported as v2 uploads.
- [ ] Tests updated to match remote-only behavior.
- [ ] CLI docs updated.

## Acceptance Criteria

- [ ] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q` passes without requiring local
  Pandoc/WeasyPrint binaries.
- [ ] CLI produces deterministic manifests that include v2 `job_id` and final artifact paths.
- [ ] v1 service contract remains unchanged and continues to support `pdf -> md` only.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
