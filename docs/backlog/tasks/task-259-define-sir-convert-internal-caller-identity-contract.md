---
id: task-259-define-sir-convert-internal-caller-identity-contract
title: Define Sir Convert InternalIdentityContextV1 authorization profile
type: task
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-36-sir-convert-internal-auth-and-metadata-hardening-before-cutover.md
  - docs/backlog/stories/story-35-preserve-internal-service-and-local-operator-sir-convert-lanes.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/backlog/tasks/task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover.md
labels:
  - internal-service
  - auth
  - identity
  - gateway
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and lock the Sir Convert authorization profile for HuleEdu
`InternalIdentityContextV1`. Sir Convert must consume the existing HuleEdu
signed downstream identity contract for Gateway/user-originated traffic with
audience `sir-convert-a-lot`, then layer Sir-specific job-owner, artifact, and
operator/service rules on top.

## PR Scope

- Reference ADR-0039 and HuleEdu
  `REF-internal-identity-context-v1-contract` as the canonical transport and
  signature authority.
- Define Sir Convert's expected `InternalIdentityContextV1` audience:
  `sir-convert-a-lot`.
- Define Sir-specific job-owner derivation, audit fields, artifact/status
  access rules, and grants/scopes.
- Define any explicit non-browser service/operator extension without creating
  a parallel signed identity transport.
- Lock the HuleEdu-owned minting authority and canonical field mapping for
  service/operator contexts, including nonblank non-browser `session_id`
  handles.
- Define how unsigned/spoofed identity headers are rejected.
- Define the migration role of the existing service API key as a transport
  credential only, not as global job/artifact ownership.
- Update API/downstream/internal adapter docs with the internal identity
  contract.

## Deliverables

- [x] Sir Convert `InternalIdentityContextV1` authorization profile document
  update.
- [x] Test plan for Gateway, internal service, user-originated backend,
  operator, and rejected spoofed identity cases.
- [x] Non-browser service/operator minting authority and canonical field
  mapping.
- [x] HuleEdu/Skriptoteket follow-up notes for adopting the contract.

## Acceptance Criteria

- [x] Direct internal callers remain supported.
- [x] Browser-derived identity is accepted only from Gateway-issued
  `InternalIdentityContextV1` with audience `sir-convert-a-lot`.
- [x] Job ownership is not reduced to a single global public API-key scope.
- [x] Status, result, artifact, partial, checkpoint, resume, cancel, template,
  SSE, and webhook access enforce context-derived job ownership.
- [x] A user-originated backend worker call must carry Gateway-issued
  `InternalIdentityContextV1` user context.
- [x] Spoofed unsigned identity headers are covered by the implementation test
  plan and must be rejected by Task 258/260 route tests.
- [x] Local operator access remains explicit and auditable.
- [x] Service/operator contexts are minted only by a HuleEdu-owned
  Gateway/internal identity authority, never by Sir Convert, service callers,
  or operator CLI tooling.
- [x] Service/operator contexts satisfy mandatory HuleEdu
  `InternalIdentityContextV1` fields, including nonblank `session_id`, without
  pretending to be browser sessions.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Completion Notes

Completed on 2026-04-19 as a contract/profile definition task.

The Sir Convert authorization profile now lives in
`docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
It consumes HuleEdu `InternalIdentityContextV1` with audience
`sir-convert-a-lot`, defines context-derived job/artifact ownership, keeps
`X-API-Key` as transport-only during migration, and names the implementation
test plan for spoofed headers, wrong audience, invalid signatures,
cross-owner artifact reads, service contexts, and operator contexts.

Runtime enforcement and route tests remain owned by Task 258, Task 260, and the
consumer cutover/proof tasks.

Review 06 resolution:

- The profile now locks all accepted context minting to a HuleEdu-owned
  Gateway/internal identity authority using the canonical HuleEdu signing key
  set and `iss == "api_gateway_service"`.
- Sir Convert, internal service callers, and operator CLI tooling are
  explicitly forbidden from signing their own contexts.
- Non-browser service and operator contexts now have a canonical signed field
  mapping through HuleEdu v1 fields only, including `sub`, nonblank
  `session_id`, `roles`, `grants`, `source_app`, optional `active_context`,
  TTL, `jti`, lane restrictions, and audit semantics.
- The implementation test plan now requires service/operator contexts to be
  accepted only from the HuleEdu-owned authority and rejected on public/browser
  routes.

Review 06 schema-compatibility follow-up:

- The profile no longer adds undeclared top-level `sir_convert_*` fields to
  `InternalIdentityContextV1` v1.
- Sir Convert derives context kind from `sub` and `roles`, registered caller
  from `source_app`, and workload purpose from route/grants with optional
  narrowing through signed `active_context`.
- The implementation test plan now requires representative service/operator
  contexts to validate through the canonical HuleEdu v1 model and malformed
  contexts with unknown top-level `sir_convert_*` fields to fail closed.
