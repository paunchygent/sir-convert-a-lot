---
id: story-37-huleedu-gateway-proxy-integration-for-sir-convert-workloads
title: HuleEdu Gateway proxy integration for Sir Convert workloads
type: story
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-05-13'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-264-cut-over-huleedu-and-skriptoteket-sir-convert-consumers.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md
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

This Sir Convert-side planning story is complete as of 2026-05-13 because the
execution authority has moved into HuleEdu as:

`/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`

The former Sir Convert Task 260 planning item was migrated into that HuleEdu
story. Sir Convert keeps the runtime implementation authority in:

`docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md`

## Scope

- HuleEdu `ST-01-07` now owns the Gateway route names, auth-edge behavior,
  CSRF/rate-limit policy, public prefix, downstream audience, streaming
  behavior, and implementation proof.
- Sir Convert `Task 282` owns the runtime routes, artifact bundle persistence,
  owner-scoped service authorization, and rejection behavior that HuleEdu must
  target.
- This story remains only as the Sir Convert cross-repo handoff record.

## Acceptance Criteria

- [x] Gateway route plan covers all required current product use cases for the
  current DigiExam migration bundle route.
- [x] Browser-derived requests are authorized at Gateway before Sir Convert is
  called.
- [x] Gateway-to-Sir calls carry verifiable `InternalIdentityContextV1`
  identity with audience `sir-convert-a-lot`.
- [x] Gateway strips browser identity/cookie/bearer/CSRF material before
  forwarding to Sir Convert.
- [x] CORS and CSRF behavior is assigned to the HuleEdu-owned implementation
  story for protected reads and unsafe writes.
- [x] Local-only proxy gates are not promoted into production without a
  production-edge contract.
- [x] Linked HuleEdu backlog reference is recorded before public-host
  restriction starts.
- [x] Public errors are assigned to Gateway normalization without leaking Sir
  internals.
- [x] HuleEdu repo follow-up work is clearly linked.

## Test Requirements

- [x] Gateway route contract tests are required by HuleEdu `ST-01-07`.
- [x] Sir Convert internal identity tests are required by `Task 282`.
- [x] End-to-end Gateway-to-Sir proof before cutover is required by HuleEdu
  `ST-01-07` and later cutover proof tasks.

## Done Definition

Done when the Gateway integration plan is implementation-ready and the
cross-repo handoff is explicit. This is now satisfied by the HuleEdu `ST-01-07`
story plus Sir Convert `Task 282`.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
