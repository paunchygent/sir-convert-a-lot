---
type: story
id: ST-SIRCON-05-04
title: Transition to Domain-Centric ML Pipeline Structure
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-05
links:
  decisions: []
acceptance_criteria:
- '- [ ] The `scripts/sir_convert_a_lot/devops/` directory no longer contains Qwen-related task files.'
- '- [ ] No filenames or public symbols in the ML domain contain "taskXXX" prefixes.'
- '- [ ] `pdm run qwen-train` and `pdm run qwen-preprocess` (or new equivalents) function identically to the old commands.'
- '- [ ] All unit tests pass with the new import structure.'
- '- [ ] Docker images build and run successfully using the new internal paths.'
retired_ids:
- story-27-transition-to-domain-centric-ml-pipeline-structure
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

Implementation slice with acceptance-driven scope.

### Objective

Replace the task-centric, fragmented directory structure of the Qwen ML pipeline
with a domain-centric architecture that separates infrastructure, preprocessing,
training, and CLI concerns into stable, SRP-aligned modules.

### Scope

- Establish `scripts/sir_convert_a_lot/ml/qwen/` as the canonical domain root.
- Move all `task100`, `task101`, `task103`, etc., logic into domain modules
  (e.g., `common/`, `preprocessing/`, `training/`).
- Remove all task-ID prefixes from filenames and internal symbols.
- Consolidate Hemma-specific storage and runtime logic into a shared `common/`
  package.
- Rebuild CLI entrypoints as thin wrappers under `scripts/sir_convert_a_lot/cli/ml/`.
- Update all internal imports, Dockerfiles, and documentation to reflect the
  clean-break structure.

Out of scope:

- changing runtime behavior or ML logic,
- adding new features,
- or maintaining backward-compatible shims/wrappers.

### Acceptance Criteria

- [ ] The `scripts/sir_convert_a_lot/devops/` directory no longer contains Qwen-related task files.
- [ ] No filenames or public symbols in the ML domain contain "taskXXX" prefixes.
- [ ] `pdm run qwen-train` and `pdm run qwen-preprocess` (or new equivalents) function identically to the old commands.
- [ ] All unit tests pass with the new import structure.
- [ ] Docker images build and run successfully using the new internal paths.

### Test Requirements

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`

### Done Definition

The repository reflects a modern, domain-driven structure for ML operations
where logic is discovered by function rather than by the chronological order
of implementation tasks.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
