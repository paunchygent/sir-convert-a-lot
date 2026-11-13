---
type: task
id: TASK-SIRCON-06-03-01
title: Preserve local operator tunnel lane for GPU-backed conversions
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
story: ST-SIRCON-06-03
task_kind: story
acceptance_criteria:
- '- [ ] Local operator conversion remains possible without public direct API exposure.'
- '- [ ] Heavy/GPU-dependent work can still be offloaded to Hemma.'
- '- [ ] The lane is documented as internal/operator-only.'
retired_ids:
- task-261-preserve-local-operator-tunnel-lane-for-gpu-backed-conversions
---
## Context

Source record: docs/backlog/tasks/task-261-preserve-local-operator-tunnel-lane-for-gpu-backed-conversions.md

### Objective

> Preserve the sanctioned local-to-Hemma operator lane for heavy GPU-backed
> conversion work after public product traffic moves behind HuleEdu Gateway.

## Decision And Assumption Ledger

## Story Contract Slice

### PR Scope

> - Keep or revise the documented SSH tunnel/wrapper access path.
> - Ensure local CLI usage can target the tunneled service with explicit operator
>   credentials.
> - Prove GPU-backed conversion and readiness through the local lane.
> - Update runbook guidance so local/operator, internal service, and public
>   Gateway lanes are not conflated.

## Contract Inputs

## Plan

## Implementation Steps

## Proof

### Deliverables

> - [ ] Runbook update for local operator lane.
> - [ ] Local CLI/tunnel proof artifact.
> - [ ] Credential handling guidance that avoids persisting secrets.

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review
