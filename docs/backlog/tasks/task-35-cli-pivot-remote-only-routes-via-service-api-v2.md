---
id: task-35-cli-pivot-remote-only-routes-via-service-api-v2
title: 'CLI pivot: remote-only routes via service API v2'
type: task
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-28'
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

- [x] `convert-a-lot routes` reflects v2-backed multi-format routes.
- [x] CLI submits v2 jobs for `html/md/pdf -> pdf/docx` conversions and downloads artifacts.
- [x] `--css`, `--reference-docx`, and optional `--resources` are supported as v2 uploads.
- [x] Tests updated to match remote-only behavior.
- [x] CLI docs updated.

## Acceptance Criteria

- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q` passes without requiring local
  Pandoc/WeasyPrint binaries.
- [x] CLI produces deterministic manifests that include v2 `job_id` and final artifact paths.
- [x] v1 service contract remains unchanged and continues to support `pdf -> md` only.

## Validation Evidence

- [x] `pdm run run-local-pdm coverage-gate` (pass: `373 passed, 5 skipped`, coverage `95.26%`,
  2026-02-28).
- [x] `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`, 2026-02-28).
- [x] `pdm run run-local-pdm validate-docs` (pass: `Validated docs=106 rules=9`, 2026-02-28).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
