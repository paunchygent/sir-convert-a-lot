---
id: 006-migrate-canonical-converter-code-and-quality-gates
title: Migrate canonical converter code and quality gates
type: task
status: completed
priority: high
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/stories/story-04-01-standalone-repo-bootstrap-and-governance-setup.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
labels:
  - migration
  - quality-gates
---

## Objective

Ensure conversion service code and tests are fully aligned to standalone repository standards and
quality gates.

## PR Scope

- Converter module and test migration checks in this repo.
- Quality script and validation command readiness.

## Deliverables

- Canonical service modules and tests in this repo.
- Quality scripts (`format-all`, `lint-fix`, `typecheck-all`, `pytest-root`) wired in PDM.
- Verified no file exceeds 500 LoC in maintained surfaces.

## Acceptance Criteria

1. Full quality gate run passes on migrated converter surfaces.
1. No lint/type suppression shortcuts are introduced.
1. Contract/API docs match current implementation.

## Checklist

- [x] Code migration quality audit complete
- [x] Quality gates green
- [x] Task status moved to completed

## Implementation Notes (2026-02-11)

- Verified canonical conversion modules and tests are present under `scripts/sir_convert_a_lot/`
  and `tests/sir_convert_a_lot/`.
- Confirmed maintained module sizes remain under 500 LoC.
- Validation and quality evidence (local wrapper execution):
  - `pdm run run-local-pdm lint`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
