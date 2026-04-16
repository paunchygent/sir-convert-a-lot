---
id: task-75-enforce-v2-only-client-imports-and-remove-re-export-facades
title: Enforce v2-only client imports and remove re-export facades
type: task
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-03-04'
related:
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - .codex/rules/030-conversion-workflows.md
  - scripts/sir_convert_a_lot/interfaces/http_client_v2.py
  - scripts/sir_convert_a_lot/interfaces/cli_app.py
  - pyproject.toml
labels:
  - clean-break
  - api-surface
  - refactor
  - v2
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Enforce the repository’s clean-break policy by removing legacy/re-export client entrypoints and
updating all in-repo callers to the explicit v2 client API surface with unambiguous naming.

## PR Scope

- Remove legacy client module `scripts/sir_convert_a_lot.interfaces.http_client` and any compatibility
  re-export facades (for example `scripts.sir_convert_a_lot.client` and `scripts.sir_convert_a_lot.cli`).
- Update all in-repo imports/callers to use:
  - `scripts.sir_convert_a_lot.interfaces.http_client_v2` (client transport + error types), and
  - `scripts.sir_convert_a_lot.interfaces.cli_app` (Typer app entrypoint).
- Update PDM script entrypoints and documentation references to the new canonical modules.
- Keep SRP: do not grow “main execution” modules; modularize instead.
- Enforce repo rule: any touched file must remain below 500 LoC.

## Deliverables

- [x] Legacy modules removed; no in-repo callers reference removed paths.
- [x] Canonical CLI entrypoints updated (`pdm run convert-a-lot` / `pdm run sir-convert-a-lot`).
- [x] Updated tests for v2-only imports and error types.
- [x] Documentation and rules updated to match the new canonical surfaces.

## Acceptance Criteria

- [x] `rg "interfaces\\.http_client(\\b|\\.)"` returns no in-repo call sites outside historical docs
  explicitly marked as such.
- [x] No compatibility re-export modules remain (no `__all__`-based facades that only import/export).
- [x] Quality gates pass:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - `pdm run pytest-root tests/sir_convert_a_lot`
- [x] Docs-as-code gates pass:
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

- Removed legacy/re-export modules (clean-break):
  - `scripts/sir_convert_a_lot/interfaces/http_client.py`
  - `scripts/sir_convert_a_lot/client.py`
  - `scripts/sir_convert_a_lot/cli.py`
  - `scripts/sir_convert_a_lot/runtime.py`
  - `scripts/sir_convert_a_lot/models.py`
  - `scripts/sir_convert_a_lot/infrastructure/webhook_subscriptions_v2.py`
- Updated CLI and callers to use canonical v2 modules:
  - CLI Typer app: `scripts/sir_convert_a_lot/interfaces/cli_app.py`
  - HTTP client: `scripts/sir_convert_a_lot/interfaces/http_client_v2.py` (`ClientErrorV2`, `SubmittedJobV2`)
- Updated service app factory call sites:
  - callers now import `create_app` from `scripts/sir_convert_a_lot/interfaces/http_api.py`
  - `scripts/sir_convert_a_lot/service.py` remains as the Uvicorn entrypoint exposing `app` only
- Split touched >500 LoC modules to remain under 500:
  - extracted webhook signing into `scripts/sir_convert_a_lot/infrastructure/webhook_signing_v2.py`
  - extracted Task 39 smoke helpers into `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions_helpers.py`
  - extracted Task 12 harness fakes into `tests/sir_convert_a_lot/scientific_corpus_harness_fakes.py`
- Updated internal adapter contract to v2:
  - added `docs/converters/internal_adapter_contract_v2.md`
  - deprecated `docs/converters/internal_adapter_contract_v1.md`

## Validation Evidence (2026-03-04)

- `pdm run format-all` (pass: `6 files reformatted`)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass: `Success: no issues found in 169 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot` (pass: `419 passed, 5 skipped`)
- `pdm run coverage-gate` (pass: coverage `95.33%`)
- `pdm run validate-tasks` (pass: `Validated 106 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=131 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
  (pass: wrote `/tmp/sir_tasks_index.md`)
