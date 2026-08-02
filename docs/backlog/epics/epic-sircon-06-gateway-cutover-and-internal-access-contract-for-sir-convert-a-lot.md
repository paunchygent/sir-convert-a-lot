---
type: epic
id: EPIC-SIRCON-06
title: Gateway cutover and internal access contract for Sir Convert-a-Lot
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
links:
  decisions: []
outcome: Gateway cutover and internal access contract for Sir Convert-a-Lot
retired_ids:
- epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot
---
## Scope

Source record: docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md

### In Scope

> - ADR-backed public/internal/operator access policy.
> - Inventory of current HuleEdu, Skriptoteket, service-to-service, CLI, tunnel,
>   and public-host consumers before cutover.
> - Sir Convert production hardening for unauthenticated failures, public
>   metadata exposure, docs/OpenAPI/metrics exposure, and security headers.
> - Sir Convert authorization profile for HuleEdu `InternalIdentityContextV1`
>   with audience `sir-convert-a-lot`, covering Gateway-forwarded product
>   workloads plus explicit non-browser service/operator extensions.
> - HuleEdu Gateway proxy route planning and cross-repo implementation handoff.
>   The HuleEdu execution authority is now
>   `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`.
> - Future governed conversion routes, including the proposed speech-to-text
>   `audio -> transcript_bundle` route, use the same `/sir-convert` product-edge
>   authority when they become product/browser surfaces.
> - Local operator tunnel/offload lane preservation.
> - Pre-cutover direct public app-route isolation for `convert.hule.education`.
> - Auth-aware public-edge evidence for ruling out or blocking unknown direct
>   public consumers before final live testing.
> - Public `convert.hule.education` restriction or fail-closed cutover.
> - End-to-end security and migration proof.

### Out of Scope

> - Removing Sir Convert's internal service-to-service capability.
> - Removing the local operator tunnel/offload workflow.
> - Changing conversion API behavior or GPU-first execution semantics except
>   where auth/transport metadata is required by ADR-0009.
> - Implementing HuleEdu Gateway code in this repo; this repo owns the Sir
>   Convert-side contract, docs, and cross-repo handoff.

## Epic Contract

## ADR Coverage

## Contract Inputs

## Stories

### Stories

> 1. `docs/backlog/stories/st-sircon-06-02-adr-and-contract-authority-for-sir-convert-gateway-cutover.md`
> 1. `docs/backlog/stories/st-sircon-06-01-sir-convert-gateway-fronted-public-access-and-internal-lane-migration.md`
> 1. `docs/backlog/stories/st-sircon-06-04-sir-convert-internal-auth-and-metadata-hardening-before-cutover.md`
> 1. `docs/backlog/stories/story-37-huleedu-gateway-proxy-integration-for-sir-convert-workloads.md`
>    (completed Sir Convert-side handoff; implementation authority moved to
>    HuleEdu `ST-01-07`)
> 1. `docs/backlog/stories/st-sircon-06-03-preserve-internal-service-and-local-operator-sir-convert-lanes.md`

## Epic Verification Plan

### Source Acceptance Criteria

> - [ ] ADR-0009 is accepted and linked from converter docs, runbooks, and
>   downstream integration guidance.
> - [x] Every current caller and access lane is inventoried before Gateway
>   product migration or final live public-edge re-enable.
> - [ ] Product/browser traffic is routed through HuleEdu Gateway with Gateway
>   session/CSRF/role/entitlement enforcement.
> - [ ] Direct internal Hemma callers have a documented and tested Sir Convert
>   authorization profile for InternalIdentityContextV1.
> - [ ] User-originated backend-submitted jobs carry verifiable user context and
>   do not collapse to global service-key ownership.
> - [ ] Local operator tunnel/offload usage remains documented and tested.
> - [ ] convert.hule.education is restricted to the ADR-0009 fail-closed
>   reserved/default posture and no longer exposes public job APIs, OpenAPI docs,
>   metrics, or detailed readiness by default.
> - [ ] Cutover proof demonstrates public deny, Gateway allow, internal service
>   allow, local operator allow, and unknown-host fail-closed behavior.
> - [ ] Unknown public consumers are either ruled out by auth-aware redacted
>   public-edge evidence or carried as explicit cutover blockers.

## Exceptions And Follow-Ups

## Risks

## Notes

### Goal

> Move Sir Convert-a-Lot public/product access behind the HuleEdu API Gateway
> while preserving Sir Convert as a direct internal Hemma conversion service and
> a local operator-accessible GPU offload lane.

## Decision And Assumption Ledger

## Plan Document Review

## Epic Closeout Review
