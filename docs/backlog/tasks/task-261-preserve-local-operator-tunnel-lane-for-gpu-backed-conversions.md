---
id: task-261-preserve-local-operator-tunnel-lane-for-gpu-backed-conversions
title: Preserve local operator tunnel lane for GPU-backed conversions
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-35-preserve-internal-service-and-local-operator-sir-convert-lanes.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - operator-lane
  - tunnel
  - gpu
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Preserve the sanctioned local-to-Hemma operator lane for heavy GPU-backed
conversion work after public product traffic moves behind HuleEdu Gateway.

## PR Scope

- Keep or revise the documented SSH tunnel/wrapper access path.
- Ensure local CLI usage can target the tunneled service with explicit operator
  credentials.
- Prove GPU-backed conversion and readiness through the local lane.
- Update runbook guidance so local/operator, internal service, and public
  Gateway lanes are not conflated.

## Deliverables

- [ ] Runbook update for local operator lane.
- [ ] Local CLI/tunnel proof artifact.
- [ ] Credential handling guidance that avoids persisting secrets.

## Acceptance Criteria

- [ ] Local operator conversion remains possible without public direct API
  exposure.
- [ ] Heavy/GPU-dependent work can still be offloaded to Hemma.
- [ ] The lane is documented as internal/operator-only.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
