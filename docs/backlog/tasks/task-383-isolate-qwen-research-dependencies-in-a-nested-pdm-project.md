---
id: 'task-383-isolate-qwen-research-dependencies-in-a-nested-pdm-project'
title: 'Isolate Qwen research dependencies in a nested PDM project'
type: 'task'
status: 'ready'
priority: 'high'
created: '2026-07-21'
last_updated: '2026-07-21'
approval_note: 'User confirmed the reviewed Qwen isolation process and requested this local task on 2026-07-21.'
related:
  - docs/backlog/tasks/task-382-standardize-sir-convert-a-lot-python-runtime-on-3-12.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - dependencies
  - runtime
  - maintenance
---
PR-sized execution unit; may be linked to a story or standalone.

## Context

The root Sir Convert-a-Lot project currently declares the
`qwen-preprocessing` dependency group, while its current lock records only the
product groups and its reused `.venv` retains Qwen packages from an older
solution. This permits product NumPy and stale Qwen/Numba packages to coexist
even when the root lock is valid.

A clean Python 3.12 reproduction proved that the Qwen dependencies resolve,
install, import, and collect independently. The accepted shared policy at
`skill-repository/skills/local-devops/references/pdm-environment-isolation.md`
therefore requires Qwen to own a separate project, lock, environment, test
root, and named commands. TASK-382 retains ownership of the product Python 3.12
baseline and must not be widened.

## Decision And Assumption Ledger

| ID | Status | Decision | Basis | Source |
|---|---|---|---|---|
| QISO-001 | closed | Qwen research uses a nested PDM project with its own Python declaration, lock, `.venv`, test root, and commands. | A valid root lock did not prevent stale Qwen packages from contaminating the product environment. | User-approved isolation process, 2026-07-21 |
| QISO-002 | closed | Remove Qwen-TTS, Librosa, Numba, and Qwen-specific NumPy constraints from the product dependency solution. Do not add a repository-wide NumPy pin. | Compatibility constraints belong to the project that requires them. | User-approved isolation process, 2026-07-21 |
| QISO-003 | closed | Move Qwen-owned tests under `qwen/tests/`; root product test collection must not collect them. | The isolated project must own one explicit test root and product validation must not import research dependencies. | User-approved isolation process, 2026-07-21 |
| QISO-004 | closed | Preserve the current public `pdm run qwen-*` command names, but make them execute through the nested project environment. | Existing runbooks and operator workflows already use these names; only dependency ownership changes. | Current Qwen runbook; user-approved isolation process, 2026-07-21 |
| QISO-005 | closed | Prove the nested project first in a clean local Python 3.12 environment, then in the independent Linux/ROCm Qwen runtime on Hemma. | macOS dependency resolution does not establish Linux, ROCm, GPU, or container readiness. | User-approved isolation process, 2026-07-21 |
| QISO-006 | closed | TASK-382 must settle the root Python 3.12 lock before this task changes root dependency ownership. | Concurrent root-lock regeneration would make either task's proof ambiguous. | TASK-382 boundary; user-approved separate authority, 2026-07-21 |
| QISO-007 | closed | Do not change model behavior, training recipes, public conversion APIs, or sidecar route contracts. | This task repairs dependency and test isolation only. | User-approved isolation process, 2026-07-21 |

## Objective

Give Qwen research one independently reproducible PDM environment while keeping
the product environment free of Qwen-only dependencies and preserving the
current named Qwen operator commands.

## PR Scope

- Create `qwen/pyproject.toml`, `qwen/pdm.lock`, the ignored local
  `qwen/.venv`, and `qwen/tests/` as one Python 3.12-owned project boundary.
- Move the existing Qwen test tree out of root product collection and make the
  nested project its sole test owner.
- Move Qwen-only dependency declarations from the root project into the nested
  project and regenerate each affected lock through its owning PDM project.
- Preserve the canonical Qwen source modules under
  `scripts/sir_convert_a_lot/ml/qwen/` and
  `scripts/devops/qwen_finetuning_patches/` unless a bounded source move is
  required for truthful nested-project imports.
- Preserve the public `pdm run qwen-*` names while routing their execution to
  the nested environment through one documented repository-owned mechanism.
- Make the Qwen container/runtime consume the Qwen-owned dependency solution,
  then prove the existing smoke boundary on Hemma.
- Update the Qwen runbook and repo-local Qwen skill so installation, testing,
  and command execution use the nested project.

Out of scope:

- Model, dataset, optimizer, training-graph, or experiment changes.
- Public API, TTS sidecar route, deployment, or model-promotion changes.
- A separate Qwen repository, global NumPy pin, compatibility environment, or
  second dependency authority.
- TASK-382 implementation beyond consuming its settled product-lock baseline.

## Deliverables

