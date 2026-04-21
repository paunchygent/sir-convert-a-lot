---
type: decision
id: ADR-0009
title: Gateway-Fronted Sir Convert Public Access and Internal Service Boundary
status: proposed
created: 2026-04-19
updated: 2026-04-19
owners:
  - platform
tags:
  - adr
  - auth
  - gateway
  - hemma
  - huledu
  - internal-service
  - public-edge
  - skriptoteket
links:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/tasks/task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover.md
  - docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

Define the target public and internal access boundary for Sir Convert-a-Lot
before migrating product traffic behind the HuleEdu API Gateway.

## Status

- Proposed
- Date: 2026-04-19

## 1. Problem and Context

Sir Convert-a-Lot is now a Hemma-hosted GPU-backed conversion service used by
HuleEdu, Skriptoteket, operator workflows, and local development/offload
workflows. Its current direct public surface on `convert.hule.education` uses a
service API key and exposes operational endpoints such as readiness, metrics,
and OpenAPI documentation.

That direct public model is too narrow for product/browser traffic because it
cannot express user session, CSRF, product entitlement, tenant, role, or
cross-product audit semantics. Those concerns already belong to the HuleEdu API
Gateway and the shared Hule Education browser-session authority.

At the same time, Sir Convert must remain usable as an internal network
resource for other Hemma services and as an operator-accessible GPU offload
service from a local machine.

## 2. Decision

Adopt a gateway-fronted public access model for product/browser traffic while
preserving direct internal and operator lanes.

Sir Convert must not mint a parallel signed identity format. The downstream
identity transport for Gateway/user-originated traffic is HuleEdu's accepted
`InternalIdentityContextV1` contract from ADR-0039 and the HuleEdu internal
identity reference:

- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/decisions/0039-huleedu-owned-browser-session-authority-and-saas-bootstrap-contract.md`
- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/reference/ref-internal-identity-context-v1-contract.md`

