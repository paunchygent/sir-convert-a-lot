---
id: task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover
title: Inventory Sir Convert callers and access lanes before gateway cutover
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-34-adr-and-contract-authority-for-sir-convert-gateway-cutover.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - inventory
  - migration
  - gateway
  - huledu
  - skriptoteket
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Inventory every current Sir Convert caller, access lane, credential source,
route usage, and migration constraint before the Gateway cutover changes any
public or internal access behavior.

## PR Scope

- Populate `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md`
  with migration-relevant facts.
- Inspect this repo's docs, runbooks, clients, adapters, env guidance, and
  verification scripts for caller/access-lane references.
- Inspect HuleEdu and Skriptoteket repos for direct Sir Convert usage and
  classify each use as browser-derived, backend-internal, or operator-local.
- Identify any external or unknown direct `convert.hule.education` consumer.
- Capture empirical public-edge evidence from nginx-proxy/access logs over a
  defined window, including route, status, host, and API-key presence/absence
  counts with secrets redacted.
- Record target lane, migration decision, blockers, and follow-up task for each
  caller.

## Deliverables

- [ ] Updated caller/access-lane inventory reference.
- [ ] Decision-ready migration matrix for public, internal, and local operator
  lanes.
- [ ] Redacted public-edge usage artifact showing observed
  `convert.hule.education` route/status/caller patterns over the chosen
  evidence window.
- [ ] Follow-up task links for Gateway, internal identity, local operator, and
  public-edge restriction work.

## Acceptance Criteria

- [ ] No public route is removed or repointed before the inventory is complete.
- [ ] HuleEdu and Skriptoteket direct usages are classified with target lanes.
- [ ] Local operator tunnel/offload use cases are explicitly preserved.
- [ ] Internal service direct-call use cases are explicitly preserved.
- [ ] Unknown or unowned direct public consumers are either ruled out or tracked
  as cutover blockers.
- [ ] Unknown public consumers are not marked ruled out by repo inspection
  alone. If access logs or equivalent empirical evidence are unavailable, they
  remain a cutover blocker.

## Checklist

- [ ] Inventory complete
- [ ] Validation complete
- [ ] Docs updated
