---
type: story
id: ST-SIRCON-07-02
title: Service source simplification and active surface truth cleanup before Exam.net runtime
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
epic: EPIC-SIRCON-07
links:
  decisions: []
acceptance_criteria:
- '- [x] Task 284 reconciles the active docs state without runtime code changes.'
- '- [x] Generic service job creation has a route policy/handler registry boundary before the Exam.net authoring route gains
  runtime behavior.'
- '- [x] Runtime engine, checkpoint executor, and CLI responsibilities are split into bounded modules with clear module docstrings
  and without behavior drift.'
- '- [ ] Legacy/deprecated experiment commands are visibly classified away from production conversion commands.'
- '- [ ] Task 200 scaffolds are either completed under their governed contract or retired with source, docs, and tests reconciled.'
- '- [ ] The onboarding map names the five service lanes, their status, entry points, owning docs, and command surfaces, and
  is generated or validator-checked.'
retired_ids:
- story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime
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

Create one governed cleanup tranche before more Exam.net authoring runtime work.
The tranche makes the active docs and command surfaces truthful, extracts the
route-specific service policy that would otherwise become a large `if`/`elif`
branch in the generic job endpoint, and then splits the largest runtime and CLI
hotspots into smaller discoverable modules.

The goal is not a cosmetic refactor. New developers should be able to identify
the production conversion core, DigiExam migration route, draft Exam.net
authoring route, OCR benchmark lane, and Qwen/sidecar research lane without
having to infer current truth from stale links, legacy proof commands, or
half-finished scaffolds.

### Scope

- Reconcile docs-state drift before touching runtime behavior: retired
  `.agents` references, retired `docs/backlog/current.md` links, Task 271
  status/checklist drift, conversion command-policy drift, and nonexistent
  facade documentation.
- Introduce a service API v2 route policy/handler registry keyed by
  `(source_format, output_format)` before implementing
  `examnet_artifact -> teacher_authoring_bundle` runtime behavior.
- Extract worker supervision and telemetry responsibilities from the v2 runtime
  engine, and extract chunk planning and checkpoint state from the checkpointed
  PDF executor.
- Split route submission, polling, and manifest construction responsibilities
  out of the CLI entrypoint.
- Demote Qwen, sidecar, and other experiment/proof lanes behind a visible
  active command matrix so legacy research does not read as production
  conversion surface.
- Finish or retire the Task 200 Qwen metadata scaffolds so governed
  `NotImplementedError` placeholders do not become permanent source-code
  furniture.
- Add a compact onboarding map for the five active service lanes and make the
  map generated or validator-checked.

### Task Sequence

1. Task 284 is the first cleanup PR and is docs-state only.
1. Task 285 must land before any service runtime implementation for
   `examnet_artifact -> teacher_authoring_bundle`.
1. Tasks 286 and 287 split runtime and CLI hotspots after the route boundary is
   explicit.
1. Tasks 288 and 289 clean experiment surfaces and finish or retire Task 200
   scaffolds without deleting preserved evidence.
1. Task 290 publishes the compact onboarding map after the active/legacy route
   and command classifications are truthful.

### Acceptance Criteria

- [x] Task 284 reconciles the active docs state without runtime code changes.
- [x] Generic service job creation has a route policy/handler registry boundary
  before the Exam.net authoring route gains runtime behavior.
- [x] Runtime engine, checkpoint executor, and CLI responsibilities are split
  into bounded modules with clear module docstrings and without behavior drift.
- [ ] Legacy/deprecated experiment commands are visibly classified away from
  production conversion commands.
- [ ] Task 200 scaffolds are either completed under their governed contract or
  retired with source, docs, and tests reconciled.
- [ ] The onboarding map names the five service lanes, their status, entry
  points, owning docs, and command surfaces, and is generated or
  validator-checked.

### Test Requirements

- [x] Docs-state changes pass `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.
- [x] Runtime/code tasks include focused unit or integration tests for preserved
  behavior before and after extraction.
- [x] Source-simplification tasks include module-size or source-map evidence so
  the tranche does not merely move complexity into new catch-all files.
- [ ] Command-surface and onboarding-map tasks include a validator or generated
  index check that fails on stale links or unclassified lanes.

### Done Definition

Story 46 is done when the repo has one truthful active surface for conversion
work, a route-handler boundary ready for Exam.net authoring runtime, no
permanent Task 200 metadata scaffolds, and a compact onboarding map that lets a
new developer find the current production and research lanes without spelunking
through stale docs or legacy command names.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
