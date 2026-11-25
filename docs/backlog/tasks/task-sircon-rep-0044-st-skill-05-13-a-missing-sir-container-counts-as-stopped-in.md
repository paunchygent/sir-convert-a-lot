---
type: task
id: TASK-SIRCON-REP-0044
title: 'ST-SKILL-05-13: a missing Sir container counts as stopped in the Hemma workload adapters'
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-11-25'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - With no sir_convert_a_lot_prod or sidecar container on the host, the Sir production and sidecar adapters report stopped for an expected stopped state and not running for an expected running state, and hemma-services release sir-production removes the stale holder row.
backlog_document_profile: contract-derived
---

## Implementation Contract

A Sir workload whose declared containers do not exist is stopped. Today
`_container_state` in
`scripts/sir_convert_a_lot/devops/hemma_workload_container_adapter.py:267-270`
raises `ValueError("cannot inspect declared container ...")` for a missing
container, and both adapter `status` methods
(`hemma_workload_container_adapter.py:119-146`,
`hemma_workload.py:174-205`) map it to `REFUSED`. With Sir production offline
by user decision and `sir_convert_a_lot_prod` removed, skill-repository's claim
engine can then never prove `sir-production` stopped: a refused claim keeps an
unprovable holder row, `hemma-services release sir-production` is refused, and
every judge claim on the same device fails while trying to stop it (ST-SKILL-05-13
landing proof, 25 Nov 2026).

1. `_container_state` returns the state `absent` with an empty restart policy
   when `docker inspect` exits non-zero and its stderr contains
   `no such object` or `no such container` (case-insensitive). Any other
   non-zero inspect still raises the existing `ValueError`.
2. `_state_category("absent")` returns `stopped`.
3. Both `status` methods check the restart policy only for containers that are
   not `absent`. Production compares categories as today, so absent with exited
   is stopped and absent with running stays the mixed-state refusal.
4. `ProductionWorkloadAdapter.start` and `ContainerWorkloadAdapter.start` are
   unchanged: a start with a missing container or image still fails.

## Contract Inputs

- Docker 29.10 on Hemma: `docker inspect --format '{{.State.Status}}' sir_convert_a_lot_prod` prints `error: no such object: sir_convert_a_lot_prod` and exits 1 (observed 25 Nov 2026).
- Skill-repository claim engine: `settlement.py:51-65,154-197` proves a stop
  with `status(STOPPED)`; an unproven stop keeps the holder row.

## Core Vertical And Performance

The adapter status reads that skill-repository calls through Sir's worker for
`sir-production` and the STT sidecar. No performance concern.

## Validation

- Focused tests in
  `tests/sir_convert_a_lot/operations/test_hemma_workload_production_adapter.py`
  and the sidecar adapter tests: both containers absent gives `SUCCEEDED` for
  expected stopped and `FAILED` for expected running; one absent and one
  exited gives stopped; one absent and one running gives the mixed-state
  refusal; a non-missing inspect error stays `REFUSED`; the sidecar absent case
  for both expected states.
- Live, after landing: `hemma-services release sir-production` in
  skill-repository removes the stale holder row, and a judge claim succeeds.

## Stop Conditions

- Sir production and STT stay offline by user decision: no start, claim or
  redeploy of them runs for this task.
- No change to skill-repository's claim engine and no ledger edit.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | A declared container that `docker inspect` reports as missing is stopped; every other inspect failure stays a refusal (orchestrator, 25 Nov 2026, ST-SKILL-05-13 landing proof). |
| D02 | Start behaviour, restart-policy rules for present containers, and the mixed-state refusal are unchanged.                                                                         |
