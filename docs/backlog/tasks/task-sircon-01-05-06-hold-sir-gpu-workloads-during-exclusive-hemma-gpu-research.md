---
type: task
id: TASK-SIRCON-01-05-06
title: Hold Sir GPU workloads during exclusive Hemma GPU research
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-30'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Sir production, GPU worker, STT sidecar, Qwen sidecars, and every other Sir GPU claimant remain stopped with live restart disabled for the complete CJ experiment.
story: ST-SIRCON-01-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Apply an operational hold to the existing Sir runtime. Stop Sir production and
every Sir GPU sidecar, set their live Docker restart policies to `no`, and make
the active hold prominent in the repository root `AGENTS.md` and Hemma skill.
Do not change Compose, bounded startup, runtime configuration, workload
declarations, or conversion behavior.

Skriptoteket owns its temporary provider routing separately. Re-enabling Sir
after the experiment uses the existing production contract and requires an
explicit user decision to lift this hold.

## Contract Inputs

- TASK-SIRCON-01-05-04 and TASK-SIRCON-01-05-05 as the unchanged normal
  production contracts.
- The user's 2026-08-30 decision to reserve Hemma's GPU exclusively for CJ.

## Core Vertical And Performance

No service implementation is required. The complete vertical is the stopped
runtime state, `restart=no` on the held containers, and loud operator routing
that keeps the hold active until the user lifts it.

## Validation

- Skill, Markdown, and repository-diff validation for the operator routing.
- Direct Hemma inspection that Sir production and GPU containers are stopped,
  use `restart=no`, and own no running GPU process.
- Direct observation that the held containers remain stopped while private Qwen
  is running.

## Stop Conditions

- Any held Sir container is running or has an automatic restart policy.
- Any Sir process claims GPU memory during the experiment.
- Re-enablement occurs without an explicit user decision to lift the hold.

## Decided Contract Terms

| ID  | Decided contract term                                                                         |
| --- | --------------------------------------------------------------------------------------------- |
| D01 | Existing Sir production and startup contracts remain unchanged.                               |
| D02 | Sir production and every Sir GPU sidecar remain stopped with `restart=no` for the experiment. |
| D03 | The hold is operational and temporary; normal re-enablement is decided later.                 |
| D04 | Skriptoteket routing and user-facing disablement are owned separately by the user.            |
