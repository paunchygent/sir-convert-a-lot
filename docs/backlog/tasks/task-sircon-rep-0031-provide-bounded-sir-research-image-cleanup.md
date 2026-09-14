---
type: task
id: TASK-SIRCON-REP-0031
title: Provide bounded Sir research image cleanup
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-09-13'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - The shared Hemma cleanup runtime can plan and retire only eligible Sir-owned research images from exact repository facts while preserving active, current, pinned, and service-state assets.
backlog_document_profile: contract-derived
---

## Implementation Contract

Add one Sir-owned provider for exact cleanup of stopped, rebuildable Sir
research containers and images. The provider declares the production runtime,
GPU worker, STT, Qwen research, and dependency-image families from repository
facts and uses the existing shared plan/apply command boundary.

Successful one-shot containers remove themselves automatically. Failed
one-shot containers may remain briefly for diagnosis, then become eligible
unless an exact pin applies. Stopped rebuildable service containers are cleanup
assets, not research-run output producers.

## Contract Inputs

- Current Compose, bounded-startup, Qwen preprocessing/training, benchmark,
  and workload-switch declarations.
- Rebuild inputs in `Dockerfile`, `containers/`, the Qwen project, lockfiles,
  and repository-owned launchers.
- The existing shared Hemma cleanup runtime and provider command boundary.
- User approval to retire rebuildable stopped Sir runtime, STT, and Qwen
  research images while preserving durable data and active services.

## Core Vertical And Performance

The change directly adds Sir ownership facts to one provider and enables
automatic removal for successful one-shot containers.

## Validation

- Update the existing affected operations and research tests.
- Run the repository's affected operations/research checks and docs validation.

## Stop Conditions

- Stop if deletion can touch a running or unknown container, named volume,
  host cache, production data, or another repository's asset.
- Never force-remove assets or invoke broad container, image, volume, network,
  or system pruning.
- Do not add a free-space threshold, move model caches, prune BuildKit, or
  change research models or storage providers.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                      |
| --- | -------------------------------------------------------------------------------------------------------------------------- |
| D01 | Sir owns cleanup classification from its existing Compose, build, and launcher facts.                                      |
| D02 | The shared runtime admits multiple providers but does not infer Sir ownership.                                             |
| D03 | Named volumes, host model caches, persistent service data, and active dependency images remain outside cleanup.            |
| D04 | An optional pin uses the existing exact image-ID input; there is no pin registry.                                          |
| D05 | Successful one-shot research containers remove themselves; failed containers may be kept briefly and then become eligible. |
| D06 | Rebuildable stopped research images receive no implicit rollback retention.                                                |
| D07 | Reuse the existing cleanup plan/apply and test surfaces.                                                                   |
| D08 | The user approved this closed contract on 2026-09-13 and authorized implementation.                                        |
