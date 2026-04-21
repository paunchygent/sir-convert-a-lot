---
id: task-260-plan-huleedu-gateway-proxy-routes-for-sir-convert-jobs-and-artifacts
title: Plan HuleEdu Gateway proxy routes for Sir Convert jobs and artifacts
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-37-huleedu-gateway-proxy-integration-for-sir-convert-workloads.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
labels:
  - huledu
  - gateway
  - proxy
  - planning
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Plan the HuleEdu API Gateway proxy routes and authorization behavior required
to serve Sir Convert workloads for product/browser traffic.

## PR Scope

- Map current Sir Convert routes to Gateway-facing routes.
- Define session, CSRF, role, entitlement, rate-limit, and audit requirements.
- Require the proven HuleEdu/Skriptoteket protected-edge mechanics:
  Gateway validates the browser session, enforces CSRF for unsafe writes,
  strips browser-supplied identity headers, cookies, bearer tokens, and CSRF
  material before downstream forwarding, then signs
  `InternalIdentityContextV1` for audience `sir-convert-a-lot`.
- Define upload and artifact streaming behavior.
- Define the HuleEdu-owned service/operator context minting surfaces required
  by the Sir Convert authorization profile, including the internal
  service-token exchange, operator wrapper path, and field mapping that remains
  valid under the HuleEdu `InternalIdentityContextV1` v1 schema.
- Define error normalization and timeout behavior.
- Define production-edge configuration separately from local-only proxy gates
  so no local proof toggle is promoted to production without an accepted
  production-edge contract.
- Produce linked HuleEdu and Skriptoteket backlog/PR requirements for the
  owned implementation work.
- Define cross-repo signoff required before Task 262 may restrict the public
  host.

## Deliverables

- [ ] Gateway route matrix.
- [ ] Authorization and rate-limit requirements.
- [ ] `InternalIdentityContextV1` forwarding requirements for audience
  `sir-convert-a-lot`.
- [ ] Header-stripping requirements for browser-supplied identity headers,
  cookies, bearer tokens, and CSRF material before downstream forwarding.
- [ ] CORS and CSRF proof requirements for protected reads and unsafe writes.
- [ ] Production-edge contract requirements that prevent promoting local-only
  proxy gates into production.
- [ ] Service/operator context minting surface requirements, including
  HuleEdu-owned signing authority, mandatory field mapping, non-browser
  `session_id` handles, lane restrictions, and no undeclared top-level
  Sir-specific fields.
- [ ] Linked HuleEdu Gateway implementation backlog or PR reference.
- [ ] Linked Skriptoteket consumer migration backlog or PR reference when
  Skriptoteket usage is in scope.
- [ ] Route contract tests and consumer smoke evidence requirements.
- [ ] Explicit cross-repo signoff gate before public-host restriction.

## Acceptance Criteria

- [ ] All product/browser current use cases have a Gateway route or an explicit
  no-migrate decision.
- [ ] Gateway route plan distinguishes job creation, polling, artifacts,
  templates, SSE/webhooks, cancel/resume, and health/status.
- [ ] No public browser route requires consumers to hold Sir Convert's internal
  service credential.
- [ ] Gateway validates HuleEdu browser session and CSRF before proxying Sir
  Convert protected reads and unsafe writes.
- [ ] Gateway strips browser identity/cookie/bearer/CSRF material and forwards
  only the signed `InternalIdentityContextV1` plus required proxy headers.
- [ ] Gateway signs `InternalIdentityContextV1` with audience
  `sir-convert-a-lot`; Sir Convert rejects missing, invalid, wrong-audience,
  expired, unknown-key, and spoofed unsigned identity inputs.
- [ ] Non-browser service/operator contexts are minted only by the HuleEdu-owned
  Gateway/internal identity authority and cannot be self-signed by Sir Convert,
  service callers, or operator tooling.
- [ ] CORS and CSRF behavior is proven for protected reads and unsafe writes.
- [ ] Local-only proxy gates are explicitly forbidden from becoming production
  exposure without a production-edge contract and proof.
- [ ] Task 262 cannot start until linked HuleEdu/Skriptoteket work is accepted
  or explicitly ruled out by the inventory.
- [ ] Gateway route tests and consumer smoke evidence are named as cutover
  prerequisites, not optional follow-up notes.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
