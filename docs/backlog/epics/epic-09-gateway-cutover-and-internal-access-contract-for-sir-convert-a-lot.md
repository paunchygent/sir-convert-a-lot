---
id: epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot
title: Gateway cutover and internal access contract for Sir Convert-a-Lot
type: epic
status: proposed
priority: critical
created: '2026-04-19'
last_updated: '2026-05-13'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/backlog/tasks/task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover.md
  - docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md
  - docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - gateway
  - auth
  - public-edge
  - internal-service
  - hemma
  - huledu
  - skriptoteket
---

Major capability increment managed through linked stories.

## Goal

Move Sir Convert-a-Lot public/product access behind the HuleEdu API Gateway
while preserving Sir Convert as a direct internal Hemma conversion service and
a local operator-accessible GPU offload lane.

## In Scope

- ADR-backed public/internal/operator access policy.
- Inventory of current HuleEdu, Skriptoteket, service-to-service, CLI, tunnel,
  and public-host consumers before cutover.
- Sir Convert production hardening for unauthenticated failures, public
  metadata exposure, docs/OpenAPI/metrics exposure, and security headers.
- Sir Convert authorization profile for HuleEdu `InternalIdentityContextV1`
  with audience `sir-convert-a-lot`, covering Gateway-forwarded product
  workloads plus explicit non-browser service/operator extensions.
- HuleEdu Gateway proxy route planning and cross-repo implementation handoff.
  The HuleEdu execution authority is now
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`.
- Future governed conversion routes, including the proposed speech-to-text
  `audio -> transcript_bundle` route, use the same `/sir-convert` product-edge
  authority when they become product/browser surfaces.
- Local operator tunnel/offload lane preservation.
- Pre-cutover direct public app-route isolation for `convert.hule.education`.
- Auth-aware public-edge evidence for ruling out or blocking unknown direct
  public consumers before final live testing.
- Public `convert.hule.education` restriction or fail-closed cutover.
- End-to-end security and migration proof.

## Out of Scope

- Removing Sir Convert's internal service-to-service capability.
- Removing the local operator tunnel/offload workflow.
- Changing conversion API behavior or GPU-first execution semantics except
  where auth/transport metadata is required by ADR-0009.
- Implementing HuleEdu Gateway code in this repo; this repo owns the Sir
  Convert-side contract, docs, and cross-repo handoff.

## Stories

1. `docs/backlog/stories/story-34-adr-and-contract-authority-for-sir-convert-gateway-cutover.md`
1. `docs/backlog/stories/story-33-sir-convert-gateway-fronted-public-access-and-internal-lane-migration.md`
1. `docs/backlog/stories/story-36-sir-convert-internal-auth-and-metadata-hardening-before-cutover.md`
1. `docs/backlog/stories/story-37-huleedu-gateway-proxy-integration-for-sir-convert-workloads.md`
   (completed Sir Convert-side handoff; implementation authority moved to
   HuleEdu `ST-01-07`)
1. `docs/backlog/stories/story-35-preserve-internal-service-and-local-operator-sir-convert-lanes.md`

## Acceptance Criteria

- [ ] ADR-0009 is accepted and linked from converter docs, runbooks, and
  downstream integration guidance.
- [x] Every current caller and access lane is inventoried before Gateway
  product migration or final live public-edge re-enable.
- [ ] Product/browser traffic is routed through HuleEdu Gateway with Gateway
  session/CSRF/role/entitlement enforcement.
- [ ] Direct internal Hemma callers have a documented and tested Sir Convert
  authorization profile for `InternalIdentityContextV1`.
- [ ] User-originated backend-submitted jobs carry verifiable user context and
  do not collapse to global service-key ownership.
- [ ] Local operator tunnel/offload usage remains documented and tested.
- [ ] `convert.hule.education` is restricted to the ADR-0009 fail-closed
  reserved/default posture and no longer exposes public job APIs, OpenAPI docs,
  metrics, or detailed readiness by default.
- [ ] Cutover proof demonstrates public deny, Gateway allow, internal service
  allow, local operator allow, and unknown-host fail-closed behavior.
- [ ] Unknown public consumers are either ruled out by auth-aware redacted
  public-edge evidence or carried as explicit cutover blockers.

## Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [ ] Execution gate defined
