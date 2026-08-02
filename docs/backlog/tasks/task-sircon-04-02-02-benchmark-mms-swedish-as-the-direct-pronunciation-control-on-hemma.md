---
type: task
id: TASK-SIRCON-04-02-02
title: Benchmark MMS Swedish as the direct-pronunciation control on Hemma
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
story: ST-SIRCON-04-02
task_kind: story
acceptance_criteria:
- MMS Swedish sidecar boots on Hemma and synthesizes Swedish sample text deterministically.
- The sidecar exposes the normalized capability contract from ADR-0007 and explicitly
  reports cloning as unsupported in `/capabilities`.
- Evidence records runtime/dependency reality, cache/storage layout, and sample artifacts.
- Report explicitly states that lack of cloning keeps MMS Swedish out of primary backend
  consideration even if pronunciation quality is strong.
- The task produces a control baseline that helps compare OpenVoice V2 and XTTS-v2
  against direct Swedish narration quality.
retired_ids:
- task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma
---
## Context

Source record: docs/backlog/tasks/task-83-benchmark-mms-swedish-as-the-direct-pronunciation-control-on-hemma.md

### Objective

> Benchmark MMS Swedish as the direct-pronunciation control so we can separate Swedish language
> quality from cloning capability when evaluating backend candidates.

## Decision And Assumption Ledger

## Story Contract Slice

### PR Scope

> - Add a committed benchmark/smoke command surface for an MMS Swedish sidecar on Hemma.
> - Implement the benchmark against the reusable internal sidecar capability contract from
>   ADR-0007 (`/health`, `/capabilities`, `/voices`, `/synthesize`).
> - Exercise Swedish synthesis using the same probe text family as Tasks 81 and 82.
> - Capture runtime truth and audio artifacts for pronunciation/naturalness review.
> - Explicitly document that this task is a control baseline, not a candidate for default backend
>   selection when cloning remains a hard requirement.

## Contract Inputs

## Plan

## Implementation Steps

## Proof

### Deliverables

> - [ ] Committed `benchmark:task-83` command surface (or equivalent named wrapper).
> - [ ] Deterministic Hemma evidence under `build/verification/task-83-mms-swedish-hemma/`.
> - [ ] Swedish control sample artifacts.
> - [ ] Comparison notes that isolate language quality from cloning support.

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review
