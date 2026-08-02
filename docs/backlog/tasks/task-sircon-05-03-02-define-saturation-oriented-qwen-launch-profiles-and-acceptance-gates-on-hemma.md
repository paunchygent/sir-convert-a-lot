---
type: task
id: TASK-SIRCON-05-03-02
title: Define saturation-oriented Qwen launch profiles and acceptance gates on Hemma
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
- "[ ] A Task 101 launch can be classified unambiguously as smoke, profile,\n  pilot-long,\
  \ or convergence."
- "[ ] Each profile selects a coherent default policy instead of leaving the\n  operator\
  \ to assemble settings manually."
- "[ ] The story-level success gate is documented as `>= 90%` median GPU busy\n  over\
  \ a steady-state non-checkpoint window, not as a vague throughput claim."
retired_ids:
- task-163-define-saturation-oriented-task-101-qwen-launch-profiles-and-acceptance-gates-on-hemma
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

### Context

State the bounded implementation or proof need and the parent story behavior it
supports.

### Decision And Assumption Ledger

Every material implementation choice must already be closed by an accepted
source before scaffolding this task.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

### Story Contract Slice

Define the single-responsibility implementation or proof slice derived from the
parent story. Name the exact surfaces this task may change.

### Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this task.

### Plan

State the smallest implementation approach that satisfies the story slice and
acceptance criteria.

### Implementation Steps

List ordered steps small enough to execute and verify without inventing scope.

### Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

### Validation

List the exact focused and repository gates required before closeout and retain
concise results after they run.

### Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to planning.

### Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

### Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

### Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

### Implementation Review

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Replace today’s effectively unbounded ad hoc launch posture with explicit Task
101 run profiles and one documented saturation-oriented acceptance gate.

### Why This Exists

The live `2026-03-13` run used sentinel-like settings such as `num_epochs=1000`
and `max_steps=1000000` while also carrying a debug-friendly checkpoint
cadence. That makes it too easy to launch the wrong operational posture for the
wrong purpose.

### PR Scope

- Define explicit Task 101 launch profiles such as:
  - `smoke`
  - `profile`
  - `pilot-long`
  - `convergence`
- Bind each profile to an explicit default posture for:
  - checkpoint cadence
  - tracker behavior
  - monitor resolution
  - profiler enablement
  - duration / max-step expectations
- Document the canonical saturation gate:
  - `>= 90%` median GPU busy
  - `>= 10` contiguous steady-state non-checkpoint minutes
  - `<= 1.0` second monitor sampling
- Keep the CLI and runbook explicit about which profile is intended for which
  operational goal.

### Implementation Plan (Concrete)

Code changes:

- add `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_profiles.py`
  - canonical profile registry:
    - `smoke`
    - `profile`
    - `pilot-long`
    - `convergence`
  - profile-default resolution with explicit override precedence
- add `scripts/sir_convert_a_lot/devops/task101_qwen_saturation_gate.py`
  - contiguous non-checkpoint window evaluation
  - gate contract:
    - `>= 90%` median GPU busy
    - at least `10` contiguous minutes
    - monitor interval `<= 1.0s`
- update
  `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_resource_monitor.py`
  so the monitor summary exposes contiguous-window evidence fields
- update launcher/runtime/metadata surfaces to persist and render selected
  launch profile and gate result:
  - `run_task101_hemma_qwen_pilot.py`
  - `task101_qwen_pilot_runtime_contract.py`
  - `task101_qwen_pilot_runtime.py`
  - `task101_qwen_pilot_probe_reporting.py`
  - `task101_qwen_pilot_metadata.py`
- add governed gate runner:
  - `scripts/sir_convert_a_lot/devops/run_task163_hemma_task101_saturation_gate.py`

Test changes:

- add `tests/sir_convert_a_lot/test_task101_qwen_launch_profiles.py`
- add `tests/sir_convert_a_lot/test_task101_qwen_saturation_gate.py`
- extend `tests/sir_convert_a_lot/test_task101_qwen_resource_monitor.py`
  with contiguous-window gate assertions

Hemma evidence path:

- `build/verification/task-163-task101-saturation-gate/<run-id>/`

### Non-Goals

- Do not itself implement precomputed bundle mels.
- Do not itself resolve MIOpen warnings.
- Do not broaden this slice into a new evaluation protocol.

### Deliverables

- [ ] Explicit Task 101 launch profiles documented in code and runbook docs.
- [ ] One canonical saturation acceptance gate for Story 26.
- [ ] Launch metadata records the selected profile.
- [ ] Current story/reference/current-log docs point at the same acceptance
  target.

### Acceptance Criteria

- [ ] A Task 101 launch can be classified unambiguously as smoke, profile,
  pilot-long, or convergence.
- [ ] Each profile selects a coherent default policy instead of leaving the
  operator to assemble settings manually.
- [ ] The story-level success gate is documented as `>= 90%` median GPU busy
  over a steady-state non-checkpoint window, not as a vague throughput claim.

### Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
