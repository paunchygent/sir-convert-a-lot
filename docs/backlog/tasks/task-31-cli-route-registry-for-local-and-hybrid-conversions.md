---
id: task-31-cli-route-registry-for-local-and-hybrid-conversions
title: CLI route registry for local and hybrid conversions
type: task
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - cli
  - routing
  - manifest
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Introduce a typed, deterministic route registry and CLI routing layer that supports:

- local conversions (no service required),
- hybrid pipelines (service + local),
- and preserves the locked PDF-to-MD service v1 behavior and manifest semantics.

## PR Scope

- Add a route registry abstraction that can express:
  - `pdf -> md` (service v1)
  - `pdf -> docx` (hybrid)
  - `md -> html -> pdf` (local)
  - `md -> html -> docx` (local)
  - `html + css -> pdf` (local)
- Guardrails:
  - Do **not** expand the locked service v1 contract (keep `POST /v1/convert/jobs` PDF→MD only).
  - Do **not** change existing PDF→MD CLI defaults or manifest field shape.
  - Keep new local/hybrid route specs separate from the service `JobSpec` language.
- CLI changes:
  - allow `--to` targets beyond `md` (without expanding the service contract),
  - add optional `--from` override (extension inference remains default),
  - add `convert-a-lot routes` (or equivalent) to list supported routes/engines,
  - add `--dry-run` route selection output (deterministic/stable).
- Error/diagnostics:
  - deterministic error codes for unsupported routes and missing local dependencies
    (e.g., Pandoc/WeasyPrint not installed),
  - keep existing PDF-to-MD error envelope mapping unchanged.
- Tests:
  - route inference and validation unit tests,
  - `--dry-run` output golden tests.

## Implementation Notes

- Expected touchpoints:
  - CLI: `scripts/sir_convert_a_lot/interfaces/cli_app.py`
  - CLI contracts: `scripts/sir_convert_a_lot/application/contracts.py`
  - New routing module(s): keep SRP and add Google-style module docstrings.
- Suggested route status model:
  - registry returns `implemented=true|false` and a `pipeline_kind` (`service|local|hybrid`),
  - CLI may expose planned-but-not-yet-implemented routes as `route_not_implemented`.
- Determinism definition for this task:
  - deterministic route selection for a given invocation,
  - deterministic manifest entry ordering and error codes,
  - not bit-for-bit determinism of generated PDFs/DOCX.

## Deliverables

- [x] Route registry + routing implementation under `scripts/sir_convert_a_lot/` (typed).
- [x] CLI updated to use registry for route selection without changing the service v1 contract.
- [x] `convert-a-lot routes` and `--dry-run` UX implemented and documented.
- [x] Focused test coverage for route inference and deterministic error codes.
- [x] CLI docs updated for new routing concepts and critical pipeline set.

## Acceptance Criteria

- [x] `convert-a-lot convert <pdf> --to md` remains stable (same defaults, same manifest fields).
- [x] Critical pipeline set is discoverable via `convert-a-lot routes`.
- [x] `--dry-run` is deterministic and clearly reports the selected pipeline and executor(s).
- [x] Unsupported routes fail with deterministic, user-actionable error codes (no ambiguous stacktraces).
- [x] Tests pass for route inference, validation, and `--dry-run` behavior.

## Validation Evidence

- Local quality gates:
  - 2026-02-18:
    - `pdm run run-local-pdm format-all` (pass)
    - `pdm run run-local-pdm lint-fix` (pass)
    - `pdm run run-local-pdm typecheck-all` (pass)
    - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -q` (pass)
    - `pdm run run-local-pdm validate-tasks` (pass)
    - `pdm run run-local-pdm validate-docs` (pass)
    - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
