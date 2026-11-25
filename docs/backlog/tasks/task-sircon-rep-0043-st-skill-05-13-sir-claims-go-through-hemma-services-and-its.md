---
type: task
id: TASK-SIRCON-REP-0043
title: 'ST-SKILL-05-13: Sir claims go through hemma-services and its own claim controller and GPU inventory are deleted'
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-11-24'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: agent-orchestrator
  decided_at: '2026-11-25T00:52:56+00:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Whole-task review changes_requested with four medium findings (F1 retired-edge precondition, F2 dead root-worker path, F3 oversized adapter tests, F4 fake claim pairings) repaired in a796499 with focused tests passing. D-level dependency met: skill-repository runtime 0.11.466 ships hemma-services claim and redeploy. Live Sir production activation stays a separate operator step.'
task_kind: repository
acceptance_criteria:
  - Sir's production start and redeploy claim through hemma-services with the same 0, 3 and 1 exit handling, and Sir no longer contains a claim controller or GPU inventory; the workload declarations and adapters stay.
backlog_document_profile: contract-derived
---

## Implementation Contract

Story ST-SKILL-05-13 T4 (skill-repository TASK-SKILL-05-13-12 plan L08 and
L09, Olof 24 Nov 2026): one claim controller and one GPU inventory, owned
by skill-repository. Sir keeps the `sir_workload_declarations` publisher
and its adapters (`ProductionWorkloadAdapter`,
`ContainerWorkloadAdapter`), which skill-repository calls through the
product worker; its own claim controller and GPU inventory are deleted.

1. `scripts/devops/prod-claim-start.sh:29` runs `hemma-services claim sir-production`, and `scripts/devops/prod-claim-redeploy.sh:29` runs
   `hemma-services redeploy sir-production` (the operator wrapper
   `/home/paunchygent/.local/bin/hemma-services`), instead of
   `pdm run hemma-workload start|redeploy sir-production <uuid>`. Exit codes
   pass through as today: 0 succeeded, 3 queued, 1 otherwise.
2. `scripts/sir_convert_a_lot/devops/hemma_deploy_and_verify.py:242-288`
   keeps reading the last stdout line's `outcome`, `target_identity`,
   `transaction_id`, `reason`; the JSON shape is unchanged.
3. Delete the controller wiring in
   `scripts/sir_convert_a_lot/devops/hemma_workload.py:438-465`,
   `SirGpuInventory` (`hemma_workload_inventory.py`), the claim CLI
   `hemma_workload_cli.py` and its `hemma-workload` entry in
   `pyproject.toml:338`, with anything only they use.
4. Tests: the claim script and deploy-and-verify tests fake `hemma-services`;
   the controller, CLI and inventory tests are deleted.
5. `AGENTS.md:22-25` and the service runbook lines 136 and 148-160 name
   `hemma-services claim|redeploy|release sir-production`.

## Contract Inputs

- skill-repository TASK-SKILL-05-13-12: `hemma-services claim|redeploy <identity>` print one JSON line with `outcome`, `reason`,
  `target_identity`, `transaction_id` and exit 0, 3 or 1.
- Discovery of the Sir claim callers (24 Nov 2026) above.

## Core Vertical And Performance

`pdm run prod-start` and `prod-recreate` claim through `hemma-services`. No
performance concern. Sir is hibernated; no live run is required.

## Validation

- `pdm run pytest` on the changed Sir tests
  (`tests/sir_convert_a_lot/operations/test_prod_claim_start.py`,
  `test_hemma_deploy_and_verify.py`, the declarations and adapter tests);
  `bash -n` on changed scripts; ruff and mypy on changed Python.

The whole-task review returned changes_requested with four medium findings: F1 retired-edge precondition, F2 dead root-worker path, F3 oversized adapter tests and F4 fake claim pairings. Commit a796499 repaired all four, and the focused tests pass. The dependency in D02 is met: skill-repository runtime 0.11.466 ships `hemma-services claim` and `redeploy`. Live Sir production activation stays a separate operator step.

## Stop Conditions

- A Sir caller needs a claim verb `hemma-services` does not offer.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Sir claims go through `hemma-services`; Sir keeps the declaration publisher and adapters and deletes its claim controller, claim CLI and GPU inventory (skill-repository TASK-SKILL-05-13-12 plan L08, L09; Olof, 24 Nov 2026). |
| D02 | This task lands after the skill-repository runtime release that ships `hemma-services redeploy` and after HuleEdu TASK-HULE-REP-0209.                                                                                           |
