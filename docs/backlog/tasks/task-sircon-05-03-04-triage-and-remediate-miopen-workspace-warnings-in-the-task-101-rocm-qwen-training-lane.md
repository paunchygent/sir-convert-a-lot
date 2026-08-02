---
type: task
id: TASK-SIRCON-05-03-04
title: Triage and remediate MIOpen workspace warnings in the Task 101 ROCm Qwen training
  lane
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
story: ST-SIRCON-05-03
task_kind: story
acceptance_criteria:
- "[ ] The task answers, with evidence, whether the MIOpen warnings materially\n \
  \ block the saturation target after the earlier pipeline fixes."
- "[ ] If the warnings do matter, one remediation is implemented or at least\n  bounded\
  \ tightly enough that a final follow-on can be scoped precisely."
- "[ ] If the warnings do not matter much, the report and logs say so clearly\n  instead\
  \ of leaving the lane in ambiguity."
retired_ids:
- task-165-triage-and-remediate-miopen-workspace-warnings-in-the-task-101-rocm-qwen-training-lane
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

Use bounded profiler evidence to determine whether the persistent MIOpen
workspace warnings in the Task 101 ROCm lane are merely noisy logs or an
actual throughput limiter, and remediate them if they materially block the
story’s saturation target.

### Why This Exists

The live `2026-03-13` run repeatedly emitted warnings like:

- `MIOpen(HIP): Warning [IsEnoughWorkspace] ... Solver <GemmFwdRest> ...`

Those warnings are clearly present, but the current evidence does not yet prove
whether they materially matter relative to the much larger starvation issues.

### PR Scope

- Reproduce the warning pattern under a bounded profiling window after the
  earlier throughput tasks land.
- Correlate warning-heavy windows with ROCm and PyTorch profiler evidence.
- Evaluate whether configuration, workspace, or backend-selection changes can
  remove the warnings or reduce their performance impact.
- If the warnings are mostly harmless after the starvation fixes, document that
  explicitly and keep them from dominating the normal training logs.

### Non-Goals

- Do not use this task to excuse skipping the much more obvious dataloader and
  checkpoint-I/O work.
- Do not claim that warning removal alone will guarantee `>= 90%` GPU busy.

### Deliverables

- [ ] Bounded profiler evidence for one warning-heavy Task 101 window.
- [ ] One explicit conclusion on whether the warnings are a real throughput
  blocker.
- [ ] If needed, one remediation for the warning source or log-noise posture.

### Acceptance Criteria

- [ ] The task answers, with evidence, whether the MIOpen warnings materially
  block the saturation target after the earlier pipeline fixes.
- [ ] If the warnings do matter, one remediation is implemented or at least
  bounded tightly enough that a final follow-on can be scoped precisely.
- [ ] If the warnings do not matter much, the report and logs say so clearly
  instead of leaving the lane in ambiguity.

### Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Bounded Hemma profiler evidence is written under `build/verification/`.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
