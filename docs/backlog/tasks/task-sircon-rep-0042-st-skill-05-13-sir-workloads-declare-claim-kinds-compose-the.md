---
type: task
id: TASK-SIRCON-REP-0042
title: "ST-SKILL-05-13: Sir workloads declare claim kinds, compose the host registry and start through the owner's claim"
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-11-24'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - sir-production and sir-stt-sidecar declare claim kind service, and sir_workload_registry composes the host-wide registry with owner sir, so RST and the other products are known consumers.
  - The STT sidecar declares restart no; prod-start, prod-start-bounded, prod-recreate, hemma-prod-recreate and the deploy-and-verify recreate end by starting through the owner's claim (hemma-workload start), creating containers with up --no-start where they create or recreate.
  - Both adapters provide start_existing, which starts existing containers only and fails when a container is absent or its image is stale; the hemma-workload CLI accepts exit 3 with outcome queued.
backlog_document_profile: contract-derived
---

## Implementation Contract

Sir's part of skill-repository ST-SKILL-05-13 step 4 (T3). The engine change
is skill-repository TASK-SKILL-05-13-08; this task lands in its
TASK-SKILL-05-13-11 window, after the runtime release. Until then, tests
import the engine from the -08 worktree's `packages/repository_governance/src`
(`PYTHONPATH`).

1. **Kinds and registry (D01, D02).** In
   `scripts/sir_convert_a_lot/devops/hemma_workload.py`: `sir-production` and
   `sir-stt-sidecar` (`:291-308`) declare kind `service`;
   `sir_workload_registry` (`:282-312`) builds its registry with
   `repository_governance.hemma_workload.products.composed_declarations`
   (owner `sir`, its two declarations as the local tuple), like HuleEdu's
   `workload_registry`.
2. **STT sidecar policy (D03).** `compose.yaml`: `sir_convert_a_lot_stt_sidecar`
   `restart: unless-stopped` becomes `restart: "no"`.
3. **Start through the claim (D03).** The commands that start production end
   with `pdm run hemma-workload start sir-production <transaction-id>` instead
   of starting containers themselves:
   - `prod-start` and `prod-start-bounded`;
   - `prod-recreate` and `hemma-prod-recreate`: recreate with
     `docker compose -f compose.yaml -f compose.secrets.yaml up -d --no-start --no-build --no-deps --force-recreate <services>` (through the existing
     `agent-secrets` wrapper), then the claim start;
   - `hemma_deploy_and_verify.py` (`:214-228`) keeps calling `prod-recreate`,
     which now ends with the claim.
     Checked syntax: Docker Compose v5.8.0 `up --no-start` creates containers
     and starts none (`docker compose up --help`; ctx7 `/docker/compose`,
     `cmd/compose/up.go`). A `queued` or other non-succeeded claim result makes
     the command exit with the claim's code (3 queued, 1 otherwise) and print
     its reason.
4. **Start-existing (D04).** `ProductionWorkloadAdapter` and the sidecar
   container adapter implement `start_existing`: `sudo -n docker start` of the
   existing containers only; `failed` when a container is absent or its image
   differs from the application image (the checks in
   `bounded_production_startup.py:151-211`); never `up`, build or
   `compose.secrets.yaml`.
5. **CLI (D05).** `scripts/sir_convert_a_lot/devops/hemma_workload_cli.py`:
   `_worker_main` (`:180-202`) returns 3 for `queued`; `_public_main`
   (`:162-163`) accepts exit 3 with outcome `queued` (0 only with
   `succeeded`, 1 for other outcomes); the field set stays the four keys.
6. **Docs.** `docs/runbooks/run-sircon-hemma-service-operations-runbook-for-sir-convert-a-lot.md`
   (`:146-151`) and `AGENTS.md:23` state that production starts through the
   owner's claim and how a queued start reads.

## Contract Inputs

- skill-repository ST-SKILL-05-13 D06, D07, D10, D12; TASK-SKILL-05-13-08
  D02, D03, D12 and its `start_existing` operation.
- Sir's controller today builds only its own two declarations and treats RST
  as an unknown consumer (`hemma_workload_inventory.py:66-76`).

## Core Vertical And Performance

`pdm run prod-recreate` recreates the containers without starting them and
the claim starts them; after a reboot a held `sir-production` claim starts
with `docker start` only. No performance concern.

Units (one junior each): (a) steps 1, 4, 5; (b) steps 2, 3, 6.

## Validation

- `pdm run test tests/sir_convert_a_lot/operations/test_hemma_workload_cli.py tests/sir_convert_a_lot/operations/test_hemma_workload_declarations.py` plus focused tests for `start_existing` and the recreate-then-claim command, run against the -08 engine source.
- `docker compose -f compose.yaml config` shows the sidecar `restart: "no"` (read-only); lint and typecheck on changed files.

## Stop Conditions

- A start path would need the secrets overlay at boot.
- A change is needed in a Sir file outside the ones named here.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D01 | Sir production and the STT sidecar are service claims (skill-repository T3 plan L08).                                                                  |
| D02 | Sir's registry composes the host-wide registry with owner `sir` (L29).                                                                                 |
| D03 | The STT sidecar restarts `no`; Sir's start, recreate and deploy commands end with the owner's claim (L03, Olof; story D07).                            |
| D04 | Boot resume is start-only: `start_existing` never runs `up`, build or the secrets overlay, and fails on an absent or stale container (L18; story D12). |
| D05 | `queued` keeps the four keys and exits 3 (L31).                                                                                                        |
| D06 | This task lands in the TASK-SKILL-05-13-11 window after the runtime release (L28).                                                                     |
