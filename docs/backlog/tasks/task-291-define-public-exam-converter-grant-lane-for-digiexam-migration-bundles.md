---
id: task-291-define-public-exam-converter-grant-lane-for-digiexam-migration-bundles
title: Define public Exam Converter grant lane for DigiExam migration bundles
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0563-define-public-exam-converter-grant-authority-for-sir-convert.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/reviews/review-pr-0320-exam-converter-public-one-time-runtime-lane.md
labels:
  - exam-migration
  - digiexam
  - examnet
  - public-access
  - grant-authority
  - skriptoteket
  - artifact-bundle
---

PR-sized contract slice for the public Exam Converter grant lane. This task is
paired with HuleEdu `TASK-0563`; neither task authorizes Skriptoteket public
runtime implementation by itself.

## Objective

Define the Sir Convert side of a narrow public Exam Converter grant lane for
`digiexam_dxe -> examnet_migration_bundle` jobs.

The goal is to unblock the authority gap found in Skriptoteket `REV-PR-0320`
without opening general anonymous public Sir Convert conversion, without using
`X-API-Key` as ownership, and without converting public work into service-owned
jobs.

## Context

Task 282 completed the authenticated DigiExam migration service-runtime route.
That route is owned by verified HuleEdu `InternalIdentityContextV1` with
`aud=sir-convert-a-lot`; anonymous public callers remain reserved/fail-closed
in the active authorization profile.

Skriptoteket `PR-0320` needs a no-login one-time Exam Converter lane. The safe
shape is not direct anonymous Sir Convert access. The safe shape is a
HuleEdu-signed public grant that Sir Convert can verify and use as a bounded
public ownership envelope for one route family.

The HuleEdu grant authority task is:

- `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0563-define-public-exam-converter-grant-authority-for-sir-convert.md`

## PR Scope

- Amend or extend the DigiExam migration service API/artifact contract with a
  public grant caller lane.
- Keep the existing `Anonymous public` caller class fail-closed unless a valid
  HuleEdu public Exam Converter grant is present.
- Define the accepted grant verifier input:
  - HuleEdu issuer/signing authority;
  - Sir Convert audience or route audience;
  - grant version;
  - capability `documents.conversion_hub.exam_converter`;
  - route key `digiexam_dxe -> examnet_migration_bundle`;
  - allowed targets;
  - `jti` or nonce;
  - issued/expiry timestamps;
  - policy version;
  - artifact-read lease or equivalent download authorization scope.
- Define persisted public ownership for granted jobs:
  - `owner_kind=public_grant`;
  - owner digest derived from verified grant fields;
  - no raw identity envelope in product-visible outputs;
  - no user, org, tenant, role, service, or operator ownership fallback.
- Define allowed routes and operations:
  - public grant job submit;
  - status/result polling for the grant-owned job;
  - artifact manifest listing;
  - named artifact download under the grant artifact lease.
- Define deterministic rejection for missing, expired, wrong-audience,
  wrong-capability, wrong-route, over-target, replayed, malformed, or
  untrusted public grants.
- Preserve the Task 282 privacy boundary: companion result PDFs may enrich only
  correct machine-marked answers, and product-visible outputs must not contain
  wrong answers, free-text student answers, scores, identity markers, or
  student-performance history.

## Non-Goals

- Do not implement the public runtime in this task unless a later review
  explicitly converts this contract slice into implementation scope.
- Do not open general anonymous public conversion on `convert.hule.education`.
- Do not allow `X-API-Key` alone to create, read, or download public jobs.
- Do not create service-owned jobs for public Exam Converter work.
- Do not change authenticated `InternalIdentityContextV1` behavior for
  user-originated Skriptoteket jobs.
- Do not add arbitrary conversion routes, general file conversion, or Exam.net
  browser automation.

## Deliverables

- [x] A governed Sir Convert contract update or companion reference defining
  the public Exam Converter grant lane.
- [x] A public grant verifier contract that names required grant fields,
  trusted HuleEdu authority, TTL, route scope, target scope, and deterministic
  rejection reasons.
