---
id: task-265-disable-direct-sir-convert-public-app-route-before-gateway-cutover
title: Disable direct Sir Convert public app route before gateway cutover
type: task
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-33-sir-convert-gateway-fronted-public-access-and-internal-lane-migration.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - compose.yaml
  - scripts/sir_convert_a_lot/devops/public_edge_verification.py
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - public-edge
  - security
  - gateway-cutover
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Disable direct public routing from `convert.hule.education` to the Sir Convert
application before the full Gateway cutover, while keeping the hostname owned
and fail-closed through a reserved public-edge response.

## PR Scope

- Remove nginx-proxy public-host advertisement from the production app service.
- Add a reserved public-edge service that owns `convert.hule.education` and
  returns a deterministic non-product 421/404-style response.
- Keep internal/tunnel service access on the production app service unchanged.
- Update public-edge verification to expect the reserved public-host response
  instead of public `/readyz`.
- Update runbook guidance so conversion clients use the tunnel/internal lane
  until the Gateway cutover re-enables the intended public edge.

## Deliverables

- [x] Production compose public-edge isolation.
- [x] Reserved public-host response config.
- [x] Public-edge verifier and report updates.
- [x] Runbook update.
- [x] Focused tests.

## Acceptance Criteria

- [x] `sir_convert_a_lot_prod` no longer sets `VIRTUAL_HOST`,
  `VIRTUAL_PORT`, or `LETSENCRYPT_HOST`.
- [x] `convert.hule.education` is owned by a reserved public-edge service, not
  by the Sir Convert app container.
- [x] Public `/readyz`, docs, metrics, job, and artifact routes do not expose
  app behavior through direct non-Gateway traffic.
- [x] Host/tunnel readiness, metrics, and conversion smoke lanes remain
  available for internal/operator use.
- [x] Final Gateway cutover tasks still own re-enabling the intended public
  product lane.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Completion Notes

Completed on 2026-04-19 and deployed to Hemma from commit
`f6eebfecd2cee273699e5b656ac49f7fb26cd248`.

Live proof:

- `sir_convert_a_lot_prod` was recreated healthy on
  `127.0.0.1:28085->8085/tcp`.
- `sir_convert_a_lot_public_reserved` was recreated and owns
  `convert.hule.education`.
- `https://convert.hule.education/readyz` returned `421` with
  `sir-convert-a-lot-public-edge-reserved`.
- `http://127.0.0.1:28085/readyz` on Hemma returned ready with the deployed
  revision.
- `sir_convert_a_lot_prod` was verified to have no `VIRTUAL_HOST`,
  `VIRTUAL_PORT`, or `LETSENCRYPT_HOST` environment variables after the
  follow-up env-leak fix.
