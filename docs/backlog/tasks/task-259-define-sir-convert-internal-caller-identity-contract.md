---
id: task-259-define-sir-convert-internal-caller-identity-contract
title: Define Sir Convert InternalIdentityContextV1 authorization profile
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-36-sir-convert-internal-auth-and-metadata-hardening-before-cutover.md
  - docs/backlog/stories/story-35-preserve-internal-service-and-local-operator-sir-convert-lanes.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
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
- Define how unsigned/spoofed identity headers are rejected.
- Define the migration role of the existing service API key as a transport
  credential only, not as global job/artifact ownership.
- Update API/downstream/internal adapter docs with the internal identity
  contract.

## Deliverables

- [ ] Sir Convert `InternalIdentityContextV1` authorization profile document
  update.
- [ ] Test plan for Gateway, internal service, user-originated backend,
  operator, and rejected spoofed identity cases.
- [ ] HuleEdu/Skriptoteket follow-up notes for adopting the contract.

## Acceptance Criteria

- [ ] Direct internal callers remain supported.
- [ ] Browser-derived identity is accepted only from Gateway-issued
  `InternalIdentityContextV1` with audience `sir-convert-a-lot`.
- [ ] Job ownership is not reduced to a single global public API-key scope.
- [ ] Status, result, artifact, partial, checkpoint, resume, cancel, template,
  SSE, and webhook access enforce context-derived job ownership.
- [ ] A user-originated backend worker call must carry Gateway-issued
  `InternalIdentityContextV1` user context.
- [ ] Spoofed unsigned identity headers are rejected in tests.
- [ ] Local operator access remains explicit and auditable.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
