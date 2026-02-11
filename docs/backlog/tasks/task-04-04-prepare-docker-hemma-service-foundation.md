---
id: '007-prepare-docker-hemma-service-foundation'
title: 'Prepare Docker + Hemma service foundation'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - 'docs/backlog/stories/story-04-01-standalone-repo-bootstrap-and-governance-setup.md'
  - 'docs/runbooks/runbook-hemma-devops-and-gpu.md'
  - '.agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md'
labels:
  - 'docker'
  - 'hemma'
  - 'gpu'
---
# Prepare Docker + Hemma service foundation

## Objective

Create the operational baseline needed to run Sir Convert-a-Lot on Hemma with GPU-first policy and
local tunnel-based development.

## PR Scope

- Hemma/GPU runbook and skill bootstrap in this repo.
- Wrapper scripts for local/remote command execution contexts.

## Deliverables

- Repo-specific Hemma/GPU runbook.
- Repo-specific DevOps skill under `.agents/skills/`.
- Command wrappers for local and remote execution context.

## Acceptance Criteria

1. Runbook exists and defines canonical host paths, command wrappers, and GPU checks.
2. DevOps skill references runbook and cross-repo Hemma topology.
3. `run-local-pdm` and `run-hemma` scripts exist and are documented.

## Checklist

- [x] Runbook created
- [x] DevOps skill created
- [x] Wrapper scripts added
- [ ] Task status moved to completed
