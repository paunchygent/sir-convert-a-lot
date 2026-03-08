---
id: task-113-migrate-hemma-docker-storage-root-to-data-backed-disk
title: Migrate Hemma Docker storage root to SSD scratch through a home-visible bind mount
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

Stop storing Hemma Docker daemon data on the root disk by migrating Docker's
storage root onto the SSD scratch tier through a Docker-snap-compatible
home-visible bind mount.

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

The Docker snap's documented `data-root` configuration must target a location
the snap can access, which makes a home-visible compatibility path necessary
even though the underlying bytes should live on SSD scratch.

## PR Scope

- review the current Docker snap storage contract on Hemma
- choose the supported migration target on SSD scratch
- create and persist the home-visible compatibility bind mount backed by SSD
  scratch
- migrate Docker daemon state in a controlled way
- update runbooks so future Docker growth stays off the root disk

## Important Constraint

This is a host-wide infrastructure change:

- it affects multiple repos and running services on Hemma
- it requires a controlled Docker restart and service interruption window
- it should not be folded silently into repo-local preprocessing work

## Deliverables

- [ ] One committed Docker storage-root migration surface for Hemma.
- [ ] One persisted home-visible bind mount backed by SSD scratch for Docker's
  configured data root.
- [ ] One controlled migration path that preserves existing Docker daemon state
  during the move.
- [ ] One updated runbook/skill/rule contract that documents the host-wide
  Docker storage policy.

## Acceptance Criteria

- [ ] `docker info` reports a data-root path that no longer lives under the
  root-backed `/var/snap/docker/...` tree.
- [ ] The configured Docker data root resolves to storage that physically lives
  on `/srv/scratch`.
- [ ] Existing Docker state survives the migration, or any intentionally
  rebuilt state is explicitly recorded in the evidence.
- [ ] The host-wide runbooks and skills clearly state that Docker persistent
  state belongs on SSD scratch, not on the Hemma OS disk.

## Checklist

- [ ] Plan approved
- [ ] Migration executed
- [ ] Validation complete
- [ ] Docs updated
