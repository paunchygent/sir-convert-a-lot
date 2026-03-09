---
id: task-113-migrate-hemma-docker-storage-root-to-data-backed-disk
title: Move Hemma Docker bytes onto SSD scratch by bind-mounting the canonical snap root
type: task
status: active
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/tasks/task-112-move-qwen-hemma-generated-output-to-data-and-clean-root-disk.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - hemma
  - docker
  - storage
  - infrastructure
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Stop storing Hemma Docker daemon bytes on the root disk by moving the backing
data onto the SSD scratch tier while preserving Docker's canonical snap-visible
logical root path at `/var/snap/docker/common/var-lib-docker`.

## Why This Exists

Measured `2026-03-09` facts on Hemma:

- Docker root dir:
  - `/var/snap/docker/common/var-lib-docker`
- root (`/`) available space:
  - about `1.3 GB`
- SSD scratch (`/srv/scratch`) available space:
  - about `398 GB`

Cleaning dangling images and BuildKit cache helps immediately, but it does not
change the underlying problem: Docker itself still defaults to root-disk
storage.

The first attempted migration path changed Docker's logical root to a
home-visible bind path. That proved to be the wrong contract for the Docker
snap on this host. Live Hemma evidence showed the daemon failing to start with:

- `failed to start daemon: error while opening volume store metadata database`
- `permission denied`

The corrected contract is:

- keep Docker's logical root at:
  - `/var/snap/docker/common/var-lib-docker`
- move the backing bytes onto SSD scratch at:
  - `/srv/scratch/docker/data-root`
- bind-mount the scratch path onto the canonical snap root

This preserves snap compatibility while moving the hot Docker state off the OS
disk.

## PR Scope

- review the current Docker snap storage contract on Hemma
- use `/srv/scratch/docker/data-root` as the SSD-backed Docker byte store
- bind-mount SSD scratch onto `/var/snap/docker/common/var-lib-docker`
- migrate Docker daemon state in a controlled way
- update runbooks so future Docker growth stays off the root disk

## Important Constraint

This is a host-wide infrastructure change:

- it affects multiple repos and running services on Hemma
- it requires a controlled Docker restart and service interruption window
- it should not be folded silently into repo-local preprocessing work

## Deliverables

- [ ] One committed Docker storage-root migration surface for Hemma.
- [ ] One persisted bind mount from `/srv/scratch/docker/data-root` onto
  `/var/snap/docker/common/var-lib-docker`.
- [ ] One controlled migration path that preserves existing Docker daemon state
  during the move.
- [ ] One updated runbook/skill/rule contract that documents the host-wide
  Docker storage policy.

## Acceptance Criteria

- [ ] `docker info` continues to report the canonical Docker snap root:
  `/var/snap/docker/common/var-lib-docker`.
- [ ] `findmnt` proves that the canonical Docker snap root is bind-mounted from
  `/srv/scratch/docker/data-root`.
- [ ] Existing Docker state survives the migration, or any intentionally
  rebuilt state is explicitly recorded in the evidence.
- [ ] The host-wide runbooks and skills clearly state that Docker persistent
  state belongs on SSD scratch, not on the Hemma OS disk.

## Checklist

- [ ] Plan approved
- [ ] Migration executed
- [ ] Validation complete
- [ ] Docs updated
