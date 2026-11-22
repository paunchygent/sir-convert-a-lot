---
type: task
id: TASK-SIRCON-REP-0038
title: Cleanup of explicit Any, cast and type-ignore comments and the shared Pyrefly explicit-any producer
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-11-22'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - 'Given the repository''s tracked Python files, when `pyrefly check --error explicit-any --only explicit-any` runs over them with Pyrefly 1.4.1, then it reports no error, and rg finds no `cast(` call or `# type: ignore` comment outside an exception recorded in this task.'
  - 'Given the released repository-governance runtime with explicit-any as an error, when the settings sync has run and `pdm run typecheck` runs, then a Pyrefly producer checks the typecheck-includes and passes, and a disposable module with `def f(x: Any) -> None` makes it fail.'
backlog_document_profile: contract-derived
---

## Implementation Contract

0. This repository has no generated tooling settings block and no Pyrefly
   install. Before the cleanup, run the settings sync with the current
   released runtime so the block and the pinned Pyrefly 1.4.1 dependency are
   added, set typecheck-includes, and install through the repository's own
   dependency route.
1. Cleanup (before the runtime release). Every explicit `Any`, `cast(` and
   `# type: ignore` in tracked Python files is rewritten to fit
   skill-repository's typing reference
   (`skills/agent-roles/references/coding-principles-typing.md`) or removed:
   parsed JSON goes through the repository's single recursive `JsonValue`
   alias and is narrowed at the boundary; test doubles and fixtures take the
   real class, a Protocol or `object` (TASK-SKILL-REP-0591 DCT-09); inherited
   third-party signatures and boundary refusal tests carry a coded
   single-line `# pyrefly: ignore[...]` with a reason comment. The
   repository's existing `pdm run typecheck` keeps passing.
2. After the release that turns explicit-any on: run
   `repository-governance-bindings sync --project-file pyproject.toml`, set
   `typecheck-includes` under `[tool.repository-governance.tooling]` to the
   repository's Python source and test roots, and add a typecheck producer
   `pyrefly check --config pyproject.toml --only explicit-any`
   (TASK-SKILL-REP-0591 DCT-08). Other type checkers stay unchanged.

## Contract Inputs

Survey of 22 Nov 2026 for sir-convert-a-lot: typecheck runs mypy; no
Pyrefly; 0 `Any`, 8 `cast(`, 10 `# type: ignore`.

## Core Vertical And Performance

`pdm run typecheck` passes with a Pyrefly producer checking the repository's
typecheck-includes with explicit-any as an error; a new explicit `Any`
fails the gate while mypy keeps covering its existing scope.

## Validation

- A disposable module with `def f(x: Any) -> None` fails
  `pdm run typecheck` with an `explicit-any` error after the settings sync
  and producer change.
- `pdm run check` passes on the changed set.

## Stop Conditions

- A site that fits no exception in the typing reference goes to the
  TASK-SKILL-REP-0591 orchestrator for Olof's decision; no junior adds an
  ignore for it.
- Unit 2 waits for the runtime release of TASK-SKILL-REP-0591.

## Decided Contract Terms

| ID     | Decided contract term                                                                                                                                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DCT-01 | Every permitted ignore is a coded single-line Pyrefly ignore with a reason comment; bare `# type: ignore` and `cast` stay forbidden. (TASK-SKILL-REP-0591)                                                                          |
| DCT-02 | A governed repository whose typecheck does not run Pyrefly adds a typecheck producer `pyrefly check --config pyproject.toml --only explicit-any`; its other type checkers stay unchanged (Olof, 22 Nov 2026). (TASK-SKILL-REP-0591) |
| DCT-03 | A test double or fixture typed `Any` is rewritten to the real class, a Protocol, or `object`; the typing reference gains no test-double exception (Olof, 22 Nov 2026). (TASK-SKILL-REP-0591)                                        |
