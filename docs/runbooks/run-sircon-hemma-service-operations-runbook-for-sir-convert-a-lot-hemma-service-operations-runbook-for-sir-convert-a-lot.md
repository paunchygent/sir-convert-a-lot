---
type: runbook
id: RUN-SIRCON-hemma-service-operations-runbook-for-sir-convert-a-lot
title: Hemma Service Operations Runbook for Sir Convert-a-Lot
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: active
summary: Hemma Service Operations Runbook for Sir Convert-a-Lot
system: hemma.hule.education
retired_ids:
  - RUN-hemma-service-ops
---

## Trigger

State the observable condition that starts this procedure and who may run it.

## Preconditions

- Required authority, system state, access, inputs, and safety checks.

## Steps

1. Give each action, command, expected intermediate result, and decision point in
   execution order.

## Expected Results

- Observable success state and the evidence that distinguishes it from partial
  or failed execution.

## Stop Conditions

- Exact condition that requires stopping, escalating, or returning to diagnosis.

## Rollback

State the safe recovery procedure and its boundary. If rollback is impossible,
state that explicitly and name the required escalation.

## Source Body Preservation

## Purpose

Operate Sir Convert-a-Lot on Hemma without duplicating HuleEdu or Skriptoteket runtime guidance.

## Host Map

- Sir Convert-a-Lot: `/home/paunchygent/apps/sir-convert-a-lot`
- HuleEdu: `/home/paunchygent/apps/huleedu`
- Skriptoteket: `/home/paunchygent/apps/skriptoteket`
- Shared edge infrastructure: `/home/paunchygent/infrastructure`
- Shared Postgres runs as shared container infrastructure, not as a Sir-local
  database.

## Command Surfaces

- Local wrapper: `pdm run run-local-pdm <script> [args]`
- Hemma wrapper: `pdm run run-hemma -- <command> [args]`
- Short shell probe: `pdm run run-hemma --shell "<command>"`
- Deploy and live verify: `pdm run hemma-deploy-and-verify --expected-revision <sha> --lane host --api-key <key>`
- GPU runtime verify from a client checkout:
  `pdm run run-local-pdm hemma-verify-gpu-runtime`. The local launcher reuses `SIR_CONVERT_A_LOT_V2_API_KEY` loaded by `run-local-pdm` and forwards only that key through the `run-hemma` verifier opt-in; operators should not rediscover or routinely pass `--api-key` by hand.
  `hemma-deploy-and-verify` gates deploy success on revision/readiness parity,
  metrics safety, and public-edge reserved state. The legacy V2 conversion smoke
  is evidence only; `gpu_not_available` there is a conversion-worker finding,
  not a deploy failure.
  Use the wrapper from the local repo root. It is environment-aware: from a client machine it SSHes to Hemma; from the canonical Hemma Server checkout it runs directly after checking the hostname, repo root, and shared skill repository path. Set `SIR_CONVERT_A_LOT_FORCE_REMOTE_HEMMA=1` only when an operator deliberately needs the SSH path despite local Hemma detection. `run-hemma` does not forward local secrets by default; the GPU verifier is the committed exception and opts in to forwarding only `SIR_CONVERT_A_LOT_V2_API_KEY` for its remote process.
  Direct production and ROCm helpers such as `prod-*`, `prod-deps-rocm-build`, and `hemma-sync-prod-env-mirror` are Hemma Server-only. They fail before Docker or host env mutation when the session does not prove the canonical Hemma hostname, repo root, and shared skill repository.

## Bounded Production Start

`pdm run prod-start-bounded` is Hemma Server-only. It admits the current repository `HEAD` only with the exact, already-present hash-addressed ROCm dependency image and all three identity labels: dependency hash, recipe hash, and dependency-image hash. Before a selected service starts, the revision-tagged application image for that `HEAD` must prove its tag and image ID, OCI revision label, and dependency-hash label; injected runtime revision values are not provenance.

The command starts only `sir_convert_a_lot_prod` and `sir_convert_a_lot_gpu_worker`, separately, with `--no-deps --no-build`. It repairs a stale API by building and force-recreating only that API; it refuses a stale running worker rather than recreating it. Within 120 seconds, `/readyz` must prove exact revision, production profile, and data-root parity. GPU proof targets `sir_convert_a_lot_gpu_worker` and requires ROCm Torch, `/dev/kfd`, `/dev/dri`, and `rocm-smi` visibility without a live conversion or CPU fallback. The source and live restart policies for both selected services must finish as `restart=no`.

The command preserves the identities and states of excluded services and all volumes. It prints exactly one final `outcome=<value>` line: `succeeded`, `timed_out`, `dependency_unhealthy`, or `failed`; only `succeeded` exits zero.

Stop when dependency ensure or build, a broad recreate, an excluded service action, a volume or data mutation, provider or Task 05 work, or a live conversion would be required. When executing the controlled stale-image proof, stop if a genuine older labeled application image is unavailable. Do not add recovery work beyond the accepted API-only stale repair.

## Shared GPU Workload Switching

`pdm run hemma-workload` is Hemma Server-only. The static consumer boundary accepts only these commands; real switching still requires separate explicit runtime authority. No Task05 live Hemma proof has run.

