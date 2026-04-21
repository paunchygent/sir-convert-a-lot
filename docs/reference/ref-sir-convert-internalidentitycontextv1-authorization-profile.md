---
type: reference
id: REF-sir-convert-internalidentitycontextv1-authorization-profile
title: Sir Convert InternalIdentityContextV1 Authorization Profile
status: active
created: 2026-04-19
updated: 2026-04-19
owners:
  - platform
tags:
  - auth
  - gateway
  - internal-identity
  - authorization
  - cutover
links:
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
---

## Purpose

Define the Sir Convert-specific authorization profile layered on top of the
HuleEdu `InternalIdentityContextV1` signed downstream identity contract.

This document does not define a new identity transport. Sir Convert consumes
the HuleEdu contract owned by ADR-0039 and
`REF-internal-identity-context-v1-contract` with audience
`sir-convert-a-lot`.

Canonical external authority:

- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/decisions/0039-huleedu-owned-browser-session-authority-and-saas-bootstrap-contract.md`
- `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/reference/ref-internal-identity-context-v1-contract.md`

## Transport Authority

Sir Convert accepts identity only through the canonical HuleEdu headers:

- `X-Huledu-Identity-Context-Version`
- `X-Huledu-Identity-Context`
- `X-Huledu-Identity-Key-Id`
- `X-Huledu-Identity-Signature`
- `X-Correlation-ID`

Verification must fail closed unless all canonical checks pass:

- recognized key id;
- valid detached RS256 signature over the encoded context;
- `iss == "api_gateway_service"`;
- `aud == "sir-convert-a-lot"`;
- supported `context_version`;
- non-empty required fields from the HuleEdu contract;
- valid `iat` and `exp` within the accepted skew;
- replay protection for persisted or reused contexts where required.

`X-API-Key` may remain as a transport credential during migration, but it is
not job ownership, artifact ownership, user identity, tenant identity, or proof
that Gateway minted the context.

Sir Convert must not mint, refresh, or sign `InternalIdentityContextV1`
payloads. It trusts only HuleEdu-owned signing keys configured through the
canonical HuleEdu internal identity verifier. A `sir_convert_a_lot` issuer,
service self-signed context, operator self-signed context, or Sir-local signing
key is forbidden.

## Rejected Inputs

Sir Convert must reject or ignore these as identity:

- unsigned `X-User-ID`, `X-Org-ID`, `X-Tenant-ID`, `X-Identity-*`, or similar
  headers;
- browser cookies;
- browser bearer tokens;
- CSRF headers forwarded to Sir Convert;
- query-string user, tenant, role, or grant claims;
- `X-API-Key` alone for any user-originated workload after enforcement.

Gateway route work must strip browser-supplied identity, cookie, bearer, and
CSRF material before downstream forwarding.

## Caller Classes

| Class | Allowed transport | Ownership source | Notes |
| --- | --- | --- | --- |
| Gateway product/browser | Gateway proxy route plus signed `InternalIdentityContextV1` | verified user context | Normal public/product lane. |
| User-originated backend worker | Internal service transport plus the original Gateway-issued `InternalIdentityContextV1` | verified user context | A backend worker must not convert user work into global service-owned work. |
| Non-browser internal service | Internal transport plus Sir-profiled service context using the canonical HuleEdu identity headers | verified service context | Requires explicit grants and must not use a separate Sir-signed issuer. |
| Local operator | Tunnel/internal transport plus Sir-profiled operator context using the canonical HuleEdu identity headers | verified operator context | Must be auditable and distinct from product/browser work. |
| Anonymous public | none | none | Reserved/fail-closed only. |

## Minting Authority

All accepted contexts are minted by a HuleEdu-owned Gateway/internal identity
authority using the canonical HuleEdu `InternalIdentityContextV1` signing key
set and `iss == "api_gateway_service"`.

Allowed minting paths:

- Gateway product/browser contexts are minted by HuleEdu Gateway after browser
  session, CSRF, role, and entitlement checks.
- User-originated backend worker contexts are the original Gateway-issued
  product/browser contexts propagated through the backend worker. A backend
  worker may not replace that context with a service-owned context.
- Non-browser service contexts are minted only through a HuleEdu-owned
  internal service-token exchange or equivalent HuleEdu Gateway/internal
  identity surface. The exact HuleEdu route name is owned by Task 260, but the
  authority is not optional: it is HuleEdu-owned, signs with the HuleEdu
  Gateway/internal identity key set, and emits `iss == "api_gateway_service"`.
- Local operator contexts are minted only through a HuleEdu-owned operator
  context surface or wrapper that authenticates the operator before signing.
  The local Sir Convert client, SSH tunnel, and Sir Convert service must not
  sign their own operator contexts.

Rejected minting paths:

- Sir Convert service-generated contexts;
- internal service self-signed contexts;
- operator CLI self-signed contexts;
- API-key-only ownership envelopes;
- browser-adjacent operator flows that reuse a human product session without an
  explicit operator context.

Until the HuleEdu service/operator minting surfaces exist, retained
non-browser internal and operator lanes may continue only as legacy
transport-authenticated lanes for explicitly non-user-originated work. They
must not be treated as satisfying the final ADR-0009 context-derived ownership
model, and they do not unblock final cutover proof.

## Canonical V1 Field Mapping

All fields below are signed inside `X-Huledu-Identity-Context`. Unsigned
request headers or query parameters cannot override them.

The top-level payload must remain valid HuleEdu `InternalIdentityContextV1`.
That v1 model forbids unknown top-level fields. Sir Convert-specific facts
therefore must be represented through allowed v1 fields such as `sub`,
`roles`, `grants`, `source_app`, `active_app`, `policy_version`, and
`active_context`; or the upstream HuleEdu contract must be extended through
accepted HuleEdu governance before Sir Convert can consume a new version.

| Field | Gateway product/browser | User-originated backend worker | Non-browser internal service | Local operator |
| --- | --- | --- | --- | --- |
| `context_version` | `1` | original Gateway value | `1` | `1` |
| `iss` | `api_gateway_service` | original Gateway value | `api_gateway_service` | `api_gateway_service` |
| `aud` | `sir-convert-a-lot` | original Gateway value | `sir-convert-a-lot` | `sir-convert-a-lot` |
| `sub` | signed user subject | original Gateway user subject | `service:<registered-service-id>` | `operator:<operator-id>` |
| `session_id` | browser session id | original Gateway browser session id | nonblank HuleEdu-minted handle `service-session:<jti>` | nonblank HuleEdu-minted handle `operator-session:<jti>` |
| `org_id` | signed org, or `null` when product realm permits | original Gateway value | signed service scope org, or `null` | signed operator scope org, or `null` |
| `tenant_id` | signed tenant, or `null` when product realm permits | original Gateway value | signed service scope tenant, or `null` | signed operator scope tenant, or `null` |
| `roles` | signed user roles | original Gateway value | `["service"]` plus narrower HuleEdu roles when needed | `["operator"]` plus narrower HuleEdu roles when needed |
| `grants` | Sir Convert grants derived from product entitlement | original Gateway value | explicit service grants only | explicit operator grants only |
| `source_app` | product source app, for example `skriptoteket` | original Gateway value | registered service id, for example `projektveckor_portal` | operator wrapper id, for example `sir-convert-operator-cli` |
| `active_app` | active product app when present | original Gateway value | omitted or registered service id | omitted or operator tool id |
| `active_product_identity_realm` | product realm when required | original Gateway value | omitted | omitted |
| `realm_subject_id` | product realm subject when required | original Gateway value | omitted | omitted |
| `policy_version` | nonblank HuleEdu policy version | original Gateway value | nonblank HuleEdu service policy version | nonblank HuleEdu operator policy version |
| `iat` / `exp` | HuleEdu Gateway TTL | original Gateway value | max 60 seconds unless HuleEdu contract tightens it | max 60 seconds unless HuleEdu contract tightens it |
| `jti` | Gateway nonce | original Gateway value | HuleEdu-minted nonce | HuleEdu-minted nonce |
| `active_context` | may include product/org context | original Gateway value | may include `{"sir_convert":{"workload_purpose":"service_conversion"}}` | may include `{"sir_convert":{"workload_purpose":"operator_conversion"}}` |

The non-browser `session_id` values are not browser sessions. They are
short-lived signed HuleEdu session handles used only to satisfy the upstream
nonblank `session_id` verifier and to give audit logs a stable context handle
for one service/operator exchange.

Sir Convert derives profile-specific facts from the allowed v1 fields:

- context kind comes from `sub` prefix plus `roles`:
  - `sub` without a service/operator prefix is `user`;
  - `sub="service:<registered-service-id>"` plus role `service` is `service`;
  - `sub="operator:<operator-id>"` plus role `operator` is `operator`.
- registered caller comes from `source_app`, with `active_app` as an optional
  additional route/application discriminator.
- workload purpose comes from the route family and relevant
  `sir-convert:*` grant. A HuleEdu-minted `active_context.sir_convert` object
  may narrow that purpose, but it must not be required for v1 verification.

Forbidden top-level examples include `sir_convert_context_kind`,
`sir_convert_registered_caller`, and `sir_convert_workload_purpose`. A payload
containing those keys must fail the canonical HuleEdu v1 verifier.

Service and operator contexts are lane-restricted:

- accepted only on the internal Hemma service lane or sanctioned local tunnel;
- rejected on direct public `convert.hule.education` traffic;
- rejected on public/browser Gateway routes unless that route is explicitly
  marked for service/operator administration by a later accepted decision;
- logged by context kind, registered caller, subject, `session_id`, `jti`,
  grants, and correlation id without recording signing material or secrets.

## Ownership Derivation

Sir Convert persists an ownership envelope for every job at creation time. The
envelope is derived from verified `InternalIdentityContextV1`, never from
unsigned request metadata.

For user-originated workloads:

- `owner_kind`: `user`
- `owner_realm`: `active_product_identity_realm` when present, otherwise
  `source_app` when present, otherwise `huleedu`
- `owner_subject_id`: `realm_subject_id` when present, otherwise `sub`
- `org_id`: signed `org_id`
- `tenant_id`: signed `tenant_id`
- `active_app`: signed `active_app`
- `source_app`: signed `source_app`
- `workload_purpose`: `product_conversion`, derived from the verified caller
  class and route family, not from unsigned request input
- `policy_version`: signed `policy_version`
- `grants_snapshot`: signed grants relevant to Sir Convert authorization
- `identity_jti`: signed `jti`
- `correlation_id`: `X-Correlation-ID`

For non-browser service workloads:

- `owner_kind`: `service`
- `owner_subject_id`: signed service subject in `sub`
- `source_app`: signed service or product origin
- `registered_caller`: signed `source_app`
- `workload_purpose`: `service_conversion` or a narrower approved service
  purpose derived from route/grants and optionally narrowed by signed
  `active_context.sir_convert.workload_purpose`
- `grants_snapshot`: signed Sir Convert service grants
- `context_session_id`: signed non-browser `session_id`
- `identity_jti`: signed `jti`

For local operator workloads:

- `owner_kind`: `operator`
- `owner_subject_id`: signed operator subject in `sub`
- `source_app`: operator tooling or devops wrapper identifier
- `registered_caller`: signed `source_app`
- `workload_purpose`: `operator_conversion` or `operator_diagnostics` derived
  from route/grants and optionally narrowed by signed
  `active_context.sir_convert.workload_purpose`
- `grants_snapshot`: signed Sir Convert operator grants
- `context_session_id`: signed non-browser `session_id`
- `identity_jti`: signed `jti`

Email and display-name fields are not ownership keys. They may be logged only
when an accepted audit policy explicitly allows it.

## Grants

Sir Convert profile grants use this prefix:

- `sir-convert:jobs:create`
- `sir-convert:jobs:read-own`
- `sir-convert:jobs:cancel-own`
- `sir-convert:artifacts:read-own`
- `sir-convert:templates:read`
- `sir-convert:templates:manage`
- `sir-convert:webhooks:manage`
- `sir-convert:operator`
- `sir-convert:service`

Gateway and internal services may carry broader HuleEdu grants, but Sir Convert
authorization must map only the relevant Sir Convert grants and route
permissions.

## Route Authorization

| Route family | Required ownership/grant rule |
| --- | --- |
| `POST /v2/convert/jobs` | Valid context plus `sir-convert:jobs:create`; job owner is persisted from context. |
| `GET /v2/convert/jobs/{job_id}` | Same persisted owner or explicit operator/service grant. |
| `GET /v2/convert/jobs/{job_id}/result` | Same persisted owner or explicit operator/service grant. |
| `GET /v2/convert/jobs/{job_id}/artifact` | Same persisted owner plus `sir-convert:artifacts:read-own`, or explicit operator/service grant. |
| `POST /v2/convert/jobs/{job_id}/cancel` | Same persisted owner plus `sir-convert:jobs:cancel-own`, or explicit operator/service grant. |
| partial, checkpoint, resume, and SSE routes | Same owner rule as the parent job route. |
| `GET /v2/templates/docx*` | Valid context plus `sir-convert:templates:read`, unless explicitly reduced to an internal unauthenticated catalog in a later accepted decision. |
| template mutation routes | Valid context plus `sir-convert:templates:manage`. |
| webhook subscription routes | Valid context plus `sir-convert:webhooks:manage`; browser public routes must not expose this surface directly. |

Cross-owner reads and artifact downloads fail closed with `403`, even when the
request has a valid transport API key.

## API-Key Migration Rule

During migration, `X-API-Key` remains useful for:

- proving the network caller is a known internal integration;
- rate-limit buckets or legacy route admission;
- staged rollout while downstream callers adopt signed identity.

It must not remain sufficient for:

- creating user-originated jobs;
- reading another user's job status;
- downloading artifacts;
- canceling jobs;
- managing templates or webhooks.

## Implementation Test Plan

Task 258 and the Gateway implementation tasks should include at least these
authorization tests:

- valid Gateway context with `aud=sir-convert-a-lot` can create a job and read
  its own status/result/artifact;
- wrong audience, unknown key id, invalid signature, expired context, missing
  context, and malformed context fail closed;
- unsigned user, tenant, role, or grant headers are rejected as identity;
- API key alone cannot authorize a user-originated job after enforcement;
- context A cannot read or download artifacts for a job owned by context B;
- user-originated backend worker calls preserve the original Gateway-issued
  ownership context;
- service context can perform only explicitly granted non-browser service
  operations and only when minted by the HuleEdu-owned authority;
- operator context is accepted only on internal/tunnel lanes, is auditable, and
  is minted by the HuleEdu-owned authority;
- service and operator contexts include nonblank signed `session_id`,
  `policy_version`, and `jti` values without overloading browser sessions;
- representative service and operator contexts validate through the canonical
  HuleEdu `InternalIdentityContextV1` v1 model without unknown top-level
  fields;
- malformed payloads with top-level `sir_convert_*` fields fail closed through
  the canonical HuleEdu v1 verifier;
- service and operator contexts are rejected on public/browser routes and
  direct public `convert.hule.education` traffic;
- Sir Convert rejects any context signed by a Sir-owned key, service self-owned
  key, operator CLI key, or unknown HuleEdu key id;
- Gateway strips browser cookies, bearer tokens, CSRF headers, and
  browser-supplied identity headers before forwarding.

## Migration Notes

Task 260 must map Gateway routes to this profile and prove protected-edge
mechanics in HuleEdu. Task 264 must migrate known Skriptoteket and HuleEdu
consumers so product/user work carries this context. Projektveckor Portal is a
retained internal consumer and needs a downstream follow-up before global
service-key ownership can be retired.