- [ ] Nested `qwen/` PDM project with Python 3.12 metadata, independent lock,
      ignored `.venv`, and Qwen-only dependencies.
- [ ] Qwen-owned test root excluded from root product collection.
- [ ] Root product metadata and lock without Qwen-only dependencies or
      Qwen-specific NumPy constraints.
- [ ] Existing named Qwen commands execute through the nested environment and
      fail clearly when that environment is missing or stale.
- [ ] Qwen container/runtime and operator documentation consume the nested
      dependency boundary.
- [ ] Clean local and Linux/ROCm proof with retained commands and results.

## Acceptance Criteria

- [ ] Root product installation and test collection do not install or import
      Qwen-TTS, Librosa, Numba, or other Qwen-only dependencies.
- [ ] The nested lock installs cleanly under Python 3.12 and dependency
      validation reports no incompatible packages.
- [ ] The patched dataset import and complete Qwen test collection succeed from
      the nested environment without relying on the root `.venv`.
- [ ] Root product tests do not collect `qwen/tests/`; the explicit nested Qwen
      test command collects and runs that suite.
- [ ] Existing public `pdm run qwen-*` commands retain their meaning and use
      the nested environment rather than the product environment.
- [ ] The Hemma Linux/ROCm Qwen runtime resolves from the Qwen-owned dependency
      boundary and passes the governed `qwen-smoke` proof.
- [ ] No global NumPy pin, copied lock, fallback environment, or second active
      Qwen dependency declaration remains.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Implementation Plan

1. Confirm TASK-382 has settled the root Python 3.12 metadata and lock. Record
   the product and Qwen dependency inventories before changing either owner.
2. Verify the current supported PDM project-selection and synchronization
   commands through official documentation before writing command bindings.
3. Create the nested `qwen/` project and resolve its lock in a fresh Python
   3.12 environment. Keep Qwen-specific compatibility constraints local.
4. Move the Qwen tests into `qwen/tests/`, configure the nested test root, and
   prove root product collection excludes them.
5. Remove the root `qwen-preprocessing` dependency group and regenerate the
   root lock only from the settled TASK-382 baseline.
6. Route the existing named Qwen commands through one nested-project execution
   mechanism. Do not duplicate command implementations or silently fall back
   to the product environment.
7. Update the Qwen container inputs, runbook, and repo-local Qwen skill to use
   the nested project and lock.
8. Run clean local proof, then the real Hemma Linux/ROCm smoke. Record the exact
   environment, commands, results, and remaining limitations.

## Proof

- Selected proof mode: behavioral red/green for root product collection and
  public Qwen command environment selection; clean-environment contract proof
  for each lock; real-boundary Hemma proof for Linux/ROCm readiness.
- Applicability basis: this changes executable dependency, command, test, and
  runtime boundaries. The current mixed environment and failing broad Qwen
  collection provide truthful pre-change evidence.
- Pre-change evidence: root product collection reaches Qwen training imports,
  and the shared `.venv` combines root NumPy with stale Qwen/Numba packages.
- Required post-change evidence:
  - clean product installation and collection without Qwen dependencies;
  - clean nested Python 3.12 lock installation, dependency validation, patched
    dataset import, and complete Qwen suite;
  - public Qwen commands proving the nested interpreter and lock owner; and
  - real Hemma `pdm run run-hemma -- pdm run qwen-smoke` success through the
    accepted Qwen runtime boundary.
- Use code/search audit, not permanent absence-only tests, to prove the retired
  root Qwen dependency group and shared-environment route are gone.

## Validation

- Focused nested-project dependency, import, collection, and test commands.
- Focused root product collection and non-ML suite.
- `pdm lock --check` in each owning project.
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Applicable focused `pdm run pytest-root <path-or-nodeid>` commands.
- Governed Hemma `qwen-smoke` proof.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- TASK-382 has not settled the product Python 3.12 lock or its worktree changes
  cannot be separated from this task.
- Current PDM documentation does not support the selected nested-project
  command mechanism.
- Product tests still collect Qwen tests or either project can import packages
  retained only in the other project's environment.
- The implementation requires a global NumPy pin, copied lock, fallback to the
  root `.venv`, or two active Qwen dependency declarations.
- Preserving a public Qwen command would require changing its operator meaning
  rather than only its environment owner.
- Linux/ROCm resolution, import, or governed smoke proof fails. Do not claim
  runtime readiness or close the task.
- Work expands into model behavior, training recipes, public APIs, deployment,
  or long-running training.

## Readiness

- Decision ledger: QISO-001 through QISO-007 are closed; the user confirmed the
  reviewed isolation process and requested this task on 2026-07-21.
- Plan review: treated as complete by explicit user instruction that the
  process was already reviewed and approved.
- Permitted next step: begin implementation only after TASK-382 settles the
  root lock boundary.
- Status: `ready`.