- [x] A public job ownership envelope shape based on verified grant digest/jti.
- [x] Artifact manifest and named-download authorization semantics for
  grant-owned jobs.
- [x] Cross-link to HuleEdu `TASK-0563` as the grant minting authority.
- [x] Explicit blocker retained for Skriptoteket `PR-0320` until both sides of
  the grant contract are accepted.

## Acceptance Criteria

- [x] The contract keeps direct anonymous public Sir Convert access
  fail-closed unless a valid HuleEdu public Exam Converter grant is supplied.
- [x] The grant lane is scoped to `digiexam_dxe -> examnet_migration_bundle`
  and the allowed public Exam Converter targets only.
- [x] Sir Convert public ownership is `owner_kind=public_grant`, derived from
  verified grant fields, and never derived from IP address, `X-API-Key`,
  unsigned metadata, user identity, service identity, or operator identity.
- [x] Submit, status/result, artifact-list, and named-download authorization
  are defined for grant-owned jobs, including expired lease behavior.
- [x] Rejection semantics are defined for missing, expired, malformed,
  wrong-audience, wrong-capability, wrong-route, over-target, replayed, and
  untrusted grants.
- [x] Privacy requirements from Task 282 remain unchanged for public grant
  jobs.
- [x] The contract states that Skriptoteket public runtime remains blocked
  until HuleEdu `TASK-0563` and this task are both accepted.
- [x] Docs validation passes.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Test Requirements

- Positive contract tests must eventually cover public-grant submit, poll,
  result, artifact manifest, and named artifact download.
- Negative tests must eventually cover no grant, expired grant, wrong audience,
  wrong capability, wrong route key, over-target requests, replay or duplicate
  use outside idempotency policy, forged issuer/key id, and valid transport
  API key without grant ownership.
- Privacy tests must prove forbidden result-PDF data is absent from API
  responses, manifests, logs intended for product consumption, and artifacts.
- Cross-repo proof must show direct public `convert.hule.education` job traffic
  remains fail-closed unless routed through the accepted grant lane.

## Stop Conditions

- Stop if public work would need to be modeled as authenticated user work.
- Stop if public work would need to be modeled as global service-owned work.
- Stop if `X-API-Key` would become job or artifact ownership.
- Stop if artifact reads cannot be bounded by the grant or artifact-read lease.
- Stop if the grant shape requires new top-level
  `InternalIdentityContextV1` fields instead of a separate public grant
  contract.
- Stop if the change would widen general Sir Convert public access beyond the
  Exam Converter route.

## Verification

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Evidence

Implemented on 2026-05-13 as a docs-governed Sir Convert contract slice. The
durable contract update lives in
`docs/converters/digiexam-migration-service-api-artifact-contract.md`, with a
supporting authorization-profile note in
`docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.

The Sir Convert side now accepts only a HuleEdu-signed
`PublicConversionGrantV1` for the public Exam Converter exception. The verifier
contract names required grant fields, trusted HuleEdu issuer/audience,
capability, route key, target scope, policy profile, upload and abuse-control
limits, timestamps, `jti`, and deterministic rejection classes.

Public jobs are defined as `owner_kind=public_grant`, with `owner_digest`
derived from verifier-approved grant material. Ownership is never derived from
IP address, `X-API-Key`, unsigned upload metadata, authenticated user identity,
service identity, operator identity, browser state, or product-visible
metadata.

The lane authorizes only public grant submit plus grant-bound status/result
polling for `digiexam_dxe -> examnet_migration_bundle`. Public artifact
manifest listing and named downloads require `PublicArtifactReadLeaseV1` bound
to the persisted public-grant job, parent grant, owner digest, route, target
snapshot, artifact key, TTL, and correlation id.

Direct anonymous Sir Convert conversion remains fail-closed. The Task 282
privacy boundary remains unchanged: public grant jobs must not expose wrong
answers, free-text student answers, scores, identity markers, or
student-performance history. Skriptoteket `PR-0320` remains blocked until the
accepted HuleEdu grant authority and this accepted Sir Convert verifier /
ownership contract are consumed by a later governed runtime slice.
