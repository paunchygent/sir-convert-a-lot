---
type: task
id: TASK-SIRCON-REP-0011
title: Demote experiment lanes behind an active command matrix
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
task_kind: repository
acceptance_criteria:
- '- [ ] No production conversion command is hidden or renamed without a compatibility
  decision.'
- '- [ ] Deprecated Qwen proof commands such as `qwen-fallback-proof` and `qwen-fallback-accumulation-proof`
  are no longer presented as active commands.'
- '- [ ] Active command docs agree with Rule 096''s status vocabulary or update that
  rule in the same governed diff.'
- '- [ ] Validation includes docs gates plus focused script/help checks for any PDM
  command names changed or demoted.'
- '- [ ] The close-out names any commands intentionally left flat and why.'
retired_ids:
- task-288-demote-experiment-lanes-behind-an-active-command-matrix
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

Make experiment and research lanes visibly subordinate to production conversion
surfaces by publishing one active command matrix and demoting legacy/deprecated
proof commands behind explicit legacy or docs-only surfaces.

### PR Scope

- Classify production conversion, OCR benchmark, Qwen, and sidecar commands as
  active, legacy-readonly, deprecated, or docs-only according to the active
  governance vocabulary.
- Keep Qwen and sidecar work available, but stop presenting old proof commands
  as peers of production conversion commands in the flat PDM script surface.
- Move legacy/deprecated proof commands behind a clearly named legacy namespace
  or a docs-only runbook section, preserving evidence and operator history.
- Align `historical rule 096-qwen-experiment-governance.md`, the Qwen runbook,
  `pyproject.toml` script exposure, and generated docs/index surfaces.
- Do not delete governed benchmark evidence, model artifacts, or historical
  reports as part of this task.

### Deliverables

- [ ] Active command matrix covering production conversion, DigiExam migration,
  OCR benchmark, Qwen, and sidecar lanes.
- [ ] Legacy/deprecated command list with explicit status and owner.
- [ ] PDM script exposure updated so deprecated proof commands are not shown as
  active production entrypoints.
- [ ] Runbook/rule/docs updates that point operators to the matrix instead of
  scattered flat script discovery.

### Acceptance Criteria

- [ ] No production conversion command is hidden or renamed without a
  compatibility decision.
- [ ] Deprecated Qwen proof commands such as `qwen-fallback-proof` and
  `qwen-fallback-accumulation-proof` are no longer presented as active commands.
- [ ] Active command docs agree with Rule 096's status vocabulary or update that
  rule in the same governed diff.
- [ ] Validation includes docs gates plus focused script/help checks for any
  PDM command names changed or demoted.
- [ ] The close-out names any commands intentionally left flat and why.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
