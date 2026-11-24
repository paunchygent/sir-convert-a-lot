---
type: task
id: TASK-SIRCON-REP-0042
title: "ST-SKILL-05-13: Sir workloads declare claim kinds, compose the host registry and start through the owner's claim"
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-11-24'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-11-24T19:35:05+00:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SIRCON-REP-0042#closeout; review task-sircon-rep-0042-code-review changes_requested, rereview changes_requested, rereview-2 approved at 36715d4 (retained root 01a20e6c-9c65-71a3-8d21-3e88a0688150, evidence/reviews/). Validation: 154 focused tests and changed-file mypy clean against engine 4beede6ad (later engine commit 164b34568 changes only boot resume, which Sir does not call). D06: it lands in the TASK-SKILL-05-13-11 window after the runtime release.'
task_kind: repository
acceptance_criteria:
  - sir-production and sir-stt-sidecar declare claim kind service, and sir_workload_registry composes the host-wide registry with owner sir, so RST and the other products are known consumers.
  - The STT sidecar declares restart no; prod-start and prod-start-bounded end with the owner's claim start; prod-recreate, hemma-prod-recreate and the deploy-and-verify recreate prepare the runtime:<HEAD> application image, recreate the two production services with up --no-start and end with the owner's claim redeploy; the production wrapper has no unclaimed start.
  - Both adapters provide start_existing, which starts existing containers only and fails when a container is absent or its image is stale; the hemma-workload CLI accepts exit 3 with outcome queued and has a redeploy verb.
  - The Sir root worker runs sibling product workers as the operator account, and Sir's inventory recognises every published host GPU container and the Qwen process.
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

7. **Review repairs (D07-D09, 24 Nov 2026).** The orchestrator admitted
   `hemma_workload_inventory.py`, `hemma_workload_constants.py`,
   `hemma_workload_container_adapter.py`, `bounded_production_startup.py`
   (image admission reused by recreate), `scripts/devops/compose-actions.sh`,
   `prod-compose.sh`, `prod-claim-start.sh` and `hemma_deploy_and_verify.py`
   status propagation into this task's boundary.

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

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Sir production and the STT sidecar are service claims (skill-repository T3 plan L08).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| D02 | Sir's registry composes the host-wide registry with owner `sir` (L29).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| D03 | The STT sidecar restarts `no`; Sir's start, recreate and deploy commands end with the owner's claim (L03, Olof; story D07).                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| D04 | Boot resume is start-only: `start_existing` never runs `up`, build or the secrets overlay, and fails on an absent or stale container (L18; story D12).                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| D05 | `queued` keeps the four keys and exits 3 (L31).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| D06 | This task lands in the TASK-SKILL-05-13-11 window after the runtime release (L28).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| D07 | The root worker runs sibling product workers as the invoking operator account with that account's PATH, like `_operator_pdm_command`; root never runs `pdm` in a user checkout (skill-repository T3 plan L40).                                                                                                                                                                                                                                                                                                                                                                           |
| D08 | Sir's inventory recognises every declared host GPU workload from HuleEdu's published container map and the Qwen service main PID; an unknown nonzero-VRAM PID still refuses (L41).                                                                                                                                                                                                                                                                                                                                                                                                       |
| D09 | Recreate prepares `runtime:<HEAD>` through the existing bounded-startup admission, passes its tag to Compose, recreates exactly the two production services with `up --no-start --no-build --no-deps --force-recreate` and ends with the owner's claim `redeploy` (start when unheld, replacement when held, refused when suspended); the production wrapper has no raw `start`; deploy-and-verify returns the claim's 3 or 1 and prints its reason; the sidecar's `start_existing` compares its image ID with the compose sidecar image and its status expects restart `no` (L39, L42). |

## Closeout

Implemented on `codex/task-sircon-rep-0042` in `a763834` (Sir workloads wired to the claim-ledger engine), `80655bf` (production started through the owner's claim) and `9b6935a` (contract terms D07–D09 from review rulings).

- Review `task-sircon-rep-0042-code-review` (`changes_requested`, 2026-11-24T18:47:46+00:00) returned blockers B1 (root worker cannot launch sibling declaration workers), B2 (recreate does not produce the application image the claimed start requires) and B3 (production Compose wrapper still starts without a claim), highs H1–H4 (sibling VRAM identity, recreate of claimed production, stale sidecar image and restart policy, deploy-and-verify converts queueing into failure) and mediums M1 (lifecycle test enforces the wrong claim rule) and M2 (stale ledger and queue wording in operator instructions). Repaired in `7589d31` (operator sibling workers, host GPU inventory, sidecar image check, redeploy verb) and `e9b2aad` (production recreate through image admission and the claim redeploy).
- First rereview (`changes_requested`, 2026-11-24T19:18:11+00:00) left H3 open (sidecar boot resolves a different image than Compose) and returned N1 (Sir refuses GPU claims because a CPU-only HuleEdu group is incomplete). Repaired in `36715d4`: the adapter resolves only the sidecar image through the production Compose configuration authority and compares IDs before `docker start`; inventory projects GPU identities from the composed registry and recognises only published group identities; the runbook explains that a conflicting holder or earlier waiter can queue the start.
- Second rereview (`approved`, 2026-11-24T19:35:05+00:00) resolved H3 and N1, accepted the M2 wording repair as parent-owned admission, and found no new findings. It admits this revision to the TASK-SKILL-05-13-11 coordinated landing subject to D06.

Validation: the four requested `pdm run pytest-root` files with the frozen engine source on `PYTHONPATH` — 85 passed (154 focused tests across the repair's test scope); changed-file mypy with that engine on `MYPYPATH` and `--follow-imports=silent` — no issues in the changed Sir Python files; `git diff --check e9b2aad..36715d4` passed; read-only Compose and Docker probes confirmed the sidecar image selection and restart policy. The engine source was skill-repository `4beede6ad`; the later engine commit `164b34568` changes only boot resume, which Sir does not call. Per D06 this task lands in the TASK-SKILL-05-13-11 window after the runtime release; no deploy, claim, start, stop or reboot ran here. |
