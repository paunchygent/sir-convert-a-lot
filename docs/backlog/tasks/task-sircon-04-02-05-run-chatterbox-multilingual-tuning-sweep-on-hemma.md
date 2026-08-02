---
type: task
id: TASK-SIRCON-04-02-05
title: Run Chatterbox multilingual tuning sweep on Hemma
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
story: ST-SIRCON-04-02
task_kind: story
acceptance_criteria:
- 'The sweep uses only repo-supported Chatterbox knobs: - `cfg_weight` - `exaggeration`'
- The sweep uses one fixed Swedish-only probe text across the same-language comparison
  set.
- The sweep uses one fixed approved teacher reference clip across the same-language
  comparison set.
- 'The sweep runs these value combinations because they are the values explicitly
  documented in the runbook: - `exaggeration` in `{0.5, 0.7}` - `cfg_weight` in `{0.5,
  0.3, 0.0}`'
- 'The conservative-first execution order is preserved: - `(0.5, 0.5)` - `(0.5, 0.3)`
  - `(0.7, 0.5)` - `(0.7, 0.3)` - `(0.5, 0.0)` - `(0.7, 0.0)`'
- 'Each lane writes its own deterministic evidence bundle containing at least: - `report.json`
  - `report.md` - `docker_logs.txt` - `artifacts/scenario-a-sv-ref-sv-out.wav`'
- Completed evidence bundles exist both on Hemma and in the local repo copy.
retired_ids:
- task-87-run-chatterbox-multilingual-tuning-sweep-on-hemma
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

Execute the first Chatterbox tuning sweep on Hemma using only the documented
knobs in the Chatterbox tuning runbook, with deterministic evidence for every
lane and a conservative-first execution order.

### PR Scope

- Add one committed Hemma sweep command surface for the Chatterbox tuning grid.
- Keep the sweep limited to the documented Chatterbox multilingual controls that
  the repo currently exposes:
  - `cfg_weight`
  - `exaggeration`
- Keep the same approved Swedish teacher reference clip across the sweep.
- Keep one Swedish-only probe text fixed across the sweep.
- Run the combinations in conservative-first order:
  - baseline before deviations
  - lower-guidance lanes before higher-exaggeration lanes
  - `cfg_weight=0` lanes last because they are less conservative for the
    same-language benchmark
- Persist one deterministic evidence bundle per lane under `build/verification/`.
- Mirror the completed Hemma evidence bundles back into the local repo copy.

### Deliverables

- [ ] Committed sweep runner for the Chatterbox tuning grid on Hemma.
- [ ] Deterministic evidence bundles for every documented lane in the sweep.
- [ ] Local copies of the remote Hemma evidence bundles under
  `build/verification/`.
- [ ] Updated Story 23 / Task 87 notes describing:
  - the exact combinations run,
  - the execution order,
  - the recorded runtime truth,
  - the qualitative comparison outcome.

### Acceptance Criteria

- [ ] The sweep uses only repo-supported Chatterbox knobs:
  - `cfg_weight`
  - `exaggeration`
- [ ] The sweep uses one fixed Swedish-only probe text across the same-language
  comparison set.
- [ ] The sweep uses one fixed approved teacher reference clip across the
  same-language comparison set.
- [ ] The sweep runs these value combinations because they are the values
  explicitly documented in the runbook:
  - `exaggeration` in `{0.5, 0.7}`
  - `cfg_weight` in `{0.5, 0.3, 0.0}`
- [ ] The conservative-first execution order is preserved:
  - `(0.5, 0.5)`
  - `(0.5, 0.3)`
  - `(0.7, 0.5)`
  - `(0.7, 0.3)`
  - `(0.5, 0.0)`
  - `(0.7, 0.0)`
- [ ] Each lane writes its own deterministic evidence bundle containing at
  least:
  - `report.json`
  - `report.md`
  - `docker_logs.txt`
  - `artifacts/scenario-a-sv-ref-sv-out.wav`
- [ ] Completed evidence bundles exist both on Hemma and in the local repo copy.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
