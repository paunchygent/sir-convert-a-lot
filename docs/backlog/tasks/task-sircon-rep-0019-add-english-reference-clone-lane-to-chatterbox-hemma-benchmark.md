---
type: task
id: TASK-SIRCON-REP-0019
title: Add English reference-clone lane to Chatterbox Hemma benchmark
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- A main English clone run can be executed without ad hoc scripts.
- Report JSON clearly records the probe language.
- Existing Swedish benchmark behavior remains the default path.
- Local tests cover the new probe-language option and reporting shape.
retired_ids:
- task-96-add-english-reference-clone-lane-to-chatterbox-hemma-benchmark
---

## Context

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Readiness

## Closeout

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Allow the canonical Task 86 Hemma Chatterbox benchmark surface to run an
English reference-clone lane as a first-class benchmark path, without
mislabelling the main clone output as Swedish in the evidence.

### PR Scope

- Add a probe-language control to the committed Task 86 benchmark CLI.
- Make the main clone artifact naming and report fields language-neutral.
- Keep the existing Swedish default behavior intact.
- Preserve the optional English-reference-to-Swedish cross-language lane.
- Add local tests for the new English main-clone path.

### Deliverables

- [ ] Task 86 benchmark supports `--probe-language en`.
- [ ] Task 86 report and markdown no longer hardcode the main clone lane as
  Swedish.
- [ ] One English reference-clone run can be executed through the canonical
  Hemma wrapper path.

### Acceptance Criteria

- [ ] A main English clone run can be executed without ad hoc scripts.
- [ ] Report JSON clearly records the probe language.
- [ ] Existing Swedish benchmark behavior remains the default path.
- [ ] Local tests cover the new probe-language option and reporting shape.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
