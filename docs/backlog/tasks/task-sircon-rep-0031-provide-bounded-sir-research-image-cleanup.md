---
type: task
id: TASK-SIRCON-REP-0031
title: Provide bounded Sir research image cleanup
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-09-13'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - The shared Hemma cleanup runtime can plan and retire only eligible Sir-owned research images from exact repository facts while preserving active, current, date-pinned, and service-state assets.
backlog_document_profile: contract-derived
---

## Implementation Contract

Add one Sir-owned provider for exact cleanup of stopped, rebuildable Sir
research containers and images. The provider declares the production runtime,
GPU worker, STT, Qwen research, and dependency-image families from repository
facts, emits an immutable plan, and applies only that unchanged plan through
exact container and image IDs.

Research launchers must write useful terminal output outside the container
under the shared `output/research-runs/<runner>/<run-id>/` contract and remove
successful containers automatically. Failed containers may remain only until
the external log/status path is proven; after that, the provider may retire
them unless an exact unexpired pin applies.

## Contract Inputs

- Current Compose, bounded-startup, Qwen preprocessing/training, benchmark,
  and workload-switch declarations.
- Rebuild inputs in `Dockerfile`, `containers/`, the Qwen project, lockfiles,
  and repository-owned launchers.
- The shared Hemma cleanup runtime's multi-provider/action contract.
- User approval to retire rebuildable stopped Sir runtime, STT, and Qwen
  research images while preserving durable data and active services.

## Core Vertical And Performance

The vertical is Sir launcher/build identity -> external run output -> exact
Docker inventory -> protected/candidate classification -> immutable plan ->
fresh-state verification -> exact apply result. Inventory is linear in Sir
assets and never scans named-volume or model-cache content.

## Validation

- Prove the provider recognizes only declared Sir image/container families.
- Prove running/current production, named-volume state, host caches, unknown
  assets, nonterminal run output, and unexpired exact pins remain protected.
- Prove eligible exited research containers and their subsequently
  unreferenced rebuildable images are planned in dependency order.
- Prove plan tampering or Docker/pin/output drift refuses apply.
- Prove active research launchers use the shared external run directory and
  successful one-shot containers remove themselves.
- Run the focused operations/research tests, typecheck, docs, skills, handoff,
  and diff checks through repository commands.
- Live installation and scheduled deletion remain a separately authorized
  shared-host deployment after every provider revision is published.

## Stop Conditions

- Stop if a target lacks exact Sir ownership or current rebuild inputs.
- Stop if deletion can touch a running container, named volume, host cache,
  production data, active dependency image, or another repository's asset.
- Stop if a failed run has no durable external log and terminal status.
- Never force-remove assets or invoke broad container, image, volume, network,
  or system pruning.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Sir owns the exact family registry, rebuild facts, and cleanup classification.                                                     |
| D02 | The shared runtime admits multiple providers but does not infer Sir ownership.                                                     |
| D03 | Research output uses `output/research-runs/<runner>/<run-id>/{run.log,status.json,artifacts/}`.                                    |
| D04 | Named volumes, host model caches, persistent service data, and active dependency images remain outside cleanup.                    |
| D05 | A retention pin contains one exact image ID and one `keep-until` date.                                                             |
| D06 | Successful one-shot research containers remove themselves; failed containers become eligible after durable terminal output exists. |
| D07 | Rebuildable stopped research images receive no implicit rollback retention.                                                        |
| D08 | The user approved this closed contract on 2026-09-13 and authorized implementation.                                                |
