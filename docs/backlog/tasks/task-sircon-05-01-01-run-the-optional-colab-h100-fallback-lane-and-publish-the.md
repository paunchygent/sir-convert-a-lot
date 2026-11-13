---
type: task
id: TASK-SIRCON-05-01-01
title: Run the optional Colab H100 fallback lane and publish the Swedish Qwen3-TTS
  comparison
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
story: ST-SIRCON-05-01
task_kind: story
acceptance_criteria:
- The task records the exact dataset slice and checkpoint strategy used on Colab.
- The task compares results against the Hemma pilot instead of publishing a standalone
  notebook-only result.
- The task records the concrete Hemma limitation that justified using Colab.
- The task records whether the Colab lane is materially better for the larger Swedish
  run.
retired_ids:
- task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Run the optional Colab H100 fallback Swedish Qwen lane only if Hemma proves
insufficient on stability, resume robustness, or unacceptable wall time, and
publish the comparison against the Hemma lane.

### PR Scope

- Reuse the same curated Swedish data and manifest policy from Tasks 102 and
  103\.
- Define checkpoint cadence and evidence export for Colab session limits.
- Compare Colab H100 against Hemma on:
  - runtime throughput,
  - checkpoint behavior,
  - operational friction,
  - qualitative Swedish output.
- Record the concrete trigger that justified leaving Hemma for this run.

### Deliverables

- [ ] One Colab H100 run report.
- [ ] One Hemma-versus-Colab comparison summary.
- [ ] Updated runbook guidance for when to use Hemma and when to use Colab.

### Acceptance Criteria

- [ ] The task records the exact dataset slice and checkpoint strategy used on
  Colab.
- [ ] The task compares results against the Hemma pilot instead of publishing a
  standalone notebook-only result.
- [ ] The task records the concrete Hemma limitation that justified using
  Colab.
- [ ] The task records whether the Colab lane is materially better for the
  larger Swedish run.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