```text
pdm run hemma-workload start <target> <transaction-id>
pdm run hemma-workload stop <target> <transaction-id>
pdm run hemma-workload restore <target>
```

| Target                | Exact container membership                               | Restart policy and operation                                                                                               |
| --------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `sir-production`      | `sir_convert_a_lot_prod`, `sir_convert_a_lot_gpu_worker` | `restart=no`; start delegates to Task04 `prod-start-bounded`, and stop names only the GPU worker then API.                 |
| `sir-stt-sidecar`     | `sir_convert_a_lot_stt_sidecar`                          | `restart=unless-stopped`; starts and stops only this pre-existing container and waits for bounded Docker-health readiness. |
| `sir-qwen-answer-key` | `sir_convert_qwen_answer_key`                            | `restart=unless-stopped`; starts and stops only this pre-existing container and waits for bounded Docker-health readiness. |

All three targets claim `gpu:amdgpu` and are pairwise conflicts. After the Hemma Server guard, the public command crosses one fixed `sudo -n` Python worker boundary; that root worker rechecks the guard, owns the provider transaction, and uses `sudo -n docker` for direct container inspection and control. The provider renders the terminal result as JSON; only `succeeded` exits zero. It owns `/var/lib/hemma/workload-switch/active-receipt.json` and `/var/lib/hemma/workload-switch/active.lock`, and recovery restores only the prior Sir services recorded in that receipt. The reserved edge remains untouched, and unknown GPU consumers cause refusal.

## Dependency Image Cleanup

`scripts/devops/service-deps-image.sh` builds CPU and ROCm dependency images through explicit repositories:

- `sir-convert-a-lot-deps-cpu:<dependency-image-hash>` and `:local`
- `sir-convert-a-lot-deps-rocm:<dependency-image-hash>` and `:local`
  After a dependency-image build completes, the same script prunes superseded tags only for the repository it just built. It protects the current hash tag, the `local` tag, and any image ID used by a running container. This keeps storage pressure down without pruning unrelated Sir service images, sibling repo images, or BuildKit cache.
  Set `SIR_CONVERT_A_LOT_PRUNE_SUPERSEDED_DEPS_IMAGES=0` only for exceptional debugging when an operator deliberately wants to retain old dependency-image tags.

## Repo Placement Check

Before deploy, smoke, or destructive maintenance:
`pdm run run-hemma --shell 'find /home/paunchygent -maxdepth 4 -type d -name "sir-convert-a-lot" 2>/dev/null | sort'`
If the canonical repo is missing, repair the `~/apps` checkout before continuing. Do not run operational commands from ad hoc root-level copies.

## Client Access

Canonical lanes:

- Tunnel lane: `http://127.0.0.1:28085`
- Gateway/public lane: disabled until the Gateway cutover explicitly re-enables
  the intended public edge.
  Do not document `127.0.0.1:8085` or `127.0.0.1:18085` as client access lanes. Port `8085` is container-internal validation only.
  Tunnel check:
  `ssh hemma -L 28085:127.0.0.1:28085 -N curl -fsS http://127.0.0.1:28085/healthz`

## API Key Handling

Deploy/live verification key precedence:

1. `--api-key` 1. `SIR_CONVERT_A_LOT_API_KEY` 1. explicit failure
   The implicit development key is rejected unless passed deliberately. Never write API keys into reports, logs, or retained artifacts.

## Production Env Mirror

Use the committed mirror command:
`pdm run run-hemma -- pdm run hemma-sync-prod-env-mirror`
Do not hand-copy `.env` files between products or repos.

## Detached Work

Use attached remote commands only for fast probes and validation. Long jobs must survive local client disconnects through committed detached runners, named containers, `tmux`, or a supervised remote service.

## Minimal Service Triage

`pdm run run-hemma -- /bin/bash -lc 'sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"' pdm run run-hemma -- curl -fsS http://127.0.0.1:28085/healthz`

### Docker Compose Changes

- Use BuildKit and Docker Compose v2 through the repository's named wrappers.
- Inspect the rendered Compose configuration before changing service topology.
- Stop when the canonical Hemma checkout, target service, or expected environment
  cannot be proven.

### PostgreSQL Migration Changes

- Shared PostgreSQL is the canonical relational backend; select the exact database
  and command context before applying a migration.
- Create a follow-up migration instead of editing an applied migration.
- Prove schema changes with focused integration coverage and representative data.
- Stop before mutation when the database target, backup/recovery path, or migration
  order is uncertain.

### Docker Compose Changes

- Use BuildKit and Docker Compose v2 through the repository's named wrappers.
- Inspect the rendered Compose configuration before changing service topology.
- Stop when the canonical Hemma checkout, target service, or expected environment
  cannot be proven.

### PostgreSQL Migration Changes

- Shared PostgreSQL is the canonical relational backend; select the exact database
  and command context before applying a migration.
- Create a follow-up migration instead of editing an applied migration.
- Prove schema changes with focused integration coverage and representative data.
- Stop before mutation when the database target, backup/recovery path, or migration
  order is uncertain.
