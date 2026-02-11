---
id: '001-sir-convert-a-lot-platform-foundation-programme'
title: 'Sir Convert-a-Lot platform foundation'
type: 'programme'
status: 'in_progress'
priority: 'critical'
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - 'docs/backlog/epics/epic-03-unified-conversion-service.md'
  - 'docs/backlog/stories/story-04-01-standalone-repo-bootstrap-and-governance-setup.md'
  - 'docs/runbooks/runbook-hemma-devops-and-gpu.md'
labels:
  - 'programme'
  - 'cross-cutting'
  - 'governance'
---
# Sir Convert-a-Lot platform foundation

## Objective

Establish a long-lived, cross-cutting programme that standardizes how conversion capabilities are
planned, implemented, validated, and operated across local repos and Hemma-hosted services.

## Scope

- Governance and docs-as-code standards.
- Platform architecture and API contracts.
- Operational runbooks and DevOps skill coverage.
- Cross-repo integration consistency (HuleEdu + Skriptoteket + future repos).

## Delivery Model

- Programme owns strategy and cross-cutting policy.
- Epics own coherent capability increments.
- Stories own implementation slices.
- Tasks own concrete execution units.

## Active Epics

1. `docs/backlog/epics/epic-03-unified-conversion-service.md`

## Acceptance Criteria

1. Planning hierarchy (`programme -> epic -> story -> task`) is enforced by repo docs contract.
2. Docs taxonomy is explicit and validated (`runbook`, `reference`, `ADR`, `PDR`).
3. Canonical AGENTS guidance reflects established Skriptoteket/HuleEdu operational standards.
4. Hemma/GPU operational instructions and skill are present and maintained in-repo.

## Checklist

- [x] Programme scaffold created
- [x] Linked epics and setup stories/tasks
- [ ] Programme governance execution complete
