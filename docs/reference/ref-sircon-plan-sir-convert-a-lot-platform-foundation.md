---
type: reference
id: REF-SIRCON-PLAN-sir-convert-a-lot-platform-foundation
title: Sir Convert-a-Lot platform foundation
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: plan
retired_ids:
- 001-sir-convert-a-lot-platform-foundation-programme
summary: Sir Convert-a-Lot platform foundation
---

## Outcome And Purpose

## Planning Boundary

## Evidence Basis

## Confirmed Contract

## Backlog Derivation

## Planning Stop Conditions

## Historical Source Content

### Objective

Establish a long-lived, cross-cutting programme that standardizes how conversion capabilities are
planned, implemented, validated, and operated across local repos and Hemma-hosted services.

### Scope

- Governance and docs-as-code standards.
- Platform architecture and API contracts.
- Operational runbooks and DevOps skill coverage.
- Cross-repo integration consistency (HuleEdu + Skriptoteket + future repos).

### Delivery Model

- Programme owns strategy and cross-cutting policy.
- Epics own coherent capability increments.
- Stories own implementation slices.
- Tasks own concrete execution units.

### Active Epics

1. `docs/backlog/epics/epic-sircon-01-unified-conversion-service-hemma-first-multi-format-cross-repo.md`
1. `docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md`
1. `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
1. `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`

### Recently Completed Epics

1. `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md`

### Acceptance Criteria

1. Planning hierarchy (`programme -> epic -> story -> task`) is enforced by repo docs contract.
1. Docs taxonomy is explicit and validated (`runbook`, `reference`, `ADR`, `PDR`).
1. Canonical AGENTS guidance reflects established Skriptoteket/HuleEdu operational standards.
1. Hemma/GPU operational instructions and skill are present and maintained in-repo.

### Checklist

- [x] Programme scaffold created
- [x] Linked epics and setup stories/tasks
- [ ] Programme governance execution complete
