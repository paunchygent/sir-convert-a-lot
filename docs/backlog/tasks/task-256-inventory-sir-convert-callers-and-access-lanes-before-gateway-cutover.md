---
id: task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover
title: Inventory Sir Convert callers and access lanes before gateway cutover
type: task
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-34-adr-and-contract-authority-for-sir-convert-gateway-cutover.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md
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
route usage, and migration constraint before Gateway product migration or final
live public-edge re-enable changes public or internal access behavior.

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

- [x] Updated caller/access-lane inventory reference.
- [x] Decision-ready migration matrix for public, internal, and local operator
  lanes.
- [x] Redacted public-edge usage artifact showing observed
  `convert.hule.education` route/status/caller patterns over the chosen
  evidence window.
- [x] Follow-up task links for Gateway, internal identity, local operator, and
  public-edge restriction work.

## Acceptance Criteria

- [x] No Gateway product route migration or final live public-edge re-enable is
  performed before the inventory is complete. Task 265's fail-closed reserved
  public-host isolation is recorded as a pre-cutover safety control.
- [x] HuleEdu and Skriptoteket direct usages are classified with target lanes.
- [x] Local operator tunnel/offload use cases are explicitly preserved.
- [x] Internal service direct-call use cases are explicitly preserved.
- [x] Unknown or unowned direct public consumers are either ruled out or tracked
  as cutover blockers.
- [x] Unknown public consumers are not marked ruled out by repo inspection
  alone. If access logs or equivalent empirical evidence are unavailable, they
  remain a cutover blocker.

## Checklist

- [x] Inventory complete
- [x] Validation complete
- [x] Docs updated

## Completion Notes

Completed on 2026-04-19.

Inventory findings:

- HuleEdu repo inspection found public ingress monitoring and optional
  host-wide startup references, but no current HuleEdu application code calling
  Sir Convert directly.
- Skriptoteket has user-originated backend callers in Conversion Hub and
  Klassrumskartan class-list PDF import.
- Projektveckor Portal is a retained internal Hemma caller using the direct
  Docker-network service lane.
- Local operator tunnel/offload remains a required lane.
- Public-edge evidence was captured under
  `build/verification/task-256-gateway-cutover-caller-inventory/`.

The 24h nginx-proxy evidence did not show a successful public conversion
workflow, but unknown public consumers are **not** ruled out because the current
log format cannot classify API-key presence. Task 266 owns auth-aware public
edge evidence before final cutover proof.
