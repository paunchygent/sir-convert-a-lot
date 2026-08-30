---
type: task
id: TASK-SIRCON-01-05-06
title: Run Sir production CPU-only during exclusive Hemma GPU research
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
- Normal Hemma production starts only a CPU-only Sir API and worker, while Sir GPU
  worker, STT sidecar, Qwen sidecars, and all other Sir GPU claims remain stopped
  for the complete CJ experiment.
story: ST-SIRCON-01-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Make sir_convert_a_lot_prod the complete production runtime for this
experiment: API plus its existing in-process supervisor, CPU-only execution,
no GPU device mappings, and no STT dependency. GPU worker, STT, Qwen,
training, and benchmark services remain opt-in offline services and stay
stopped for the full CJ experiment.

The bounded production command and shared workload declaration start and verify
only the API. Existing image provenance, revision readiness, persistent data,
and authentication remain unchanged.

## Contract Inputs

- TASK-SIRCON-01-05-04 and TASK-SIRCON-01-05-05 as historical GPU-rollout
  implementation facts, superseded for the duration of this experiment.
- The existing CPU-only acceleration policy and job supervisor.
- The user's 2026-08-30 decision to reserve Hemma's GPU exclusively for CJ.

## Core Vertical And Performance

Enable explicit CPU-only admission, enable the existing supervisor in the
production API, remove its STT dependency, and make every Sir GPU service
profile-only. Update the bounded starter and shared declaration to own only the
API and no GPU resource claim.

## Validation

- Focused runtime-config, acceleration-policy, Compose, bounded-startup, and
  workload-declaration tests.
- Real Hemma recreate from clean published main, exact readiness, empty Docker
  device list, empty queue, and one small CPU-only conversion.
- Direct observation that all Sir GPU containers remain stopped while private
  Qwen is running.

## Stop Conditions

- The production API gains a GPU device mapping or starts a sidecar dependency.
- CPU-only work cannot execute through the existing supervisor.
- A GPU-required request is accepted while the CPU-only profile is active.
- Starting private Qwen stops the CPU-only Sir API.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D01 | Production is one CPU-only API plus in-process supervisor. |
| D02 | GPU worker and STT remain offline and stopped for the experiment. |
| D03 | Sir production has no GPU claim and is not a private-Qwen conflict. |
| D04 | Skriptoteket routing and user-facing disablement are owned separately by the user. |