Sir Convert consumes that contract with audience `sir-convert-a-lot` and adds
only a Sir-specific authorization profile for conversion jobs and artifacts.
The profile is tracked in
`docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.

### 2.1 Public product lane

Browser and product-originated traffic must enter through HuleEdu API Gateway.
Gateway owns:

- browser session validation;
- CSRF protection;
- user, role, tenant, and product entitlement checks;
- request rate limiting and abuse controls;
- public error normalization;
- browser-facing audit correlation.

Sir Convert must not accept unsigned public user identity claims directly.

### 2.2 Internal service lane

Sir Convert remains a direct internal Hemma network service for sanctioned
backend callers such as HuleEdu services, Skriptoteket backend services, and
future internal services.

The first enforced identity model is HuleEdu
`InternalIdentityContextV1` with audience `sir-convert-a-lot`.

Every Sir Convert job, status read, result read, artifact download, checkpoint
read, partial-artifact read, resume, cancel, template mutation, and push
configuration request must carry verified `InternalIdentityContextV1` when the
workload is Gateway/user-originated. A transport credential may prove that the
network caller is allowed to reach Sir Convert, but it is not sufficient for
job ownership or artifact authorization.

Sir Convert must verify the canonical HuleEdu headers:

- `X-Huledu-Identity-Context-Version`
- `X-Huledu-Identity-Context`
- `X-Huledu-Identity-Key-Id`
- `X-Huledu-Identity-Signature`
- `X-Correlation-ID`

Sir Convert must enforce issuer, key id, signature, expiry, context version,
replay protections where needed, and audience `sir-convert-a-lot` according to
the HuleEdu reference contract. Browser cookies, bearer tokens, CSRF headers,
and unsigned identity headers are not downstream identity.

For non-browser internal service and local operator workflows, Sir Convert also
consumes HuleEdu-minted `InternalIdentityContextV1`. Those contexts must be
minted by a HuleEdu-owned Gateway/internal identity authority using the
canonical HuleEdu signing key set and `iss == "api_gateway_service"`. Sir
Convert must not mint contexts, accept a Sir-specific issuer, accept
service/operator self-signed contexts, or treat API keys as job/artifact
ownership. Required service/operator field mappings, including nonblank
non-browser `session_id` handles, are defined in the Sir Convert authorization
profile.

Sir Convert must derive durable job ownership from the verified
`InternalIdentityContextV1` plus the Sir-specific authorization profile and
enforce that ownership on status, result, artifact, checkpoint, partial,
resume, cancel, and webhook/template routes. The current single service API
key may remain as a transport credential during migration, but it must not
remain the authorization scope for all jobs and artifacts.

Direct internal callers may bypass Gateway only for non-user-originated backend
workflows, or when they carry Gateway-issued `InternalIdentityContextV1` from
the original browser/product request. Unsigned identity headers are never
trusted.

Task 259 is a hard prerequisite for accepting this ADR and for any product
traffic cutover: it must define the Sir-specific
`InternalIdentityContextV1` authorization profile, job-owner derivation,
artifact/status access rules, grants/scopes, any explicit non-browser
service/operator extension, and authorization tests. It must not define a
parallel Sir identity transport.

### 2.3 Local operator lane

Operators must retain a documented local offload path for heavy conversions and
GPU-reliant processing, using the sanctioned Hemma tunnel or wrapper surface.
The local lane is an operator/internal lane, not a public product API.

### 2.4 Direct public convert host

`convert.hule.education` must not remain the normal public job API after
cutover. The accepted posture for this ADR is **fail-closed reserved/default
response** after replacement lanes are proven.

A minimal public status page or external machine-to-machine API is out of scope
for this ADR and requires a separate accepted ADR, route contract, auth model,
rate-limit/abuse policy, and proof.

OpenAPI docs, metrics, and detailed readiness must not be publicly exposed by
default in production.

## 3. Access Lane Matrix

| Lane | Caller | Entry | Primary auth boundary | Supported after cutover |
| --- | --- | --- | --- | --- |
| Product/browser | HuleEdu/Skriptoteket UI | HuleEdu API Gateway | Browser session, CSRF, roles, entitlement | yes |
| Backend internal | HuleEdu/Skriptoteket/internal services | Hemma internal network | `InternalIdentityContextV1` for user-originated workloads; Sir-profiled service context for non-browser service workflows | yes |
| Local operator | Devops/local CLI via tunnel | local tunnel to Hemma listener | Sir-profiled operator extension to the internal identity contract | yes |
| Direct anonymous public | internet caller | `convert.hule.education` | none | no |

## 4. User-Originated Workload Rule

Any job caused by a human/product session is user-originated even if a backend
worker eventually submits the HTTP request to Sir Convert.

User-originated jobs must either:

- enter through HuleEdu Gateway; or
- carry Gateway-issued `InternalIdentityContextV1` with audience
  `sir-convert-a-lot` all the way to Sir Convert.

Sir Convert must persist that context-derived ownership and enforce it for all
subsequent job, status, result, artifact, partial, checkpoint, resume, cancel,
template, SSE, and webhook-related access. A backend service must not turn a
browser/user workload into a global service-owned job merely by using the
direct internal lane.

## 5. Consequences

### Positive

- Public authorization is centralized in the existing Gateway authority.
- Sir Convert stays focused on conversion execution, GPU policy, retention, and
  artifact safety.
- Internal services can continue to use Sir Convert without unnecessary
  Gateway hops when the workflow is service-to-service.
- Local GPU offload remains a first-class operator workflow.

### Costs

- Gateway proxy routes and identity propagation must be implemented and
  verified.
- Existing direct consumers must be inventoried and migrated deliberately.
- Sir Convert needs a stricter internal identity model than the current single
  public service API key.
- Public-edge and docs/runbook guidance must change together to avoid stale
  `convert.hule.education` advice.

## 6. Follow-up

- Complete the caller/access-lane inventory in
  `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md`.
- Complete Task 259 before ADR acceptance so the Sir-specific
  `InternalIdentityContextV1` authorization profile and implementation test
  plan are not left as implementation discretion.
- Harden the current public surface before cutover so unauthorized traffic
  fails cleanly and metadata exposure is reduced.
- Add Gateway proxy planning and implementation tasks in the HuleEdu repo once
  this ADR is accepted.
- Run a final cutover proof that covers public-deny, Gateway-allow,
  internal-service-allow, local-operator-allow, and unknown-host fail-closed
  behavior.
