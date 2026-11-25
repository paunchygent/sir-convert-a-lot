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
- Before the first Sir production start on a revision that includes
  TASK-SIRCON-07-04-01, the pre-start stored job-spec migration below has
  exited `0` against the production data volume.

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
- Deploy and live verify: `pdm run hemma-deploy-and-verify --expected-revision <sha> --lane host`
- GPU runtime verify from a client checkout:
  `pdm run run-local-pdm hemma-verify-gpu-runtime`. The verifier reads `SIR_CONVERT_A_LOT_V2_API_KEY` through `agent-secrets run --set sir-convert-a-lot-operator` on Hemma; the client side handles no key, and operators should not pass `--api-key` by hand.
  `hemma-deploy-and-verify` gates deploy success on revision/readiness parity,
  and metrics safety over the selected private lane. It consumes source already
  published by the parent; it does not push a branch. The legacy V2 conversion smoke
  is evidence only; `gpu_not_available` there is a conversion-worker finding,
  not a deploy failure.
  Use the wrapper from the local repo root. It is environment-aware: from a client machine it SSHes to Hemma; from the canonical Hemma Server checkout it runs directly after checking the hostname, repo root, and shared skill repository path. Set `SIR_CONVERT_A_LOT_FORCE_REMOTE_HEMMA=1` only when an operator deliberately needs the SSH path despite local Hemma detection. `run-hemma` never forwards local secrets; remote commands that need `SIR_CONVERT_A_LOT_V2_API_KEY` or `HF_TOKEN` read them through `agent-secrets run --set sir-convert-a-lot-operator` on Hemma.
  Direct production and ROCm helpers such as `prod-*` and `prod-deps-rocm-build` are Hemma Server-only. They fail before Docker or host env mutation when the session does not prove the canonical Hemma hostname, repo root, and shared skill repository.

## Pre-Start Stored Job-Spec Migration

TASK-SIRCON-07-04-01 removed the exam fields `conversion.targets`,
`conversion.artifact_language`, and `digiexam_migration_options` from the v2
job spec, and changed the request-fingerprint encoding. Job manifests written
before that revision fail strict validation in the current runtime: reading
the job returns HTTP 500, and so does every new admission while one such
manifest exists. This migration is a required step before any Sir production
start, including `hemma-services claim sir-production`, on a revision that
includes TASK-SIRCON-07-04-01. Run it once per data volume with both
`sir_convert_a_lot_prod` and `sir_convert_a_lot_gpu_worker` stopped.

The command rewrites each retained generic manifest in place and drops the
retired keys. It never deletes jobs, artifacts, or idempotency records, and it
never rewrites idempotency records: because the request inputs are not
persisted, a pre-retirement fingerprint cannot be recomputed, so the migration
neither waits for nor blocks on records still inside their replay window. Those
records expire on their normal schedule, and until then a same-key retry keeps
returning its changed-payload conflict. The default is a dry run; `--execute`
writes. The report is JSON, and the exit code is `0` when the data root is
current or was rewritten, `1` when a dry run found manifests to rewrite, and
`2` only when `unmigratable_jobs` is non-empty:

- `unmigratable_jobs` lists exam jobs or manifests that stay invalid. Stop and
  escalate; do not delete them to unblock the start.

The command runs inside the runtime image of the revision about to start,
`sir-convert-a-lot-runtime:<40-character HEAD>`, because older images do not
contain the migration module. Today only `prod-workload-start` builds that
image, and it also starts services, so no committed command yet builds it on
its own. Until one exists, stop here and escalate rather than starting services
to get the image. This procedure has not yet been run on Hemma, because
production has been offline since the retirement.

From the Hemma Server repository root, with the target revision checked out,
confirm the production data volume name (Compose prefixes it with the project
name), then run the dry run:

```bash
sudo docker volume ls --format '{{.Name}}' --filter name=sir-convert-a-lot-prod-data
sudo docker run --rm --entrypoint python \
  -v sir-convert-a-lot_sir-convert-a-lot-prod-data:/var/lib/sir-convert-a-lot/prod \
  "sir-convert-a-lot-runtime:$(git rev-parse HEAD)" \
  -m scripts.sir_convert_a_lot.interfaces.cli_retired_spec_fields_migration_v2 \
  --data-root /var/lib/sir-convert-a-lot/prod
```

Use the volume name the first command prints if it differs from
`sir-convert-a-lot_sir-convert-a-lot-prod-data`. It is a one-time pre-start
step, not a routine check.

If it exits `1`, rerun the same command with `--execute` appended. Then run
the dry run again: it must exit `0` with `"outcome": "clean"` before
`prod-start-bounded` may run. Rerunning `--execute` on a migrated volume
changes nothing. Keep the JSON reports as start evidence.

## Bounded Production Start

