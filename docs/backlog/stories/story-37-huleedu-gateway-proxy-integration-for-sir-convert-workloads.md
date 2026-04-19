---
id: story-37-huleedu-gateway-proxy-integration-for-sir-convert-workloads
title: HuleEdu Gateway proxy integration for Sir Convert workloads
type: story
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-260-plan-huleedu-gateway-proxy-routes-for-sir-convert-jobs-and-artifacts.md
  - docs/backlog/tasks/task-264-cut-over-huleedu-and-skriptoteket-sir-convert-consumers.md
labels:
  - huledu
  - gateway
  - proxy
  - integration
---

Implementation slice with acceptance-driven scope.

## Objective

Define and hand off the HuleEdu API Gateway proxy surface that will become the
public/browser entrypoint for Sir Convert workloads.

## Scope

- Identify Gateway routes for job creation, status, result, artifact,
  checkpoint/partial, cancel/resume, templates, and push/SSE/webhook surfaces.
- Define Gateway-owned authorization, CSRF, rate-limit, audit, and error
  normalization behavior.
- Define HuleEdu Gateway forwarding of `InternalIdentityContextV1` with
  audience `sir-convert-a-lot`.
- Reuse the proven protected-edge mechanics from Skriptoteket: strip
  browser-supplied identity headers, cookies, bearer tokens, and CSRF material
  before downstream forwarding.
- Distinguish local proof proxy gates from production protected-edge
  configuration.
- Produce HuleEdu implementation tasks or handoff references.

## Acceptance Criteria

- [ ] Gateway route plan covers all required current product use cases.
- [ ] Browser-derived requests are authorized at Gateway before Sir Convert is
  called.
- [ ] Gateway-to-Sir calls carry verifiable `InternalIdentityContextV1`
  identity with audience `sir-convert-a-lot`.
- [ ] Gateway strips browser identity/cookie/bearer/CSRF material before
  forwarding to Sir Convert.
- [ ] CORS and CSRF behavior is proven for protected reads and unsafe writes.
- [ ] Local-only proxy gates are not promoted into production without a
  production-edge contract.
- [ ] Linked HuleEdu and Skriptoteket backlog or PR references, route contract
  tests, consumer smoke evidence, and signoff are recorded before public-host
  restriction starts.
- [ ] Public errors are normalized by Gateway without leaking Sir internals.
- [ ] HuleEdu repo follow-up work is clearly linked.

## Test Requirements

- [ ] Gateway route contract tests in the HuleEdu repo.
- [ ] Sir Convert internal identity tests in this repo.
- [ ] End-to-end Gateway-to-Sir proof before cutover.

## Done Definition

Done when the Gateway integration plan is implementation-ready and the
cross-repo handoff is explicit.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