`pdm run prod-start` and `pdm run prod-start-bounded` are the Hemma Server-only operator start commands. Both end with `hemma-services claim sir-production`: production starts only through the shared claim, never directly through Compose. The claim prints one JSON line with `outcome`, `reason`, `target_identity` and `transaction_id` (`null` when a refusal precedes a transaction), and its exit code is the result — `0` on `succeeded`, `3` on `queued`, `1` on any other outcome — and the printed line carries the reason. Exit `3` with outcome `queued` means a conflicting held claim — a service, batch or interactive holder — or an earlier waiter blocks the start; the reason names the queue position and the holders or waiters it awaits, and the start happens when the queue advances. The recreate surfaces (`pdm run prod-recreate`, `pdm run hemma-prod-recreate`, and the deploy-and-verify recreate) admit or build `sir-convert-a-lot-runtime:<HEAD>`, create the two production containers with `up -d --no-start --no-build --no-deps --force-recreate`, and end with `hemma-services redeploy sir-production` instead of claim: redeploy starts the claim when unheld, replaces it when held, and is refused when suspended, so their exit code is also the claim's.

`pdm run prod-workload-start` is the claim adapter's internal start command, not an operator surface. It admits the current repository `HEAD` only with the exact, already-present hash-addressed ROCm dependency image and all three identity labels: dependency hash, recipe hash, and dependency-image hash. Before a selected service starts, the revision-tagged application image for that `HEAD` must prove its tag and image ID, OCI revision label, and dependency-hash label; injected runtime revision values are not provenance.

The command starts only `sir_convert_a_lot_prod` and `sir_convert_a_lot_gpu_worker`, separately, with `--no-deps --no-build`. It repairs a stale API by building and force-recreating only that API; it refuses a stale running worker rather than recreating it. Within 120 seconds, `/readyz` must prove exact revision, production profile, and data-root parity. GPU proof targets `sir_convert_a_lot_gpu_worker` and requires ROCm Torch, `/dev/kfd`, `/dev/dri`, and `rocm-smi` visibility without a live conversion or CPU fallback. The source and live restart policies for both selected services must finish as `restart=no`.

The command preserves the identities and states of excluded services and all volumes. It prints exactly one final `outcome=<value>` line: `succeeded`, `timed_out`, `dependency_unhealthy`, or `failed`; only `succeeded` exits zero.

Stop when dependency ensure or build, a broad recreate, an excluded service action, a volume or data mutation, provider or Task 05 work, or a live conversion would be required. The pre-start stored job-spec migration is the one sanctioned data mutation; it runs separately, before this command, and never inside it. When executing the controlled stale-image proof, stop if a genuine older labeled application image is unavailable. Do not add recovery work beyond the accepted API-only stale repair.

## Shared GPU Workload Switching

`hemma-services` in the shared skill repository owns the claim queue, the claim controller and the GPU inventory; Sir keeps only its workload declarations and adapters, which the skill repository's product worker loads. Real switching still requires separate explicit runtime authority. No Task05 live Hemma proof has run.

```text
hemma-services claim <target>
hemma-services redeploy <target>
hemma-services release <target>
hemma-services claims
```

| Target            | Exact container membership                               | Restart policy and operation                                                                                   |
| ----------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `sir-production`  | `sir_convert_a_lot_prod`, `sir_convert_a_lot_gpu_worker` | `restart=no`; start delegates to `prod-workload-start`, and stop names only the GPU worker then API.           |
| `sir-stt-sidecar` | `sir_convert_a_lot_stt_sidecar`                          | `restart=no`; starts and stops only this pre-existing container and waits for bounded Docker-health readiness. |

Both targets claim `gpu:amdgpu` and conflict with each other. Each of `claim`, `redeploy` and `release` prints one JSON line with `outcome`, `reason`, `target_identity` and `transaction_id`; `transaction_id` is `null` when a refusal precedes a transaction. `succeeded` exits `0`, `queued` exits `3`, and any other outcome exits `1`. A `queued` result's reason names the queue position and the holders or waiters it awaits. `hemma-services claims` shows the claim ledger for queue review. The public reserved workload is retired. An unknown GPU consumer causes a refusal, which the shared inventory reports through its own alert.

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
- Direct public lane: retired under TASK-SIRCON-06-01-04 and ADR-SIRCON-0014.
  Sir production remains stopped by user decision. Startup and GPU access still
  require separate authority.
  Do not document `127.0.0.1:8085` or `127.0.0.1:18085` as client access lanes. Port `8085` is container-internal validation only.
  Tunnel check:
  `ssh hemma -L 28085:127.0.0.1:28085 -N curl -fsS http://127.0.0.1:28085/healthz`

## API Key Handling

Deploy/live verification key handling:

1. Hemma-side verifiers read `SIR_CONVERT_A_LOT_V2_API_KEY` from the process environment injected by `agent-secrets run --set sir-convert-a-lot-operator`; the key never travels on a command line.
2. The implicit development key is rejected unless passed deliberately.
3. Never write API keys into reports, logs, or retained artifacts.

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
